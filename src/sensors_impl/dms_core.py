import time
import cv2

# Hardware / Module Imports
try:
    from dms_led import DMSLed
    from dms_audio import DMSAudio
    from dms_camera import DMSCamera
    from dms_temp import DMSTemp
    from dms_alcohol import DMSAlcohol
    from dms_light import DMSLight
    from dms_air import DMSAir
    from dms_gyro import DMSGyro
except ImportError:
    print("Hardware modules not found")

def main():
    # --- SETUP ---
    print("Avvio Sistemi...")
    led_system = DMSLed()
    camera_system = DMSCamera()
    audio_system = DMSAudio(device_index=0, threshold_db=85) 
    audio_system.start_listening()
    temperature_system = DMSTemp()
    alcohol_system = DMSAlcohol()
    light_system = DMSLight()
    air_system = DMSAir()
    gyro_system = DMSGyro()
    last_temp_check = 0
    last_light_check = 0
    
    while True:      
        gyro_decision = gyro_system.get_status()
        alc_decision = alcohol_system.get_status()
        air_decision = air_system.get_status()
        cam_decision = camera_system.get_status()
        
        if audio_system.crash_detected:
            print("CRITICAL ERROR: ACCIDENT DETECTED (AUDIO)")
            led_system.signal_danger()
            exit()
        
        if gyro_decision and gyro_decision["led_command"] == "DANGER":
            print(f"CRASH DETECTED: {gyro_decision['g_force']:.1f} G")
            led_system.signal_danger()
            exit()
        
        if time.time() - last_temp_check > 5.0: # every 5 seconds
            temp_decision = temperature_system.get_status()
            last_temp_check = time.time()
        
        if time.time() - last_light_check > 5.0:
            light_decision = light_system.get_status()
            last_light_check = time.time()
            print(light_decision['ui_text'], light_decision['lux_value'])
        
        final_led_cmd = "SAFE"
        if alc_decision and alc_decision["led_command"] == "DANGER":
            final_led_cmd = "DANGER"        
        elif cam_decision is not None and cam_decision.get("led_command") in ["DANGER", "DOWN", "SX", "DX"]:
            final_led_cmd = cam_decision.get("led_command", "SAFE")
        elif air_decision and air_decision["led_command"] == "ALERT":
            final_led_cmd = "ALERT" 
        elif temp_decision and temp_decision["led_command"] == "ALERT":
            final_led_cmd = "ALERT"
        # Low priority
        elif cam_decision is not None and cam_decision.get("led_command") == "ALERT":
            final_led_cmd = "ALERT"

        if led_system:
            if final_led_cmd == "DOWN": led_system.signal_distraction_down()
            elif final_led_cmd == "DANGER": led_system.signal_danger()
            elif final_led_cmd == "SX": led_system.signal_distraction_sx()
            elif final_led_cmd == "DX": led_system.signal_distraction_dx()
            elif final_led_cmd == "ALERT": led_system.signal_alert()
            elif final_led_cmd == "SAFE": led_system.signal_safe()

        # waitKey it's used to process graphic events from cv2.imshow
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    # Cleanup
    print("Chiusura in corso...")
    audio_system.stop()
    camera_system.stop()
    temperature_system.stop()
    alcohol_system.stop()
    air_system.stop()
    light_system.stop()
    gyro_system.stop()
    cv2.destroyAllWindows()
    led_system.close()

if __name__ == "__main__":
    main()