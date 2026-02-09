import board
import adafruit_tsl2591

class DMSLight:
    def __init__(self):
        self.active = True
        self.sensor = None
        try:
            i2c = board.I2C()
            self.sensor = adafruit_tsl2591.TSL2591(i2c)
            self.sensor.gain = adafruit_tsl2591.GAIN_MED
            print("☀️ Sensore Luce TSL2591 Inizializzato (I2C)")
        except Exception as e:
            print(f"❌ Errore Init Luce: {e}")
            self.active = False


    def get_status(self):
        """
        Ritorna lo stato di illuminazione.
        Non ha priorità di sicurezza ma serve per UI/Comfort.
        """
        if not self.active:
            return None
        try:
            lux = self.sensor.lux
            if lux is None: 
                return None
            if lux < 20:
                mode = "NIGHT"
                ui_text = "MODALITÀ NOTTE"
            elif lux > 2000:
                mode = "GLARE"
                ui_text = "LUCE FORTE"
            else:
                mode = "DAY"
                ui_text = "GIORNO"

            return {
                "priority": 0,
                "led_command": "SAFE",
                "lux_value": lux,
                "light_mode": mode,
                "ui_text": ui_text
            }
        except Exception:
            return None


    def stop(self):
        pass # I2C don't requires explicit closing