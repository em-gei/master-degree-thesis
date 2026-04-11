import time
import sys
import os
import warnings
from datetime import datetime

# --headless flag: run without a display (SSH / no monitor).
# Without the flag, OpenCV windows are shown normally (desktop mode).
if "--headless" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["DMS_HEADLESS"] = "1"
    sys.argv.remove("--headless")

# --- SUPPRESS NOISY THIRD-PARTY WARNINGS ---
# scikit-learn version mismatch warning (model trained with different version)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*Trying to unpickle estimator.*")
# protobuf SymbolDatabase.GetPrototype() deprecation warning (from MediaPipe)
warnings.filterwarnings("ignore", message=".*SymbolDatabase.GetPrototype.*")
# libcamera verbose INFO logs
os.environ["LIBCAMERA_LOG_LEVELS"] = "ERROR"

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

    # Suppress C++ stderr spam (Qt fonts, TensorFlow, MediaPipe) during init.
    # These warnings come from native libraries and cannot be filtered via Python.
    sys.stderr.flush()
    _stderr_fd_backup = os.dup(2)
    _devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(_devnull_fd, 2)

    environment_unit = EnvironmentUnit()
    # Model path is relative to the project root (one level above src/)
    _project_root = os.path.dirname(_base)
    _model_path = os.path.join(_project_root, "src", "lightgbm_model.pkl")
    behavioral_unit = BehavioralUnit(shared_gyro_sensor=shared_gyro, model_path=_model_path)

    # Restore stderr
    os.dup2(_stderr_fd_backup, 2)
    os.close(_devnull_fd)
    os.close(_stderr_fd_backup)
    
    # 3. INITIALIZE DECISION ENGINE
    arbitrator = PriorityArbitrator()

    print("\nAll systems nominal. Starting main monitoring loop...\n")
    last_log_time = 0.0
    session_log = []  # Stores log entries for file export on shutdown

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
            # The LED matrix is the primary feedback device when driving (no monitor).
            # Pattern selection mirrors the rich mapping from dms_core.py:
            #   X (danger)  = crash, alcohol, gas, malore, sonnolenza       -> ALERT
            #   Arrow       = distraction direction (left / right / down)   -> WARNING
            #   Line        = environmental alert (heat, low light, audio)  -> WARNING
            #   Dot         = normal / vigile                               -> SAFE
            if led_system.active:
                if action == arbitrator.ACTION_CRITICAL_STOP:
                    # All critical stops show X (crash, alcohol, gas, malore)
                    led_system.signal_danger()
                elif action == arbitrator.ACTION_ALARM_HIGH:
                    # Sonnolenza -> X (driver may be falling asleep)
                    led_system.signal_danger()
                elif action == arbitrator.ACTION_ALARM_LOW:
                    # Distrazione -> use camera data for direction
                    cam_raw = ml_data.get("_cam_raw", {})
                    yaw = cam_raw.get("yaw", 0.0)
                    pitch = cam_raw.get("pitch", 0.0)
                    if pitch < -20:
                        led_system.signal_distraction_down()
                    elif yaw < -20:
                        led_system.signal_distraction_sx()
                    elif yaw > 20:
                        led_system.signal_distraction_dx()
                    else:
                        led_system.signal_alert()
                elif warnings:
                    # Environmental warnings (heat, low light, audio) -> horizontal line
                    led_system.signal_alert()
                else:
                    led_system.signal_safe()    # Normal driving -> dot

            # --- D. SYSTEM LOGGING (throttled to 1 Hz) ---
            if time.time() - last_log_time >= 1.0:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                warning_text = f" | Warnings: {len(warnings)}" if warnings else ""
                log_line = f"[{timestamp}] Action: {action} | Reason: {reason}{warning_text}"
                print(log_line)
                session_log.append(log_line)
                last_log_time = time.time()

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

        # --- SAVE SESSION LOG ---
        if session_log:
            log_dir = os.path.join(os.path.dirname(_base), "session_logs")
            os.makedirs(log_dir, exist_ok=True)
            log_filename = f"dms_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_path = os.path.join(log_dir, log_filename)
            with open(log_path, "w") as f:
                f.write("\n".join(session_log) + "\n")
            print(f"Session log saved to: {log_path}")

        print("Shutdown complete. Goodbye!")

if __name__ == "__main__":
    main()