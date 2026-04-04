from dms_alcohol import DMSAlcohol
from dms_gyro import DMSGyro

class CriticalUnit:
    def __init__(self, shared_gyro=None):
        """
        Initializes the hardware abstraction layers for critical safety sensors.

        Args:
            shared_gyro: Optional shared DMSGyro instance to avoid I2C conflicts.
                         If None, a new DMSGyro is created internally.
        """
        print("Initializing Critical Unit...")
        self.alcohol_sensor = DMSAlcohol()
        self.gyro_sensor = shared_gyro if shared_gyro else DMSGyro()

    def get_data(self):
        """
        Polls the hardware sensors and formats the output to match 
        the PriorityArbitrator contract.
        
        Returns:
            dict: {"crash_detected": bool, "alcohol_over_limit": bool}
        """
        # Baseline safe state
        critical_data = {
            "crash_detected": False,
            "alcohol_over_limit": False
        }

        # --- 1. ALCOHOL CHECK ---
        alc_status = self.alcohol_sensor.get_status()
        # If the HAL dictionary returns a DANGER command, the threshold is exceeded
        if alc_status and alc_status.get("led_command") == "DANGER":
            critical_data["alcohol_over_limit"] = True

        # --- 2. GYROSCOPE CRASH CHECK ---
        gyro_status = self.gyro_sensor.get_status()
        # If the HAL dictionary returns a DANGER command, G-force > 5.0G
        if gyro_status and gyro_status.get("led_command") == "DANGER":
            critical_data["crash_detected"] = True

        return critical_data

    def stop(self):
        """Safely shuts down the hardware sensors."""
        self.alcohol_sensor.stop()
        self.gyro_sensor.stop()