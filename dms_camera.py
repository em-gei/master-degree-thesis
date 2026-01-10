import time
import cv2
import numpy as np
import mediapipe as mp

try:
    from picamera2 import Picamera2
except ImportError:
    print("⚠️ Camera module not found")

# --- CONFIGURATION PARAMETERS ---
EAR_THRESHOLD = 0.20        
EAR_FRAMES_PER_ALARM = 10
# Distraction thresholds (degrees)
YAW_THRESH = 20             
PITCH_DOWN_THRESH = -20     

class DMSCamera:
    def __init__(self):
        print("Inizializzazione Camera")
        try:
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(main={"size": (640, 480), "format": "XRGB8888"})
            self.picam2.configure(config)
            self.picam2.start()
        except Exception as e:
            print(f"Camera Error: {e}")
            return

        self.blink_counter = 0
        self.alarm_trigger_time = 0
        self.system_status = "INIZIALIZZAZIONE"
        self.status_color = (255, 255, 255)
        
        # Initialize MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
        
        # --- Generic 3D face model ---
        self.face_3d = np.array([
            (0.0, 0.0, 0.0),            # Nose
            (0.0, -330.0, -65.0),       # Chin
            (-225.0, 170.0, -135.0),    # Left eye
            (225.0, 170.0, -135.0),     # Right eye
            (-150.0, -150.0, -125.0),   # Left mouth
            (150.0, -150.0, -125.0)     # Right mouth
        ], dtype=np.float64)
        
        self.FACE_3D_INDEXES = [1, 199, 33, 263, 61, 291]
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        

    def calculate_ear(self, landmarks, indices, w, h):
        coords = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in indices])
        v1 = np.linalg.norm(coords[1] - coords[5])
        v2 = np.linalg.norm(coords[2] - coords[4])
        hor = np.linalg.norm(coords[0] - coords[3])
        return (v1 + v2) / (2.0 * hor)
    

    def get_head_pose(self, landmarks, w, h, cam_matrix, dist_matrix):
        face_2d = []
        for idx in self.FACE_3D_INDEXES:
            x, y = int(landmarks[idx].x * w), int(landmarks[idx].y * h)
            face_2d.append([x, y])
        face_2d = np.array(face_2d, dtype=np.float64)
        _, rot_vec, _ = cv2.solvePnP(self.face_3d, face_2d, cam_matrix, dist_matrix)
        rmat, _ = cv2.Rodrigues(rot_vec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        return angles[0], angles[1], angles[2]
    

    def analyze_driver_state(self, pitch, yaw, avg_ear):
        # Determines driver status based on sensor data
        # Returns a dictionary with the state, color, new counter, and LED command
        
        result = {
            "alarm_triggered": False,
            "blink_counter": 0,
            "color": (0, 255, 0),
            "led_command": "SAFE",
            "text": "GUIDA SICURA"
        }

        # CASE 1: HEAD DOWN (Maximum Priority)
        if pitch < PITCH_DOWN_THRESH:
            # A: Eyes Open -> Cell Phone
            if avg_ear > EAR_THRESHOLD:
                result["text"] = "DISTRATTO: CELLULARE (Testa Giu)"
                result["color"] = (0, 255, 255) # Giallo
                result["blink_counter"] = 0
                result["led_command"] = "DOWN"
            # B: Eyes Closed -> Dozing Off
            else:
                result["text"] = "ALLARME: COLPO DI SONNO!"
                result["color"] = (0, 0, 255) # Rosso
                result["blink_counter"] = self.blink_counter + 5 # Rapid growth
                result["led_command"] = "DANGER"
                result["alarm_triggered"] = True

        # CASE 2: HEAD STRAIGHT BUT EYES CLOSED (Classic Drowsiness)
        elif avg_ear < EAR_THRESHOLD:
            new_counter = self.blink_counter + 1
            result["blink_counter"] = new_counter
            result["text"] = "Occhi Chiusi..."
            result["color"] = (100, 100, 255)
            
            if new_counter >= EAR_FRAMES_PER_ALARM:
                result["text"] = "ALLARME: SONNOLENZA!"
                result["color"] = (0, 0, 255)
                result["led_command"] = "DANGER"
                result["alarm_triggered"] = True

        # CASE 3: LATERAL DISTRACTION
        elif abs(yaw) > YAW_THRESH:
            result["text"] = f"DISTRATTO: {'SX' if yaw < 0 else 'DX'}"
            result["color"] = (0, 255, 255)
            result["blink_counter"] = max(0, self.blink_counter - 1)        
            if yaw < 0:
                result["led_command"] = "SX"
            else:
                result["led_command"] = "DX"

        # CASE 4: SAFE DRIVING (None of the above conditions are met)
        else:
            result["blink_counter"] = 0 # Reset
            result["led_command"] = "SAFE"

        return result
    

    def get_status(self):
        w, h = 640, 480
        focal_length = 1 * w
        cam_matrix = np.array([[focal_length, 0, w/2], [0, focal_length, h/2], [0, 0, 1]])
        dist_matrix = np.zeros((4, 1), dtype=np.float64)
        
        image = self.picam2.capture_array()
        if image is None: return
        if image.shape[2] == 4: image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        
        image.flags.writeable = False
        results = self.face_mesh.process(image)
        image.flags.writeable = True
        anonymous_view = np.zeros((h, w, 3), dtype=np.uint8)

        current_status = "GUIDA SICURA"
        current_color = (0, 255, 0)
        
        pitch, yaw, avg_ear = 0, 0, 0
        decision = None
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                lm = face_landmarks.landmark
                left_ear = self.calculate_ear(lm, self.LEFT_EYE, w, h)
                right_ear = self.calculate_ear(lm, self.RIGHT_EYE, w, h)
                avg_ear = (left_ear + right_ear) / 2.0
                pitch, yaw, _ = self.get_head_pose(lm, w, h, cam_matrix, dist_matrix)

                decision = self.analyze_driver_state(pitch, yaw, avg_ear)
                current_status = decision["text"]
                current_color = decision["color"]
                self.blink_counter = decision["blink_counter"]
                
                if decision["alarm_triggered"]:
                    self.alarm_trigger_time = time.time()
                    
                if decision["led_command"] == "SAFE":
                    # Alarm persistence management (2 seconds)
                    if time.time() - self.alarm_trigger_time < 2.0:
                        current_status = "ALLARME (Persistenza)"
                        current_color = (0, 0, 255)
                        decision["led_command"] = "DANGER"

                for idx in self.LEFT_EYE + self.RIGHT_EYE + self.FACE_3D_INDEXES:
                    pt = (int(lm[idx].x * w), int(lm[idx].y * h))
                    cv2.circle(anonymous_view, pt, 2, current_color, -1)
        else:
            current_status = "NESSUN VOLTO RILEVATO"
            self.blink_counter = 0
            decision = {
                "alarm_triggered": False,
                "blink_counter": self.blink_counter,
                "color": current_color,
                "led_command": "ALERT",
                "text": current_status
            }

        # UI Text
        cv2.putText(anonymous_view, current_status, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, current_color, 2)
        debug_info = f"EAR: {avg_ear:.2f} | P: {int(pitch)} | Y: {int(yaw)}"
        cv2.putText(anonymous_view, debug_info, (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        cv2.imshow('DMS', anonymous_view)
        return decision
    

    def stop(self):
        self.picam2.stop()