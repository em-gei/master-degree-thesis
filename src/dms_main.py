import time
import sys
import os

# --headless flag: run without a display (SSH / no monitor).
# Without the flag, OpenCV windows are shown normally (desktop mode).
if "--headless" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.argv.remove("--headless")

# Suppress Qt font warnings by pointing to system fonts if available.
_sys_fonts = "/usr/share/fonts/truetype"
if os.path.isdir(_sys_fonts):
    os.environ.setdefault("QT_QPA_FONTDIR", _sys_fonts)

import cv2

# --- PATH SETUP ---
# Add source directories so bare imports work regardless of PYTHONPATH.
_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_base, 'sensors_impl'))
sys.path.insert(0, os.path.join(_base, 'units_impl'))

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
    critical_unit = CriticalUnit(shared_gyro=shared_gyro)
    
    environment_unit = EnvironmentUnit()
    # Model path is relative to the project root (one level above src/)
    _project_root = os.path.dirname(_base)
    _model_path = os.path.join(_project_root, "lightgbm_model.pkl")
    behavioral_unit = BehavioralUnit(shared_gyro_sensor=shared_gyro, model_path=_model_path)
    
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
        led_system.close()
        cv2.destroyAllWindows()
        print("Shutdown complete. Goodbye!")

if __name__ == "__main__":
    main()