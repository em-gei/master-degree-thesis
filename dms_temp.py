import time
import board
import adafruit_dht
import cv2
import numpy as np

# Threshold configuration
TEMP_LOW = 18.0
TEMP_HIGH = 30.0

WINDOW_NAME = "MONITOR AMBIENTALE"

class DMSTemp:
    def __init__(self):
        self.active = True
        self.dht_device = None
        
        try:
            # Use DHT11 su GPIO4
            self.dht_device = adafruit_dht.DHT11(board.D4)
            print("🌡️ Monitor Ambientale Avviato (DHT11 su GPIO4)")
            # Create window view
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 400, 300)
            
        except Exception as e:
            print(f"❌ Errore Init Temp: {e}")
            self.active = False


    def _update_ui(self, temp, hum):
        """Aggiorna la finestra con i nuovi dati e colori"""
        bg_color = (0, 0, 0) # black
        text_color = (255, 255, 255) # white
        if temp < TEMP_LOW:
            bg_color = (255, 0, 0)      # Blue
        elif TEMP_LOW <= temp <= TEMP_HIGH:
            bg_color = (0, 255, 0)    # Green
        else:
            bg_color = (0, 0, 255)      # Red
            
        # Create backgroun image
        img = np.zeros((300, 400, 3), dtype=np.uint8)
        img[:] = bg_color
        # Title        
        cv2.putText(img, "CABINA METEO", (60, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
        # Temperature
        cv2.putText(img, f"{temp:.1f} C", (80, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, text_color, 4)
        # 3. Humidity
        hum_text = f"Umidita': {hum}%" if hum is not None else "Umidita': --%"
        cv2.putText(img, hum_text, (100, 220),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)        
        cv2.imshow(WINDOW_NAME, img)
        

    def get_status(self):
        """
        Legge i dati, aggiorna la finestra e ritorna lo stato per i LED (eventualmente).
        """
        if not self.active or self.dht_device is None:
            return None

        try:
            temperature = self.dht_device.temperature
            humidity = self.dht_device.humidity
            if temperature is None:
                return None

            self._update_ui(temperature, humidity)
            if temperature > TEMP_HIGH:
                return {"priority": 1, "led_command": "WARN"}
            else:
                return {"priority": 0, "led_command": "SAFE"}
        except RuntimeError:
            # Normal reading errors for DHT11
            return None
        except Exception as e:
            print(f"Errore Temp UI: {e}")
            return None
        

    def stop(self):
        try:
            cv2.destroyWindow(WINDOW_NAME)
        except:
            pass
        if self.dht_device:
            self.dht_device.exit()