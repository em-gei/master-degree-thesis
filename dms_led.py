from gpiozero import OutputDevice
import time

class DMSLed:
    def __init__(self):
        try:
            print("Inizializzazione LED...")
            # PIN CONFIGURATION
            self.data_pin = OutputDevice(10) # Physical Pin 19 -> GPIO 10 (Data)
            self.clock_pin = OutputDevice(11) # Physical Pin 23 -> GPIO 11 (Clock)
            self.load_pin = OutputDevice(8) # Physical Pin 24 -> GPIO 8 (Load/CS)
            self.active = True
            
            # Hardware Initialization
            self._init_matrix()
            self.clear()
            print("✅ Matrice LED pronta (Modalità Manuale/GPIOZero).")
            
        except Exception as e:
            print(f"❌ Errore Hardware LED: {e}")
            self.active = False
            

    def _shift_out(self, val):
        # Send byte, bit per bit
        for i in range(8):
            bit = val & (0x80 >> i)
            if bit:
                self.data_pin.on()
            else:
                self.data_pin.off()
            
            # Clock Pulse
            self.clock_pin.on()
            # No need for sleep here, Python is already slow enough for the chip
            self.clock_pin.off()


    def _send(self, register, data):
        # Send command to the chip
        if not self.active: return
        self.load_pin.off()
        self._shift_out(register)
        self._shift_out(data)
        self.load_pin.on()
        

    def _init_matrix(self):
        # Boot sequence MAX7219
        self._send(0x0F, 0x00) # Test mode off
        self._send(0x0C, 0x01) # Shutdown -> Normal
        self._send(0x0B, 0x07) # Scan limit -> All
        self._send(0x0A, 0x02) # Intensity (0x00 a 0x0F) - Mettiamo 2 (bassa)
        self._send(0x09, 0x00) # Decode mode -> None
        

    def draw_bitmap(self, bitmap):
        # Draw an 8-byte list
        for i, row_data in enumerate(bitmap):
            self._send(i + 1, row_data)


    def clear(self):
        # Clean the matrix
        for i in range(1, 9):
            self._send(i, 0x00)


    def close(self):
        self.clear()
        self._send(0x0C, 0x00) # Shutdown


    # --- SYMBOLS ---
    def signal_safe(self):
        # A dot at the bottom right    
        self.draw_bitmap([0, 0, 0, 0, 0, 0, 0, 1])

    def signal_distraction_sx(self):
        # Left arrow
        bitmap = [0x18, 0x3C, 0x7E, 0xFF, 0x18, 0x18, 0x18, 0x18]
        self.draw_bitmap(bitmap)

    def signal_distraction_dx(self):
        # Right arrow
        bitmap = [0x18, 0x18, 0x18, 0x18, 0xFF, 0x7E, 0x3C, 0x18]
        self.draw_bitmap(bitmap)
        
    def signal_distraction_down(self):
        # Down arrow
        bitmap = [
            0x00, # Column 0: Empty
            0x10, # Column 1: Outer Tip (Bit 4)
            0x30, # Column 2: Inner Tip (Bits 4 and 5)
            0xFF, # Column 3: Center Rod (Full On)
            0xFF, # Column 4: Center Rod (Full On)
            0x30, # Column 5: Inner Tip
            0x10, # Column 6: Outer Tip
            0x00 # Column 7: Empty
        ]
        self.draw_bitmap(bitmap)    

    def signal_danger(self):
        # Draw an X
        bitmap = [0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81]
        self.draw_bitmap(bitmap)
        
    def signal_alert(self):
        # Draw an horizontal line in the middle
        val = 0x18 
        bitmap = [val, val, val, val, val, val, val, val]
        self.draw_bitmap(bitmap)
        

# Test
if __name__ == "__main__":
    led = DMSLed()
    print("Test X (Pericolo)")
    led.signal_danger()
    time.sleep(2)
    print("Test Freccia SX")
    led.signal_distraction_sx()
    time.sleep(2)
    print("Test Freccia DX")
    led.signal_distraction_dx()
    time.sleep(2)
    print("ALERT")
    led.signal_alert()
    time.sleep(2)
    led.close()