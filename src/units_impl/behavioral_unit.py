import time
import numpy as np
import joblib
import pandas as pd
from collections import deque
from dms_camera import DMSCamera

class BehavioralUnit:
    def __init__(self, shared_gyro_sensor, model_path="lightgbm_model.pkl"):
        """
        Initializes the ML-based behavioral unit.
        Args:
            shared_gyro_sensor: The DMSGyro instance (shared with CriticalUnit to prevent I2C conflicts).
            model_path (str): Path to the trained LightGBM model file.
        """
        print("Initializing Behavioral & Kinematic Unit (LightGBM)...")
        self.camera_sensor = DMSCamera()
        self.gyro_sensor = shared_gyro_sensor
        # Buffer to hold historical data for the 3-second rolling window
        # deque allows fast O(1) appends and pops from both ends
        self.history = deque()
        self.ROLLING_WINDOW_SECONDS = 3.0
        # Direct drowsiness detection
        self.EAR_THRESHOLD = 0.20
        self.EAR_FRAMES_PER_ALARM = 10
        self.blink_counter = 0
        # Load the Pre-trained LightGBM Model
        try:
            self.model = joblib.load(model_path)
            self.model_loaded = True
            print("LightGBM Model loaded successfully.")
        except Exception as e:
            print(f"Warning: ML Model not found at {model_path}. Running in fallback mode. Error: {e}")
            self.model_loaded = False

    def get_data(self):
        """
        Polls camera and gyro, updates the rolling window, calculates std/mean, 
        and requests a prediction from LightGBM.
        Returns:
            dict: {"prediction": str} (e.g., "VIGILE", "SONNOLENZA", "MALORE", "DISTRAZIONE")
        """
        current_time = time.time()
        
        # --- 1. FETCH RAW METRICS FROM SENSORS ---
        cam_raw = self.camera_sensor.get_raw_data() or {}
        gyro_raw = self.gyro_sensor.get_raw_data() or {}

        # Extract Camera Data
        ear = cam_raw.get("ear", 0.30)
        pitch = cam_raw.get("pitch", 0.0)
        yaw = cam_raw.get("yaw", 0.0)

        # Extract Gyro Data
        acc_x = gyro_raw.get("accel_x", 0.0)
        acc_y = gyro_raw.get("accel_y", 0.0)
        acc_z = gyro_raw.get("accel_z", 0.0)

        # --- 2. UPDATE ROLLING WINDOW ---
        self.history.append({
            "timestamp": current_time,
            "ear": ear,
            "pitch": pitch,
            "yaw": yaw,
            "acc_x": acc_x,
            "acc_y": acc_y,
            "acc_z": acc_z
        })

        # Remove old data that falls outside the 3-second window
        while self.history and (current_time - self.history[0]["timestamp"]) > self.ROLLING_WINDOW_SECONDS:
            self.history.popleft()

        # Raw camera snapshot for LED directional feedback
        _cam_raw = {"pitch": pitch, "yaw": yaw, "ear": ear}

        # --- 3. DIRECT DROWSINESS DETECTION (frame-by-frame, like dms_core) ---
        # This provides immediate response without waiting for the ML rolling window.
        if ear < self.EAR_THRESHOLD:
            self.blink_counter += 1
        else:
            self.blink_counter = 0

        if self.blink_counter >= self.EAR_FRAMES_PER_ALARM:
            return {"prediction": "SONNOLENZA", "_cam_raw": _cam_raw}

        # --- 4. ML PREDICT ---
        # If the ML model failed to load, or we don't have enough data yet (< 1 second)
        # we return a safe default to prevent system crashes at boot.
        if not self.model_loaded or len(self.history) < 5:
            return {"prediction": "VIGILE", "_cam_raw": _cam_raw}

        # Calculate exactly the metrics requested by the LightGBM learning curve
        features = self._calculate_rolling_features()

        # The model expects a 2D array or a DataFrame.
        # Using a DataFrame with columns ensures LightGBM matches features correctly
        df_features = pd.DataFrame([features])

        try:
            # Output of predict is usually an array, e.g., ['SONNOLENZA']
            prediction_array = self.model.predict(df_features)
            prediction = str(prediction_array[0])
            return {"prediction": prediction, "_cam_raw": _cam_raw}
        except Exception as e:
            print(f"ML Prediction Error: {e}")
            return {"prediction": "VIGILE", "_cam_raw": _cam_raw}

    def _calculate_rolling_features(self):
        """
        Extracts temporal features (mean, min, std) from the current buffer.
        """
        # Convert deque of dicts to a dictionary of lists for easier numpy math
        data = {k: [dic[k] for dic in self.history] for k in self.history[0]}
        
        return {
            "EAR_mean_3s": np.mean(data["ear"]),
            "EAR_min_3s": np.min(data["ear"]),
            "Pitch_std_3s": np.std(data["pitch"]),
            "Yaw_std_3s": np.std(data["yaw"]),
            "Gyro_X_std_3s": np.std(data["acc_x"]),
            "Gyro_Y_std_3s": np.std(data["acc_y"]),
            "Gyro_Z_std_3s": np.std(data["acc_z"])
        }

    def stop(self):
        """Safely shuts down the camera."""
        # Gyro is not stopped here since it's shared and will be stopped by the caller
        try:
            self.camera_sensor.stop()
        except:
            pass