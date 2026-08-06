import os
import time
import json
import logging
import requests
import docker
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
from prometheus_client import start_http_server, Gauge

from metrics_collector import get_current_metrics
from lstm_model import LSTMOrchestratorModel, LOOK_BACK, N_FEATURES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables
DASHBOARD_PREDICT_URL = os.environ.get("DASHBOARD_PREDICT_URL", "http://dashboard-service:3002/api/predict")
PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", 8000))
PRELOAD_CSV = os.environ.get("PRELOAD_CSV", "/app/data/clarknet_features_30s.csv")
INTERVAL_SEC = 1.0
AGGREGATION_WINDOW = 30  # 30-second aggregation

# GDS Auto-scaler config
MAX_CAPACITY = 10.0
R_MIN = 1
CDT_LIMIT = 10 # 10 seconds cooldown
SDR = 0.4      # Scale-down ratio

# Prometheus metrics to expose
PRED_RPS_CONTENT = Gauge('predicted_rps_content', 'Predicted RPS for content-service')
PRED_RPS_MEDIA = Gauge('predicted_rps_media', 'Predicted RPS for media-service')
TARGET_REP_CONTENT = Gauge('target_replicas_content', 'Target replicas for content-service')
TARGET_REP_MEDIA = Gauge('target_replicas_media', 'Target replicas for media-service')

