import os
import time
import json
import logging
import requests
import docker
import pandas as pd
from collections import deque
from prometheus_client import start_http_server, Gauge

from metrics_collector import get_current_metrics
from lstm_model import LSTMOrchestratorModel, LOOK_BACK

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables
DASHBOARD_PREDICT_URL = os.environ.get("DASHBOARD_PREDICT_URL", "http://dashboard-service:3002/api/predict")
PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", 8000))
PRELOAD_CSV = os.environ.get("PRELOAD_CSV", "/app/data/combined_clarknet_rps_3x.csv")
INTERVAL_SEC = 1.0

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
        self.history_buffer = deque(maxlen=LOOK_BACK)
        self.docker_client = docker.from_env()
        
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
            # We want to ensure 1 is running, the rest are stopped.
            for srv_name in ["content-service", "media-service"]:
                containers = self.docker_client.containers.list(
                    all=True,
                    filters={"label": [f"com.docker.compose.project={project_name}", f"com.docker.compose.service={srv_name}"]}
                )
                # Sort containers by container index (e.g. _1, _2, _3)
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
        if os.path.exists(PRELOAD_CSV):
            logging.info(f"Preloading 60-second history from {PRELOAD_CSV}")
            try:
                df = pd.read_csv(PRELOAD_CSV)
                
                if len(df) == LOOK_BACK:
                    # If the CSV has exactly 60 rows, it's a specialized demo history file
                    preload_df = df
                else:
                    # Standard behavior: grab the 60 rows before the 70% test split
                    split_idx = int(len(df) * 0.7)
                    preload_df = df.iloc[split_idx-LOOK_BACK : split_idx]
                
                for _, row in preload_df.iterrows():
                    c = row.get('Content_Service', row.iloc[1] if len(row) > 1 else 0)
                    m = row.get('Media_Service', row.iloc[2] if len(row) > 2 else 0)
                    self.history_buffer.append([c, m])
                    
                logging.info(f"Successfully preloaded {len(self.history_buffer)} records.")
            except Exception as e:
                logging.error(f"Failed to preload data: {e}")
        else:
            logging.warning("Preload CSV not found. Will require 60 seconds warm-up.")

    def calculate_replicas(self, predicted_rps):
        """Calculate required replicas based on capacity and max constraint"""
        import math
        req = math.ceil(predicted_rps / MAX_CAPACITY)
        return max(R_MIN, req)

    def perform_gds_scaling(self, service_name, predicted_rep, current_rep, cooldown_timer):
        """Gradual Down-Scaling logic"""
        target = current_rep
        new_cooldown = cooldown_timer
        
        if predicted_rep > current_rep:
            # Proactive Scale-Up
            target = predicted_rep
            new_cooldown = CDT_LIMIT
            logging.info(f"[SCALE-UP] {service_name}: {current_rep} -> {target}")
            self._scale_docker_service(service_name, target)
        elif predicted_rep < current_rep:
            if cooldown_timer > 0:
                new_cooldown -= 1
            else:
                # Gradual Scale-Down
                import math
                diff = current_rep - predicted_rep
                drop = math.ceil(diff * SDR)
                target = current_rep - drop
                target = max(predicted_rep, target)
                new_cooldown = CDT_LIMIT
                logging.info(f"[SCALE-DOWN] {service_name}: {current_rep} -> {target}")
                self._scale_docker_service(service_name, target)
        
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
        logging.info(f"Starting Brain Orchestrator on Prometheus port {PROMETHEUS_PORT}...")
        start_http_server(PROMETHEUS_PORT)
        
        while True:
            start_time = time.time()
            
            # 1. Collect current metrics
            metrics = get_current_metrics()
            self.history_buffer.append([metrics['rps_content'], metrics['rps_media']])
            
            if len(self.history_buffer) == LOOK_BACK:
                # 2. Predict next second
                pred_content, pred_media = self.model.predict(list(self.history_buffer))
                
                # 3. Calculate Replicas
                req_content = self.calculate_replicas(pred_content)
                req_media = self.calculate_replicas(pred_media)
                
                # 4. Apply GDS Auto-Scaling
                self.current_rep_content, self.cooldown_content = self.perform_gds_scaling(
                    "content-service", req_content, self.current_rep_content, self.cooldown_content
                )
                self.current_rep_media, self.cooldown_media = self.perform_gds_scaling(
                    "media-service", req_media, self.current_rep_media, self.cooldown_media
                )
                
                # 5. Export to Prometheus
                PRED_RPS_CONTENT.set(pred_content)
                PRED_RPS_MEDIA.set(pred_media)
                TARGET_REP_CONTENT.set(self.current_rep_content)
                TARGET_REP_MEDIA.set(self.current_rep_media)
                
                # 6. HTTP POST to Dashboard
                payload = {
                    "predicted_rps_content": pred_content,
                    "predicted_rps_media": pred_media,
                    "predicted_replicas_content": self.current_rep_content,
                    "predicted_replicas_media": self.current_rep_media
                }
                try:
                    requests.post(DASHBOARD_PREDICT_URL, json=payload, timeout=0.5)
                except Exception as e:
                    logging.warning(f"Failed to push to dashboard: {e}")
            else:
                logging.info(f"Warming up... Buffer size: {len(self.history_buffer)}/{LOOK_BACK}")
                
            elapsed = time.time() - start_time
            sleep_time = max(0, INTERVAL_SEC - elapsed)
            time.sleep(sleep_time)

if __name__ == "__main__":
    orchestrator = BrainOrchestrator()
    orchestrator.run()
