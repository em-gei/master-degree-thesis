import board
import adafruit_mpu6050
import math

CRASH_THRESHOLD_G = 4.0

class DMSGyro:
    def __init__(self):
        self.active = True
        self.sensor = None
        
        try:
            i2c = board.I2C()
            adafruit_mpu6050._MPU6050_DEVICE_ID = 0x70
            self.sensor = adafruit_mpu6050.MPU6050(i2c)
            print("MPU6050 Gyroscope (ID 0x70) Initialized")
        except Exception as e:
            print(f"Error initializing Gyro: {e}")
            self.active = False


    def get_status(self):
        """
        Ritorna lo stato inerziale.
        Priority:
        - 4 (CRASH): Se G-Force > 5.0G -> LED ROSSO
        - 0 (SAFE): Guida normale
        """
        if not self.active:
            return None

        try:
            acc_x, acc_y, acc_z = self.sensor.acceleration
            total_accel = math.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
            g_force = total_accel / 9.81 
            if g_force > CRASH_THRESHOLD_G:
                return {
                    "priority": 4,
                    "led_command": "DANGER",
                    "ui_text": "IMPATTO RILEVATO!",
                    "g_force": g_force
                }
            else:
                return {
                    "priority": 0,
                    "led_command": "SAFE",
                    "ui_text": f"G-Force: {g_force:.1f}",
                    "g_force": g_force
                }
        except Exception:
            return None
        

    def stop(self):
        pass