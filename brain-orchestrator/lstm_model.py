import os
import joblib
import numpy as np
from tensorflow.keras.models import load_model

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/lstm_quantile_tau095_30s_7030.keras")
FEAT_SCALER_PATH = os.environ.get("FEAT_SCALER_PATH", "/app/models/feat_scaler.pkl")
TGT_SCALER_PATH = os.environ.get("TGT_SCALER_PATH", "/app/models/tgt_scaler.pkl")

LOOK_BACK = int(os.environ.get("LOOK_BACK", 60))
N_FEATURES = int(os.environ.get("N_FEATURES", 12))

class LSTMOrchestratorModel:
    def __init__(self):
        print(f"Loading Feature Scaler from {FEAT_SCALER_PATH}...")
        self.feat_scaler = joblib.load(FEAT_SCALER_PATH)
        
        print(f"Loading Target Scaler from {TGT_SCALER_PATH}...")
        self.tgt_scaler = joblib.load(TGT_SCALER_PATH)
        
        print(f"Loading Model from {MODEL_PATH}...")
        self.model = load_model(MODEL_PATH, compile=False)
        
        print("LSTM 12-feature model and scalers successfully loaded.")

    def predict(self, feature_matrix):
        """
        feature_matrix: numpy array or list of shape (60, 12)
        It must contain exactly LOOK_BACK items (60 steps), each with 12 features.
        Returns a tuple: (predicted_rps_content, predicted_rps_media)
        """
        data = np.array(feature_matrix, dtype=np.float32)
        if data.shape != (LOOK_BACK, N_FEATURES):
            raise ValueError(f"Feature matrix must have shape ({LOOK_BACK}, {N_FEATURES}), got {data.shape}.")
        
        # Scale input features
        data_scaled = self.feat_scaler.transform(data)
        
        # Reshape to 3D for LSTM input: (batch_size, time_steps, features)
        input_X = data_scaled.reshape(1, LOOK_BACK, N_FEATURES)
        
        # Make prediction
        pred_scaled = self.model.predict(input_X, verbose=0)
        
        # Inverse transform target
        pred = self.tgt_scaler.inverse_transform(pred_scaled)
        
        pred_content = max(0.0, float(pred[0][0]))
        pred_media = max(0.0, float(pred[0][1]))
        
        return pred_content, pred_media
