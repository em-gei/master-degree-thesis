import unittest
import numpy as np
import dms_core

# --- MOCK CLASS TO SIMULATE MEDIAPIPE ---
class MockLandmark:
    # This class simulates a single MediaPipe point (Landmark).
    # MediaPipe returns objects with .x and .y properties, so we
    # create fake objects with the same properties to fool the functions.
    def __init__(self, x, y):
        self.x = x
        self.y = y

class TestDMSAlgorithms(unittest.TestCase):
    
    def setUp(self):
        # Before each test, setup the environment
        self.width = 640
        self.height = 480
        
        # Camera matrix setup
        focal_length = 1 * self.width
        self.cam_matrix = np.array([[focal_length, 0, self.width/2], 
                                    [0, focal_length, self.height/2], 
                                    [0, 0, 1]])
        self.dist_matrix = np.zeros((4, 1), dtype=np.float64)

        # Let's create a list of 478 "empty" landmarks (all 0,0)
        # 478 is the default number of points in MediaPipe Face Mesh
        self.fake_landmarks = [MockLandmark(0.0, 0.0) for _ in range(478)]

    def test_ear_calculation_open_eye(self):
        # Verify that an open eye returns a high EAR
        print("\nTesting: Calcolo EAR Occhio Aperto...")
        
        # Left eye indices used in dms_core:
        # [362, 385, 387, 263, 373, 380]
        # P0 (sx), P1(su1), P2(su2), P3(dx), P4(giu2), P5(giu1)
        # Let's simulate an OPEN eye
        # X-coordinates (horizontal): P0 at 10px, P3 at 30px (Width 20)
        self.fake_landmarks[362] = MockLandmark(0.1, 0.5) # left
        self.fake_landmarks[263] = MockLandmark(0.3, 0.5) # right
        # Y-coordinates (vertical): Eyelid on at 0.4, down at 0.6
        self.fake_landmarks[385] = MockLandmark(0.2, 0.4) # up1
        self.fake_landmarks[387] = MockLandmark(0.2, 0.4) # up2
        self.fake_landmarks[373] = MockLandmark(0.2, 0.6) # down2
        self.fake_landmarks[380] = MockLandmark(0.2, 0.6) # down1
        
        ear = dms_core.calculate_ear(self.fake_landmarks, dms_core.LEFT_EYE, 100, 100)
        
        print(f" -> EAR Calcolato: {ear}")
        self.assertGreater(ear, 0.25, "L'EAR per un occhio aperto dovrebbe essere alto")

    def test_ear_calculation_closed_eye(self):
        # Verify that a closed eye gives a low EAR
        print("\nTesting: Calcolo EAR Occhio Chiuso...")
        
        # Let's simulate a CLOSED eye (Almost coinciding vertical points)
        self.fake_landmarks[362] = MockLandmark(0.1, 0.5) 
        self.fake_landmarks[263] = MockLandmark(0.3, 0.5)
        # Eyelids very close together (almost the same Y)
        self.fake_landmarks[385] = MockLandmark(0.2, 0.49) 
        self.fake_landmarks[387] = MockLandmark(0.2, 0.49)
        self.fake_landmarks[373] = MockLandmark(0.2, 0.51) 
        self.fake_landmarks[380] = MockLandmark(0.2, 0.51)
        
        ear = dms_core.calculate_ear(self.fake_landmarks, dms_core.LEFT_EYE, 100, 100)
        
        print(f" -> EAR Calcolato: {ear}")
        self.assertLess(ear, 0.15, "L'EAR per un occhio chiuso dovrebbe essere basso")

    def test_head_pose_robustness(self):
        # Verify that get_head_pose doesn't crash and return 3 values
        print("\nTesting: Robustezza Head Pose...")
        
        # We initialize all points to the center
        for i in range(478):
            self.fake_landmarks[i] = MockLandmark(0.5, 0.5)

        # Move the key points to create a "real" face otherwise solvePnP will crash (mathematical singularity)
        # The indexes used in dms_core are: [1, 199, 33, 263, 61, 291]
        # 1: Nose (Center)
        self.fake_landmarks[1] = MockLandmark(0.5, 0.5)
        # 199: Chin (Down)
        self.fake_landmarks[199] = MockLandmark(0.5, 0.8)
        # 33: Left eye (Left, Up)
        self.fake_landmarks[33] = MockLandmark(0.3, 0.3)
        # 263: Right eye (Right, Up)
        self.fake_landmarks[263] = MockLandmark(0.7, 0.3)
        # 61: Left mouth (Left, Down)
        self.fake_landmarks[61] = MockLandmark(0.4, 0.7)
        # 291: Right mouth (Right, Down)
        self.fake_landmarks[291] = MockLandmark(0.6, 0.7)
            
        try:
            pitch, yaw, roll = dms_core.get_head_pose(
                self.fake_landmarks, 
                self.width, 
                self.height, 
                self.cam_matrix, 
                self.dist_matrix
            )
            print(f" -> Output Posa: Pitch={pitch:.2f}, Yaw={yaw:.2f}, Roll={roll:.2f}")
            
            # Verify values are float (not None / errors)
            self.assertIsInstance(pitch, float)
            self.assertIsInstance(yaw, float)
            self.assertIsInstance(roll, float)
            
        except Exception as e:
            self.fail(f"get_head_pose ha generato un errore imprevisto: {e}")

    def test_thresholds_logic(self):
        # Verify that the configuration thresholds make sense
        print("\nTesting: Verifica Configurazione...")
        self.assertTrue(0 < dms_core.EAR_THRESHOLD < 1, "La soglia EAR deve essere un numero tra 0 e 1")
        self.assertGreater(dms_core.EAR_FRAMES_PER_ALARM, 0)

if __name__ == '__main__':
    unittest.main()
