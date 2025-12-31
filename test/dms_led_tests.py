import unittest
from unittest.mock import MagicMock, patch, call
import dms_led

class TestDMSLed(unittest.TestCase):
    
    # patch replaces 'gpiozero.OutputDevice' with a dummy object for the duration of tests in this class.
    @patch('dms_led.OutputDevice')
    def setUp(self, mock_output_device_cls):
        self.mock_data = MagicMock(name="DATA_PIN")
        self.mock_clock = MagicMock(name="CLOCK_PIN")
        self.mock_load = MagicMock(name="LOAD_PIN")
        # Define OutputDevice constructor
        mock_output_device_cls.side_effect = [self.mock_data, self.mock_clock, self.mock_load]    
        
        # Inizializziamo la classe
        self.led_system = dms_led.DMSLed()
        self.data_pin = self.led_system.data_pin
        self.clock_pin = self.led_system.clock_pin
        self.load_pin = self.led_system.load_pin

    def test_initialization(self):
        self.assertTrue(self.led_system.active)
        self.assertNotEqual(self.data_pin, self.clock_pin)

    def test_shift_out_logic(self):
        # Check bit-bang logic: sending a byte (0x80 = 10000000)
        self.data_pin.reset_mock()
        self.clock_pin.reset_mock()
        self.led_system._shift_out(0x80)
        
        self.assertEqual(self.clock_pin.on.call_count, 8)
        self.assertEqual(self.clock_pin.off.call_count, 8)
        self.data_pin.on.assert_called()

    def test_send_command(self):
        # Verify that _send handles the LOAD/CS pin correctly
        self.load_pin.reset_mock()
        self.led_system._send(0x01, 0xFF)
        
        # Check sequence: Load OFF -> Transmission -> Load ON
        self.load_pin.off.assert_called()
        self.load_pin.on.assert_called()

    def test_signal_safe(self):
        # Verify that signal_safe sends the correct bitmap
        # Mock the _send method to see what data it's called with
        with patch.object(self.led_system, '_send') as mock_send:
            self.led_system.signal_safe()
            
            self.assertEqual(mock_send.call_count, 8)
            # The last byte of the safe signal is 0x01 (a dot), line 8
            mock_send.assert_called_with(8, 0x01)

    def test_error_handling(self):
        # Check error handling
        with patch('dms_led.OutputDevice', side_effect=OSError("GPIO Error")):
            broken_led = dms_led.DMSLed()
            self.assertFalse(broken_led.active)

if __name__ == '__main__':
    unittest.main()