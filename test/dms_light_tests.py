import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import importlib


class TestDMSLight(unittest.TestCase):
    
    def setUp(self):
        self.mock_board = MagicMock()
        self.mock_adafruit = MagicMock()
        self.mock_sensor_cls = MagicMock()
        self.mock_adafruit.TSL2591 = self.mock_sensor_cls
        self.mock_adafruit.GAIN_MED = 0x10 
        self.modules_patcher = patch.dict(sys.modules, {
            'board': self.mock_board,
            'adafruit_tsl2591': self.mock_adafruit
        })
        self.modules_patcher.start()
        # Reload dms_light with mocks
        import dms_light
        importlib.reload(dms_light)
        self.dms_light_module = dms_light
        self.light_system = dms_light.DMSLight()
        # Retrieve sensor's instance created in __init__
        self.mock_sensor_instance = self.mock_sensor_cls.return_value
        

    def tearDown(self):
        self.modules_patcher.stop()
        

    def test_initialization_success(self):
        """Verifica che il sensore venga inizializzato con il Gain corretto"""
        self.assertTrue(self.light_system.active)
        self.assertEqual(self.mock_sensor_instance.gain, self.mock_adafruit.GAIN_MED)


    def test_initialization_failure(self):
        """Verifica la gestione dell'errore se il sensore non è collegato"""
        # Simulate an error
        self.mock_sensor_cls.side_effect = RuntimeError("I2C Device not found")
        # Reload to trigger __init__ 
        importlib.reload(self.dms_light_module)
        broken_system = self.dms_light_module.DMSLight()
        
        self.assertFalse(broken_system.active)
        self.assertIsNone(broken_system.get_status())
        

    def test_mode_night(self):
        """Test: Lux < 20 -> Modalità NOTTE"""
        type(self.mock_sensor_instance).lux = PropertyMock(return_value=5.0)
        
        status = self.light_system.get_status()
        
        self.assertIsNotNone(status)
        self.assertEqual(status['light_mode'], 'NIGHT')
        self.assertEqual(status['ui_text'], 'MODALITÀ NOTTE')
        self.assertEqual(status['lux_value'], 5.0)


    def test_mode_day(self):
        """Test: Lux standard (es. 500) -> Modalità GIORNO"""
        type(self.mock_sensor_instance).lux = PropertyMock(return_value=500.0)
        
        status = self.light_system.get_status()
        
        self.assertEqual(status['light_mode'], 'DAY')
        self.assertEqual(status['ui_text'], 'GIORNO')


    def test_mode_glare(self):
        """Test: Lux > 2000 -> Modalità LUCE FORTE"""
        type(self.mock_sensor_instance).lux = PropertyMock(return_value=2500.0)
        
        status = self.light_system.get_status()
        
        self.assertEqual(status['light_mode'], 'GLARE')
        self.assertEqual(status['ui_text'], 'LUCE FORTE')
        

    def test_sensor_read_error(self):
        """Test: Se il sensore restituisce None o errore durante la lettura"""
        # Sensor returns None (saturated)
        type(self.mock_sensor_instance).lux = PropertyMock(return_value=None)
        self.assertIsNone(self.light_system.get_status())
        
        # Sensor throws an exception (es. unwired during execution)
        type(self.mock_sensor_instance).lux = PropertyMock(side_effect=OSError("I/O Error"))
        self.assertIsNone(self.light_system.get_status())

if __name__ == '__main__':
    unittest.main()