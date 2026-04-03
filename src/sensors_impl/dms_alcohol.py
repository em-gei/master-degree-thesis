import time
import board
import digitalio
import cv2
import numpy as np


PIN_SENSOR = board.D23
WINDOW_NAME = "ALCOL ALERT"

class DMSAlcohol:
    def __init__(self):
        self.active = True
        self.sensor_pin = None
        self.alert_window_open = False
        try:
            # Setup GPIO
            self.sensor_pin = digitalio.DigitalInOut(PIN_SENSOR)
            self.sensor_pin.direction = digitalio.Direction.INPUT
            self.sensor_pin.pull = None # Using external resistance
            print("MQ-3 Alcohol Sensor Initialized (GPIO 23)")
        except Exception as e:
            print(f"Errore Init Alcol: {e}")
            self.active = False
            

    def _show_alert_window(self):
        """Crea una finestra di allerta rossa lampeggiante"""
        img = np.zeros((300, 400, 3), dtype=np.uint8)
        img[:] = (0, 0, 255) # RED
        cv2.putText(img, "PERICOLO!", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 4)
        cv2.putText(img, "ALCOL RILEVATO", (30, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.imshow(WINDOW_NAME, img)
        self.alert_window_open = True
        

    def _close_alert_window(self):
        """Chiude la finestra se aperta"""
        if self.alert_window_open:
            try:
                cv2.destroyWindow(WINDOW_NAME)
            except:
                pass
            self.alert_window_open = False
            

    def get_status(self):
        """
        Legge il sensore MQ-3.
        Hardware: 
           - Aria Pulita = 3.2V (True)
           - Alcol = 0V (False)
        """
        if not self.active or not self.sensor_pin:
            return None

        # If raw_value=False (0V) =>  is_alcohol_detected=True
        is_alcohol_detected = not self.sensor_pin.value
        if is_alcohol_detected:
            self._show_alert_window()
            return {
                "priority": 3,
                "led_command": "DANGER",
                "ui_text": "ALCOL RILEVATO"
            }
        else:
            self._close_alert_window()
            return {
                "priority": 0,
                "led_command": "SAFE",
                "ui_text": "Sobrio"
            }
            

    def stop(self):
        self._close_alert_window()
        if self.sensor_pin:
            self.sensor_pin.deinit()