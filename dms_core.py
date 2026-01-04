import time
import cv2
import numpy as np
import mediapipe as mp
from dms_audio import DMSAudio

# Import management to allow testing even without hardware
try:
    from picamera2 import Picamera2
    from dms_led import DMSLed
except ImportError:
    print("⚠️ Hardware modules not found (Running in Test/Emulation mode)")

# --- CONFIGURATION PARAMETERS ---
EAR_THRESHOLD = 0.20        
EAR_FRAMES_PER_ALARM = 10   
# Distraction thresholds (degrees)
YAW_THRESH = 20             
PITCH_DOWN_THRESH = -20     

# --- Generic 3D face model ---
face_3d = np.array([
    (0.0, 0.0, 0.0),            # Nose
    (0.0, -330.0, -65.0),       # Chin
    (-225.0, 170.0, -135.0),    # Left eye
    (225.0, 170.0, -135.0),     # Right eye
    (-150.0, -150.0, -125.0),   # Left mouth
    (150.0, -150.0, -125.0)     # Right mouth
], dtype=np.float64)

FACE_3D_INDEXES = [1, 199, 33, 263, 61, 291]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def calculate_ear(landmarks, indices, w, h):
    coords = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in indices])
    v1 = np.linalg.norm(coords[1] - coords[5])
    v2 = np.linalg.norm(coords[2] - coords[4])
    hor = np.linalg.norm(coords[0] - coords[3])
    return (v1 + v2) / (2.0 * hor)

def get_head_pose(landmarks, w, h, cam_matrix, dist_matrix):
    face_2d = []
    for idx in FACE_3D_INDEXES:
        x, y = int(landmarks[idx].x * w), int(landmarks[idx].y * h)
        face_2d.append([x, y])
    face_2d = np.array(face_2d, dtype=np.float64)

    success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)
    rmat, jac = cv2.Rodrigues(rot_vec)
    angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)
    return angles[0], angles[1], angles[2]

def analyze_driver_state(pitch, yaw, avg_ear, blink_counter):
    # Determines driver status based on sensor data
    # Returns a dictionary with the state, color, new counter, and LED command
    
    result = {
        "text": "GUIDA SICURA",
        "color": (0, 255, 0),
        "blink_counter": 0,
        "led_command": "SAFE",
        "alarm_triggered": False
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
            result["blink_counter"] = blink_counter + 5 # Rapid growth
            result["led_command"] = "DANGER"
            result["alarm_triggered"] = True

    # CASE 2: HEAD STRAIGHT BUT EYES CLOSED (Classic Drowsiness)
    elif avg_ear < EAR_THRESHOLD:
        new_counter = blink_counter + 1
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
        result["blink_counter"] = max(0, blink_counter - 1)        
        if yaw < 0:
            result["led_command"] = "SX"
        else:
            result["led_command"] = "DX"

    # CASE 4: SAFE DRIVING (None of the above conditions are met)
    else:
        result["blink_counter"] = 0 # Reset
        result["led_command"] = "SAFE"

    return result

def main():
    print("Inizializzazione LED...")
    led_system = DMSLed()
    
    # --- SETUP AUDIO ---
    audio_system = DMSAudio(device_index=0, threshold_db=90) 
    audio_system.start_listening()
    # -------------------
    
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "XRGB8888"})
        picam2.configure(config)
        picam2.start()
    except Exception as e:
        print(f"Camera Error: {e}")
        return

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

    blink_counter = 0
    alarm_trigger_time = 0
    system_status = "INIZIALIZZAZIONE"
    status_color = (255, 255, 255)

    w, h = 640, 480
    focal_length = 1 * w
    cam_matrix = np.array([[focal_length, 0, w/2], [0, focal_length, h/2], [0, 0, 1]])
    dist_matrix = np.zeros((4, 1), dtype=np.float64)

    while True:
        image = picam2.capture_array()
        if image is None: continue
        if image.shape[2] == 4: image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        
        image.flags.writeable = False
        results = face_mesh.process(image)
        image.flags.writeable = True
        anonymous_view = np.zeros((h, w, 3), dtype=np.uint8)

        current_status = "GUIDA SICURA"
        current_color = (0, 255, 0)
        
        pitch, yaw, avg_ear = 0, 0, 0
        
        if audio_system.crash_detected:
            print("🚨 CRITICAL ERROR: INCIDENTE RILEVATO (AUDIO)")
            led_system.signal_danger()
            cv2.putText(anonymous_view, "CRASH DETECTED!", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
            cv2.imshow('DMS - Anonymous Core', anonymous_view)
            cv2.waitKey(1)
            time.sleep(5)
            audio_system.crash_detected = True
            exit()

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                lm = face_landmarks.landmark
                left_ear = calculate_ear(lm, LEFT_EYE, w, h)
                right_ear = calculate_ear(lm, RIGHT_EYE, w, h)
                avg_ear = (left_ear + right_ear) / 2.0
                pitch, yaw, roll = get_head_pose(lm, w, h, cam_matrix, dist_matrix)

                decision = analyze_driver_state(pitch, yaw, avg_ear, blink_counter)
                current_status = decision["text"]
                current_color = decision["color"]
                blink_counter = decision["blink_counter"]
                
                if decision["alarm_triggered"]:
                    alarm_trigger_time = time.time()

                # LED management based on the received command
                cmd = decision["led_command"]
                if cmd == "DOWN": led_system.signal_distraction_down()
                elif cmd == "DANGER": led_system.signal_danger()
                elif cmd == "SX": led_system.signal_distraction_sx()
                elif cmd == "DX": led_system.signal_distraction_dx()
                elif cmd == "SAFE":
                    # Alarm persistence management (2 seconds)
                    if time.time() - alarm_trigger_time < 2.0:
                        led_system.signal_danger()
                        current_status = "ALLARME (Persistenza)"
                        current_color = (0, 0, 255)
                    else:
                        led_system.signal_safe()

                for idx in LEFT_EYE + RIGHT_EYE + FACE_3D_INDEXES:
                    pt = (int(lm[idx].x * w), int(lm[idx].y * h))
                    cv2.circle(anonymous_view, pt, 2, current_color, -1)
        else:
            current_status = "NESSUN VOLTO RILEVATO"
            blink_counter = 0
            led_system.signal_safe()

        # UI Text
        cv2.putText(anonymous_view, current_status, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, current_color, 2)
        debug_info = f"EAR: {avg_ear:.2f} | P: {int(pitch)} | Y: {int(yaw)}"
        cv2.putText(anonymous_view, debug_info, (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        cv2.imshow('DMS', anonymous_view)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    audio_system.stop()
    picam2.stop()
    cv2.destroyAllWindows()
    led_system.close()

if __name__ == "__main__":
    main()