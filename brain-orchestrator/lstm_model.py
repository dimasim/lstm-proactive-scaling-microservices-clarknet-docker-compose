import os
import joblib
import numpy as np
from tensorflow.keras.models import load_model

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/LSTM_1min_1step.h5")
SCALER_PATH = os.environ.get("SCALER_PATH", "/app/models/rps_scaler_1min_1step.pkl")

# We expect the model to be trained with look_back=60 and n_features=2 (e.g., RPS_Content, RPS_Media)
LOOK_BACK = int(os.environ.get("LOOK_BACK", 60))
N_FEATURES = int(os.environ.get("N_FEATURES", 2))

class LSTMOrchestratorModel:
    def __init__(self):
        print(f"Loading Scaler from {SCALER_PATH}...")
        self.scaler = joblib.load(SCALER_PATH)
        
        print(f"Loading Model from {MODEL_PATH}...")
        self.model = load_model(MODEL_PATH, compile=False)
        
        print("LSTM model and scaler successfully loaded.")

    def predict(self, history_buffer):
        """
        history_buffer: list of lists, e.g., [[rps_content, rps_media], ...] 
        It must contain exactly LOOK_BACK items (60 steps).
        Returns a tuple: (predicted_rps_content, predicted_rps_media)
        """
        if len(history_buffer) != LOOK_BACK:
            raise ValueError(f"History buffer must have exactly {LOOK_BACK} timesteps, got {len(history_buffer)}.")
        
        # Convert to numpy array
        data = np.array(history_buffer) # shape: (60, 2)
        
        # Scale the data using the loaded scaler
        data_scaled = self.scaler.transform(data)
        
        # Reshape to 3D for LSTM input: (batch_size, time_steps, features)
        input_X = data_scaled.reshape(1, LOOK_BACK, N_FEATURES)
        
        # Make prediction
        pred_scaled = self.model.predict(input_X, verbose=0)
        
        # Inverse transform
        pred = self.scaler.inverse_transform(pred_scaled)
        
        # pred is shape (1, 2). Return as tuple.
        pred_content = max(0.0, float(pred[0][0]))
        pred_media = max(0.0, float(pred[0][1]))
        
        return pred_content, pred_media