class BrainOrchestrator:
    def __init__(self):
        self.model = LSTMOrchestratorModel()
        self.docker_client = docker.from_env()
        
        # Buffer to keep 1-second RPS readings for 30s aggregation
        self.sec_rps_buffer = []
        
        # Buffer to keep 120 steps of 30-second Total RPS (1 hour history)
        # Needed for 1h rolling mean/std and 60-step lookback
        self.history_30s_rps = deque(maxlen=120)
        self.history_30s_dt = deque(maxlen=120)
        
        self.cooldown_content = 0
        self.cooldown_media = 0
        
        self.current_rep_content = R_MIN
        self.current_rep_media = R_MIN

        self._preload_data()
        self._init_cold_pool()

    def _init_cold_pool(self):
        project_name = os.environ.get("COMPOSE_PROJECT_NAME", "lstm-proactive-scaling-microservices-clarknet-docker-compose")
        logging.info("Initializing Cold Pool via Docker Socket API...")
        try:
            for srv_name in ["content-service", "media-service"]:
                containers = self.docker_client.containers.list(
                    all=True,
                    filters={"label": [f"com.docker.compose.project={project_name}", f"com.docker.compose.service={srv_name}"]}
                )
                containers = sorted(containers, key=lambda c: c.name)
                for idx, c in enumerate(containers):
                    if idx == 0:
                        if c.status != 'running':
                            c.start()
                    else:
                        if c.status == 'running':
                            c.stop()
            logging.info("Cold Pool Initialization Complete.")
        except Exception as e:
            logging.error(f"Error initializing Cold Pool: {e}")

    def _preload_data(self):
        """Preload 120 steps (1 hour) of 30-second RPS before the 70% test split mark."""
        if os.path.exists(PRELOAD_CSV):
            logging.info(f"Preloading 120-step (1h) history from {PRELOAD_CSV}")
            try:
                df = pd.read_csv(PRELOAD_CSV, parse_dates=['datetime']) if 'datetime' in pd.read_csv(PRELOAD_CSV, nrows=2).columns else pd.read_csv(PRELOAD_CSV)
                
                # Standard 70/30 split logic
                n_total = len(df)
                n_train = int(n_total * 0.7)
                
                # Grab 120 rows before train split index
                start_idx = max(0, n_train - 120)
                preload_df = df.iloc[start_idx:n_train]
                
                for _, row in preload_df.iterrows():
                    tot_rps = row.get('rps', row.get('Content_Service', 0) + row.get('Media_Service', 0))
                    dt_val = row.get('datetime', datetime.now())
                    self.history_30s_rps.append(float(tot_rps))
                    self.history_30s_dt.append(dt_val)
                    
                logging.info(f"Successfully preloaded {len(self.history_30s_rps)} 30-second records for 12-feature pipeline.")
            except Exception as e:
                logging.error(f"Failed to preload data: {e}")
        else:
            logging.warning(f"Preload CSV not found at {PRELOAD_CSV}. Will require warm-up period.")

    def compute_12_features(self):
        """Extract 12 temporal features from the 120-step 30s RPS buffer."""
        rps_list = list(self.history_30s_rps)
        dt_list  = list(self.history_30s_dt)
        
        df = pd.DataFrame({'rps': rps_list})
        
        # Rolling window stats
        df['roll_1m_mean']  = df['rps'].rolling(2).mean()
        df['roll_15m_mean'] = df['rps'].rolling(30).mean()
        df['roll_1h_mean']  = df['rps'].rolling(120).mean()
        df['roll_1m_max']   = df['rps'].rolling(2).max()
        df['roll_1h_std']   = df['rps'].rolling(120).std().fillna(0.0)
        
        # Lags and diffs
        df['lag_30s'] = df['rps'].shift(1)
        df['diff_1']  = df['rps'].diff(1)
        df['diff_2']  = df['rps'].diff(2)
        df['diff_10'] = df['rps'].diff(10)
        
        # Time features based on latest datetime
        last_dt = dt_list[-1] if dt_list and hasattr(dt_list[-1], 'hour') else datetime.now()
        hour = last_dt.hour
        dow  = last_dt.weekday() if hasattr(last_dt, 'weekday') else 0
        
        df['hour_sin']   = np.sin(2 * np.pi * hour / 24.0)
        df['hour_cos']   = np.cos(2 * np.pi * hour / 24.0)
        df['is_weekend'] = 1.0 if dow >= 5 else 0.0
        
        feature_cols = [
            'roll_1m_mean', 'roll_15m_mean', 'roll_1h_mean',
            'roll_1m_max', 'roll_1h_std',
            'lag_30s', 'diff_1', 'diff_2', 'diff_10',
            'hour_sin', 'hour_cos', 'is_weekend'
        ]
        
        # Fill NaN from rolling/diff at start
        df_feat = df[feature_cols].bfill().ffill().fillna(0.0)
        
        # Take the last 60 rows for LSTM lookback window
        feat_matrix = df_feat.iloc[-LOOK_BACK:].values.astype(np.float32)
        return feat_matrix

    def calculate_replicas(self, predicted_rps):
        import math
        req = math.ceil(predicted_rps / MAX_CAPACITY)
        return max(R_MIN, req)

    def perform_gds_scaling(self, service_name, predicted_rep, current_rep, cooldown_timer):
        import threading
        target = current_rep
        new_cooldown = cooldown_timer
        
        if predicted_rep > current_rep:
            target = predicted_rep
            new_cooldown = CDT_LIMIT
            logging.info(f"[SCALE-UP] {service_name}: {current_rep} -> {target}")
            threading.Thread(target=self._scale_docker_service, args=(service_name, target)).start()
        elif predicted_rep < current_rep:
            if cooldown_timer > 0:
                new_cooldown -= 1
            else:
                import math
                diff = current_rep - predicted_rep
                drop = math.ceil(diff * SDR)
                target = current_rep - drop
                target = max(predicted_rep, target)
                new_cooldown = CDT_LIMIT
                logging.info(f"[SCALE-DOWN] {service_name}: {current_rep} -> {target}")
                threading.Thread(target=self._scale_docker_service, args=(service_name, target)).start()
        
        return target, new_cooldown

    def _scale_docker_service(self, service_name, replicas):
        try:
            project_name = os.environ.get("COMPOSE_PROJECT_NAME", "lstm-proactive-scaling-microservices-clarknet-docker-compose")
            logging.info(f"Using Socket API to scale {service_name} to {replicas}")
            
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": [f"com.docker.compose.project={project_name}", f"com.docker.compose.service={service_name}"]}
            )
            containers = sorted(containers, key=lambda c: c.name)
            
            for idx, c in enumerate(containers):
                if idx < replicas:
                    if c.status != 'running':
                        logging.info(f"Starting {c.name}...")
                        c.start()
                else:
                    if c.status == 'running':
                        logging.info(f"Stopping {c.name}...")
                        c.stop()
        except Exception as e:
            logging.error(f"Error scaling {service_name}: {e}")

    def run(self):
        logging.info(f"Starting Brain Orchestrator (12-feature 30s aggregate) on Prometheus port {PROMETHEUS_PORT}...")
        start_http_server(PROMETHEUS_PORT)
        
        while True:
            start_time = time.time()
            
            # 1. Collect 1-second metric from Prometheus
            metrics = get_current_metrics()
            tot_rps = metrics['rps_content'] + metrics['rps_media']
            self.sec_rps_buffer.append(tot_rps)
            
            # Every 30 seconds (or if buffer reaches 30 seconds of readings)
            if len(self.sec_rps_buffer) >= AGGREGATION_WINDOW:
                max_30s_rps = max(self.sec_rps_buffer)
                self.sec_rps_buffer.clear()
                
                # Append 30s max RPS to 1-hour history
                self.history_30s_rps.append(max_30s_rps)
                
                # Sinkronisasi Waktu Virtual (ClarkNet Time Flow)
                if len(self.history_30s_dt) > 0:
                    next_dt = self.history_30s_dt[-1] + timedelta(seconds=30)
                else:
                    next_dt = datetime.now()
                self.history_30s_dt.append(next_dt)
                
                if len(self.history_30s_rps) >= LOOK_BACK:
                    # 2. Extract 12 features on-the-fly
                    feat_matrix = self.compute_12_features()
                    
                    # 3. Predict using 12-feature LSTM Quantile model
                    pred_content, pred_media = self.model.predict(feat_matrix)
                    
                    # 4. Calculate Replicas
                    req_content = self.calculate_replicas(pred_content)
                    req_media = self.calculate_replicas(pred_media)
                    
                    # 5. Apply GDS Auto-Scaling
                    self.current_rep_content, self.cooldown_content = self.perform_gds_scaling(
                        "content-service", req_content, self.current_rep_content, self.cooldown_content
                    )
                    self.current_rep_media, self.cooldown_media = self.perform_gds_scaling(
                        "media-service", req_media, self.current_rep_media, self.cooldown_media
                    )
                    
                    # 6. Export to Prometheus
                    PRED_RPS_CONTENT.set(pred_content)
                    PRED_RPS_MEDIA.set(pred_media)
                    TARGET_REP_CONTENT.set(self.current_rep_content)
                    TARGET_REP_MEDIA.set(self.current_rep_media)
                    
                    # 7. (Kode HTTP POST dihapus karena Dashboard sudah mengambil data langsung dari Prometheus)
            
            elapsed = time.time() - start_time
            sleep_time = max(0, INTERVAL_SEC - elapsed)
            time.sleep(sleep_time)

if __name__ == "__main__":
    orchestrator = BrainOrchestrator()
    orchestrator.run()

