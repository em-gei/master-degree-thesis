import time
import cv2

# --- HARDWARE & UI IMPORTS ---
try:
    from dms_led import DMSLed
    from dms_gyro import DMSGyro
except ImportError:
    print("Hardware modules not found. Make sure you are on the Raspberry Pi.")

# --- ARCHITECTURE UNITS IMPORTS ---
from critical_unit import CriticalUnit
from environment_unit import EnvironmentUnit
from behavioral_unit import BehavioralUnit
from priority_arbitrator import PriorityArbitrator

def main():
    print("==================================================")
    print("   STARTING DRIVER MONITORING SYSTEM (DMS) V2.0   ")
    print("==================================================")

    # 1. INITIALIZE SHARED HARDWARE
    # The Gyroscope is instantiated here and shared between Critical and Behavioral units
    # to prevent I2C bus address conflicts.
    shared_gyro = DMSGyro()
    led_system = DMSLed()

    # 2. INITIALIZE ARCHITECTURE UNITS
    critical_unit = CriticalUnit()
    critical_unit.gyro_sensor = shared_gyro # Inject shared gyro
    
    environment_unit = EnvironmentUnit()
    behavioral_unit = BehavioralUnit(shared_gyro_sensor=shared_gyro)
    
    # 3. INITIALIZE DECISION ENGINE
    arbitrator = PriorityArbitrator()

    print("\nAll systems nominal. Starting main monitoring loop...\n")
    
    try:
        while True:
            loop_start = time.time()

            # --- A. DATA ACQUISITION (Level 2: Units) ---
            critical_data = critical_unit.get_data()
            env_data = environment_unit.get_data()
            ml_data = behavioral_unit.get_data()

            # --- B. DECISION MAKING (Level 3: Arbitrator) ---
            decision = arbitrator.evaluate_system_state(critical_data, ml_data, env_data)
            
            action = decision["primary_action"]
            reason = decision["trigger_reason"]
            warnings = decision["active_warnings"]

            # --- C. EXECUTION & UI (Level 4: Output) ---
            if led_system.active:
                if action == arbitrator.ACTION_CRITICAL_STOP:
                    led_system.signal_danger()
                elif action == arbitrator.ACTION_ALARM_HIGH:
                    led_system.signal_danger()  # Or a specific Sonnolenza pattern
                elif action == arbitrator.ACTION_ALARM_LOW:
                    led_system.signal_alert()   # Alert pattern for Distrazione
                else:
                    led_system.signal_safe()    # Normal driving

            # --- D. SYSTEM LOGGING ---
            # Print a clean status line to the console (overwriting the same line)
            warning_text = f" | Warnings: {len(warnings)}" if warnings else ""
            print(f"\r[DMS STATUS] Action: {action} | Reason: {reason}{warning_text}      ", end="")

            # Graphic event processing for OpenCV windows
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n\nUser requested shutdown ('q' pressed).")
                break
            
            # Optional: cap the loop rate to avoid 100% CPU usage if needed
            # (Though OpenCV and I2C reads usually act as natural bottlenecks)
            loop_time = time.time() - loop_start
            if loop_time < 0.05: # Cap at ~20 FPS
                time.sleep(0.05 - loop_time)

    except KeyboardInterrupt:
        print("\n\nSystem interrupted by user (Ctrl+C).")
    
    finally:
        # --- TEARDOWN & CLEANUP ---
        print("Cleaning up hardware and terminating threads...")
        critical_unit.stop()
        environment_unit.stop()
        behavioral_unit.stop()
        cv2.destroyAllWindows()
        print("Shutdown complete. Goodbye!")

if __name__ == "__main__":
    main()