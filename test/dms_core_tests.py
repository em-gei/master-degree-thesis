import unittest
import numpy as np
import dms_core

# --- MOCK CLASS TO SIMULATE MEDIAPIPE ---
class MockLandmark:
    """
    This class simulates a single MediaPipe point (Landmark).
    MediaPipe returns objects with .x and .y properties, so we
    create fake objects with the same properties to fool the functions.
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

class TestDMSLogicAndMath(unittest.TestCase):
    
    def setUp(self):
        """
        Set up the test environment before EACH test.
        Initializes fake landmarks and camera matrix.
        """
        # Print a header to see which test is running in the logs
        print(f"\n🔵 {self._testMethodName}")

        self.width = 640
        self.height = 480
        
        # Create a list of 478 "empty" landmarks (all 0,0)
        self.fake_landmarks = [MockLandmark(0.0, 0.0) for _ in range(478)]

    def tearDown(self):
        """Executed after each test"""
        # If we reach this point without errors, the test passed
        # (If assertion fails, unittest stops before this)
        pass

    # --- DECISION LOGIC TESTS ---
    def test_case_safe_driving(self):
        """Test: Normal driving (Head straight, Eyes open)"""
        print("   Context: Pitch=0, Yaw=0, EAR=0.30 (Open), Counter=0")
        
        result = dms_core.analyze_driver_state(pitch=0, yaw=0, avg_ear=0.30, blink_counter=0)
        
        self.assertEqual(result["led_command"], "SAFE")
        self.assertEqual(result["blink_counter"], 0)
        self.assertFalse(result["alarm_triggered"])
        print("   ✅ PASSED: System correctly identified Safe Driving.")

    def test_case_cellphone_distraction(self):
        """Test: Cellphone Distraction (Head down, Eyes open)"""
        print("   Context: Pitch=-25 (Down), EAR=0.30 (Open)")
        
        # We simulate looking down (-25 degrees) with eyes open
        result = dms_core.analyze_driver_state(pitch=-25, yaw=0, avg_ear=0.30, blink_counter=5) 
        
        # Expectation: DOWN command and blink counter reset
        self.assertEqual(result["led_command"], "DOWN")
        self.assertIn("CELLULARE", result["text"])
        self.assertEqual(result["blink_counter"], 0, "Blink counter should reset if looking at phone")
        print("   ✅ PASSED: System correctly identified Cellphone distraction.")

    def test_case_microsleep_head_drop(self):
        """Test: Microsleep / Head Drop (Head down, Eyes closed)"""
        print("   Context: Pitch=-25 (Down), EAR=0.15 (Closed)")
        
        current_counter = 2
        result = dms_core.analyze_driver_state(pitch=-25, yaw=0, avg_ear=0.15, blink_counter=current_counter)
        
        # Expectation: DANGER command and rapid counter increase
        self.assertEqual(result["led_command"], "DANGER")
        self.assertIn("COLPO DI SONNO", result["text"])
        self.assertTrue(result["alarm_triggered"])
        self.assertGreater(result["blink_counter"], current_counter + 2, "Counter should increase rapidly")
        print("   ✅ PASSED: System correctly identified Head Drop Microsleep.")

    def test_case_standard_drowsiness(self):
        """Test: Standard Drowsiness (Head straight, Eyes closed for long time)"""
        threshold = dms_core.EAR_FRAMES_PER_ALARM
        print(f"   Context: Pitch=0, EAR=0.15, Counter={threshold} (Threshold reached)")
        
        result = dms_core.analyze_driver_state(pitch=0, yaw=0, avg_ear=0.15, blink_counter=threshold)
        
        self.assertEqual(result["led_command"], "DANGER")
        self.assertIn("SONNOLENZA", result["text"])
        self.assertTrue(result["alarm_triggered"])
        print("   ✅ PASSED: System correctly identified Standard Drowsiness.")

    def test_case_side_distraction(self):
        """Test: Side Distraction (High Yaw)"""
        print("   Context: Yaw=-30 (Looking Left)")
        
        result = dms_core.analyze_driver_state(pitch=0, yaw=-30, avg_ear=0.30, blink_counter=5)
        
        self.assertEqual(result["led_command"], "SX")
        self.assertIn("DISTRATTO", result["text"])
        # Counter should decrease slowly, not full reset
        self.assertEqual(result["blink_counter"], 4)
        print("   ✅ PASSED: System correctly identified Side Distraction.")       


    # --- MATHEMATICAL TESTS ---
    def test_ear_calculation(self):
        """Test: Verify EAR calculation formula"""
        print("   Context: Simulating open eye coordinates...")
        
        # Simulate an OPEN eye using specific landmark indices
        self.fake_landmarks[362] = MockLandmark(0.1, 0.5) 
        self.fake_landmarks[263] = MockLandmark(0.3, 0.5)
        self.fake_landmarks[385] = MockLandmark(0.2, 0.4) 
        self.fake_landmarks[387] = MockLandmark(0.2, 0.4)
        self.fake_landmarks[373] = MockLandmark(0.2, 0.6) 
        self.fake_landmarks[380] = MockLandmark(0.2, 0.6)
        
        ear = dms_core.calculate_ear(self.fake_landmarks, dms_core.LEFT_EYE, 100, 100)
        self.assertGreater(ear, 0.25)
        print(f"   ✅ PASSED: Calculated EAR is {ear:.2f} (Expected > 0.25)")

    def test_config_validity(self):
        """Test: Verify configuration constants are valid"""
        print("   Context: Checking global constants...")
        
        self.assertLess(dms_core.PITCH_DOWN_THRESH, 0, "Pitch Down Threshold must be negative")
        self.assertGreater(dms_core.EAR_THRESHOLD, 0.10, "EAR Threshold too low")
        print("   ✅ PASSED: Configuration parameters are valid.")

if __name__ == '__main__':
    unittest.main()