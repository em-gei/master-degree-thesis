import time
from dms_air import DMSAir
from dms_temp import DMSTemp
from dms_light import DMSLight
from dms_audio import DMSAudio

class EnvironmentUnit:
    def __init__(self):
        """
        Initializes the hardware abstraction layers for environmental sensors.
        """
        print("Initializing Environment Unit...")
        self.air_sensor = DMSAir()
        self.temp_sensor = DMSTemp()
        self.light_sensor = DMSLight()
        
        # Audio runs in a separate daemon thread to avoid blocking
        self.audio_sensor = DMSAudio(device_index=0, threshold_db=85)
        self.audio_sensor.start_listening()
        
        # --- THROTTLING TIMERS ---
        # Slow sensors (DHT11, I2C Light) will be polled infrequently 
        # to avoid freezing the main camera/gyro loop.
        self.last_temp_check = 0.0
        self.last_light_check = 0.0
        self.cached_temp_status = None
        self.cached_light_status = None

    def get_data(self):
        """
        Polls the environmental sensors (using caching for slow ones) and formats 
        the output to match the PriorityArbitrator contract.
        
        Returns:
            dict: {"gas_danger": bool, "heat_stress": bool, "low_light": bool, "audio_anomaly": bool}
        """
        # Baseline safe state
        env_data = {
            "gas_danger": False,
            "heat_stress": False,
            "low_light": False,
            "audio_anomaly": False
        }

        current_time = time.time()

        # --- 1. AIR QUALITY CHECK (Fast GPIO Read) ---
        air_status = self.air_sensor.get_status()
        if air_status and air_status.get("led_command") == "ALERT":
            env_data["gas_danger"] = True

        # --- 2. TEMPERATURE CHECK (Slow DHT11 Read - Every 5 seconds) ---
        if current_time - self.last_temp_check > 5.0:
            self.cached_temp_status = self.temp_sensor.get_status()
            self.last_temp_check = current_time

        if self.cached_temp_status and self.cached_temp_status.get("led_command") == "ALERT":
            env_data["heat_stress"] = True

        # --- 3. AMBIENT LIGHT CHECK (Slow I2C Read - Every 2 seconds) ---
        if current_time - self.last_light_check > 2.0:
            self.cached_light_status = self.light_sensor.get_status()
            self.last_light_check = current_time

        if self.cached_light_status and self.cached_light_status.get("light_mode") == "NIGHT":
            env_data["low_light"] = True

        # --- 4. AUDIO ANOMALY CHECK (Flag read from background thread) ---
        if self.audio_sensor.crash_detected:
            env_data["audio_anomaly"] = True
            # Reset the flag after reading it so it doesn't trigger continuously
            self.audio_sensor.crash_detected = False

        return env_data

    def stop(self):
        """Safely shuts down the hardware sensors and terminates threads."""
        self.air_sensor.stop()
        self.temp_sensor.stop()
        self.light_sensor.stop()
        self.audio_sensor.stop()