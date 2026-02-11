import board
import digitalio
import cv2
import numpy as np

PIN_SENSOR = board.D24  # GPIO24
WINDOW_NAME = "ALLARME GAS"

class DMSAir:
    def __init__(self):
        self.active = True
        self.sensor_pin = None
        self.alert_window_open = False
        try:
            # Setup
            self.sensor_pin = digitalio.DigitalInOut(PIN_SENSOR)
            self.sensor_pin.direction = digitalio.Direction.INPUT
            self.sensor_pin.pull = None # Because configured with external resistance
            print("💨 Sensore Aria MQ-135 Inizializzato (GPIO 24)")
        except Exception as e:
            print(f"❌ Errore Init Aria: {e}")
            self.active = False


    def _show_alert_window(self):
        """Crea la finestra Gialla UNA sola volta"""
        img = np.zeros((300, 500, 3), dtype=np.uint8)
        img[:] = (0, 255, 255) # Yellow
        text_color = (0, 0, 0) # Black
        cv2.putText(img, "ATTENZIONE", (110, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, text_color, 4)
        cv2.putText(img, "LIVELLO GAS", (150, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2)
        cv2.putText(img, "RILEVATO NELL'ARIA", (90, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2)
        cv2.imshow(WINDOW_NAME, img)
        self.alert_window_open = True


    def _close_alert_window(self):
        """Chiude la finestra solo se è aperta"""
        if self.alert_window_open:
            try:
                cv2.destroyWindow(WINDOW_NAME)
            except:
                pass
            self.alert_window_open = False


    def get_status(self):
        """
        True (1) = Aria Pulita
        False (0) = Aria Sporca (Active Low)
        """
        if not self.active or not self.sensor_pin:
            return None

        is_bad_air = not self.sensor_pin.value
        if is_bad_air:
            if not self.alert_window_open:
                self._show_alert_window()
            return {
                "priority": 2,
                "led_command": "ALERT",
                "ui_text": "GAS RILEVATO"
            }
        else:
            if self.alert_window_open:
                self._close_alert_window()
            return {
                "priority": 0,
                "led_command": "SAFE",
                "ui_text": "Aria OK"
            }


    def stop(self):
        self._close_alert_window()
        if self.sensor_pin:
            self.sensor_pin.deinit()