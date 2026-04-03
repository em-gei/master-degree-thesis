import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

# Add src/sensors_impl to sys.path so bare "import dms_air" works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))

class TestDMSAir(unittest.TestCase):
    
    def setUp(self):
        """
        Setup dell'ambiente di test isolato (Sandbox).
        Simuliamo l'hardware prima di importare il modulo.
        """
        self.mock_board = MagicMock()
        self.mock_digitalio = MagicMock()
        self.mock_cv2 = MagicMock()
        self.mock_numpy = MagicMock()
        self.modules_patcher = patch.dict(sys.modules, {
            'board': self.mock_board,
            'digitalio': self.mock_digitalio,
            'cv2': self.mock_cv2,
            'numpy': self.mock_numpy
        })
        self.modules_patcher.start()
        # Reload and instantiate module to test
        import dms_air
        importlib.reload(dms_air)
        self.dms_air_module = dms_air
        self.air_system = dms_air.DMSAir()
        # Get pin's mock
        self.mock_pin = self.mock_digitalio.DigitalInOut.return_value


    def tearDown(self):
        self.modules_patcher.stop()
        

    def test_initialization(self):
        """Verifica che il sensore sia configurato correttamente (Input, No Pull)"""
        self.assertTrue(self.air_system.active)
        self.assertFalse(self.air_system.alert_window_open)
        
        self.mock_digitalio.DigitalInOut.assert_called_with(self.mock_board.D24)
        self.assertEqual(self.mock_pin.direction, self.mock_digitalio.Direction.INPUT)
        self.assertIsNone(self.mock_pin.pull)
        

    def test_gas_detected_opens_window(self):
        """
        Scenario: Il sensore rileva gas per la prima volta.
        Atteso: Return ALERT e Apre la finestra CV2.
        """
        self.air_system.alert_window_open = False
        self.mock_pin.value = False # Gas detected
        
        status = self.air_system.get_status()
        
        self.assertEqual(status['led_command'], "ALERT")
        self.assertEqual(status['priority'], 2)
        self.mock_cv2.imshow.assert_called_once()
        self.assertTrue(self.air_system.alert_window_open)


    def test_gas_continuous_detection_optimization(self):
        """
        Scenario: Il sensore continua a rilevare gas
        Atteso: Return ALERT ma NON deve riaprire la finestra
        """
        self.air_system.alert_window_open = True
        self.mock_pin.value = False
        
        status = self.air_system.get_status()
        
        self.assertEqual(status['led_command'], "ALERT")
        self.mock_cv2.imshow.assert_not_called()
        self.assertTrue(self.air_system.alert_window_open)


    def test_air_becomes_safe_closes_window(self):
        """
        Scenario: L'aria torna pulita dopo un allarme.
        Atteso: Return SAFE e Chiude la finestra CV2.
        """
        # Active Low: True (3.3V)
        self.mock_pin.value = True
        # Initial state: window was open
        self.air_system.alert_window_open = True
        
        status = self.air_system.get_status()
        
        self.assertEqual(status['led_command'], "SAFE")
        # UI Action Check: Must destroy window
        self.mock_cv2.destroyWindow.assert_called_once_with("ALLARME GAS")
        # Check Internal Status: Flag must be False
        self.assertFalse(self.air_system.alert_window_open)


    def test_air_stays_safe_optimization(self):
        """
        Scenario: L'aria è pulita e resta pulita.
        Atteso: Return SAFE e NON prova a chiudere finestre inesistenti.
        """
        self.mock_pin.value = True
        self.air_system.alert_window_open = False
        
        status = self.air_system.get_status()
        
        self.assertEqual(status['led_command'], "SAFE")
        self.mock_cv2.destroyWindow.assert_not_called()


    def test_hardware_error_handling(self):
        """Verifica la gestione errori se il pin non risponde"""
        # Simulate hardware error
        self.mock_digitalio.DigitalInOut.side_effect = RuntimeError("GPIO Error")
        
        importlib.reload(self.dms_air_module)
        broken_system = self.dms_air_module.DMSAir()
        
        self.assertFalse(broken_system.active)
        self.assertIsNone(broken_system.get_status())


if __name__ == '__main__':
    unittest.main()