import time
import cv2
import numpy as np
import mediapipe as mp

# Hardware / Module Imports
try:
    from dms_led import DMSLed
    from dms_audio import DMSAudio
    from dms_camera import DMSCamera
    from dms_temp import DMSTemp
except ImportError:
    print("⚠️ Hardware modules not found")

def main():
    # --- SETUP ---
    led_system = DMSLed()
    camera_system = DMSCamera()
    audio_system = DMSAudio(device_index=0, threshold_db=85) 
    audio_system.start_listening()
    temperature_system = DMSTemp()
    last_temp_check = 0
    
    while True:        
        if audio_system.crash_detected:
            print("🚨 CRITICAL ERROR: INCIDENTE RILEVATO (AUDIO)")
            led_system.signal_danger()
            exit()
        
        if time.time() - last_temp_check > 5.0:
            temp_decision = temperature_system.get_status()
            last_temp_check = time.time()
        
        decision = camera_system.get_status()
        if decision is not None and led_system is not None:
            cmd = decision.get("led_command", "SAFE")
            if cmd == "DOWN": led_system.signal_distraction_down()
            elif cmd == "DANGER": led_system.signal_danger()
            elif cmd == "SX": led_system.signal_distraction_sx()
            elif cmd == "DX": led_system.signal_distraction_dx()
            elif cmd == "ALERT": led_system.signal_alert()
            elif cmd == "SAFE": led_system.signal_safe()
        elif led_system is not None and decision is None:
            led_system.signal_alert()

        # waitKey it's used to process graphic events from cv2.imshow
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    # Cleanup
    print("Chiusura in corso...")
    audio_system.stop()
    camera_system.stop()
    temperature_system.stop()
    cv2.destroyAllWindows()
    led_system.close()

if __name__ == "__main__":
    main()