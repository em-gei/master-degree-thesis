import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Stub hardware/heavy modules before importing dms_camera so module-level
# imports don't fail or conflict with mocked numpy from other test files.
for _mod in ('cv2', 'mediapipe', 'picamera2'):
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))
import dms_camera

# --- MOCK CLASS TO SIMULATE MEDIAPIPE ---
class MockLandmark:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class TestDMSCameraLogic(unittest.TestCase):
    
    @patch('dms_camera.Picamera2')
    def setUp(self, _):
        print(f"\n{self._testMethodName}")
        self.cam_system = dms_camera.DMSCamera()
        self.cam_system.blink_counter = 0
        self.fake_landmarks = [MockLandmark(0.0, 0.0) for _ in range(478)]


    def test_case_safe_driving(self):
        """Test: Normal driving"""
        print("   Context: Pitch=0, Yaw=0, EAR=0.30")
        result = self.cam_system.analyze_driver_state(pitch=0, yaw=0, avg_ear=0.30)
        
        self.assertEqual(result["led_command"], "SAFE")
        self.assertEqual(result["blink_counter"], 0)
        self.assertFalse(result["alarm_triggered"])
        print("PASSED: Safe Driving identified.")
        

    def test_case_cellphone_distraction(self):
        """Test: Cellphone Distraction (Head down, Eyes open)"""
        print("   Context: Pitch=-25, EAR=0.30")
        result = self.cam_system.analyze_driver_state(pitch=-25, yaw=0, avg_ear=0.30)
        
        self.assertEqual(result["led_command"], "DOWN")
        self.assertIn("CELLULARE", result["text"])
        print("PASSED: Cellphone distraction identified.")
        

    def test_case_microsleep(self):
        """Test: Microsleep (Head down, Eyes closed)"""
        print("   Context: Pitch=-25, EAR=0.15")
        # Simulate counter value equals 2
        self.cam_system.blink_counter = 2
        
        result = self.cam_system.analyze_driver_state(pitch=-25, yaw=0, avg_ear=0.15)
        
        self.assertEqual(result["led_command"], "DANGER")
        self.assertTrue(result["alarm_triggered"])
        self.assertEqual(result["blink_counter"], 7)
        print("PASSED: Microsleep identified.")


    def test_case_side_distraction(self):
        """Test: Side Distraction"""
        print("   Context: Yaw=-30")
        result = self.cam_system.analyze_driver_state(pitch=0, yaw=-30, avg_ear=0.30)
        self.assertEqual(result["led_command"], "SX")
        print("PASSED: Side Distraction identified.")


    def test_ear_calculation(self):
        """Test: Verify EAR calculation formula"""
        # Simulate an OPEN eye
        self.fake_landmarks[362] = MockLandmark(0.1, 0.5) 
        self.fake_landmarks[263] = MockLandmark(0.3, 0.5)
        self.fake_landmarks[385] = MockLandmark(0.2, 0.4) 
        self.fake_landmarks[387] = MockLandmark(0.2, 0.4)
        self.fake_landmarks[373] = MockLandmark(0.2, 0.6) 
        self.fake_landmarks[380] = MockLandmark(0.2, 0.6)
        
        ear = self.cam_system.calculate_ear(self.fake_landmarks, self.cam_system.LEFT_EYE, 100, 100)
        self.assertGreater(ear, 0.25)
        print(f"PASSED: Calculated EAR is {ear:.2f}")

if __name__ == '__main__':
    unittest.main()