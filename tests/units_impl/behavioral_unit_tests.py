import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pandas as pd

# --- IMPORT MOCKING ---
sys.modules['dms_camera'] = MagicMock()
sys.modules['joblib'] = MagicMock()

# Add source directories to sys.path so bare imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'units_impl'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))

from behavioral_unit import BehavioralUnit
import joblib

class TestBehavioralUnit(unittest.TestCase):
    
    def setUp(self):
        """Initialize the unit with mocked hardware and a mocked ML model."""
        # Create a mock gyro instance to pass as dependency
        self.mock_gyro = MagicMock()
        
        # Create a fake ML model that will return "VIGILE" by default
        self.mock_model = MagicMock()
        self.mock_model.predict.return_value = ["VIGILE"]
        joblib.load.return_value = self.mock_model
        
        self.unit = BehavioralUnit(shared_gyro_sensor=self.mock_gyro)
        self.mock_camera = self.unit.camera_sensor

    @patch('behavioral_unit.time.time')
    def test_buffer_accumulation_and_prediction(self, mock_time):
        """Test that the 3-second window accumulates data properly and calls the model."""
        
        # Simulate 6 frames (e.g., 2 frames per second for 3 seconds)
        for i in range(6):
            # Advance time by 0.5s each frame
            mock_time.return_value = 100.0 + (i * 0.5)
            
            # Feed raw numbers from HAL
            self.mock_camera.get_status.return_value = {
                "raw_metrics": {"ear": 0.25, "pitch": 5.0, "yaw": 2.0}
            }
            self.mock_gyro.get_status.return_value = {
                "raw_acc": {"acc_x": 0.1, "acc_y": 0.2, "acc_z": 9.8}
            }
            
            result = self.unit.get_data()
        
        # After 6 frames, buffer is full. The model should have been called!
        self.assertTrue(self.mock_model.predict.called)
        
        # Retrieve the DataFrame passed to the ML model on the last call
        args, _ = self.mock_model.predict.call_args
        features_df = args[0]
        
        # Verify the DataFrame columns match the LightGBM expected inputs
        expected_columns = [
            "EAR_mean_3s", "EAR_min_3s", "Pitch_std_3s", "Yaw_std_3s", 
            "Gyro_X_std_3s", "Gyro_Y_std_3s", "Gyro_Z_std_3s"
        ]
        self.assertListEqual(list(features_df.columns), expected_columns)
        
        # Since EAR was constantly 0.25, the mean should be 0.25 and std dev of pitch should be 0.0
        self.assertAlmostEqual(features_df["EAR_mean_3s"].iloc[0], 0.25)
        self.assertAlmostEqual(features_df["Pitch_std_3s"].iloc[0], 0.0)
        
        # And the output should match our fake model's return
        self.assertEqual(result["prediction"], "VIGILE")

    @patch('behavioral_unit.time.time')
    def test_ml_detects_malore(self, mock_time):
        """Test the system returning a MALORE state from the ML model."""
        # Force the fake model to detect a medical emergency
        self.mock_model.predict.return_value = ["MALORE"]
        
        # Fill buffer instantly to trigger prediction
        for i in range(5):
            mock_time.return_value = 100.0 + i
            self.unit.get_data()
            
        result = self.unit.get_data()
        self.assertEqual(result["prediction"], "MALORE")

if __name__ == '__main__':
    unittest.main(verbosity=2)