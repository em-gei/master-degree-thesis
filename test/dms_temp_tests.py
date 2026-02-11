import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import numpy as np
import importlib

# --- PRE-IMPORT MOCKING ---
mock_board = MagicMock()
mock_dht = MagicMock()
mock_cv2 = MagicMock()
mock_cv2.WINDOW_NORMAL = 0 
mock_cv2.FONT_HERSHEY_SIMPLEX = 1

sys.modules['board'] = mock_board
sys.modules['adafruit_dht'] = mock_dht
sys.modules['cv2'] = mock_cv2

import dms_temp

class TestDMSTemp(unittest.TestCase):
    
    def setUp(self):
        mock_cv2.reset_mock()
        mock_dht.reset_mock()        
        # Force DHT11 to return a NEW MagicMock instance every time
        self.mock_sensor_instance = MagicMock()
        mock_dht.DHT11.return_value = self.mock_sensor_instance
        # Reload dms_temp module to use mocks in sys.modules
        importlib.reload(dms_temp)
        self.temp_system = dms_temp.DMSTemp()


    def test_initialization(self):
        """Verifica init senza aprire finestre reali"""
        mock_cv2.namedWindow.assert_called_with(dms_temp.WINDOW_NAME, mock_cv2.WINDOW_NORMAL)
        self.assertTrue(self.temp_system.active)


    def test_status_blue_cold(self):
        """Test: < 18 gradi -> Sfondo Blu"""
        self.mock_sensor_instance.temperature = 15.0
        self.mock_sensor_instance.humidity = 60
        
        status = self.temp_system.get_status()
        
        self.assertEqual(status['led_command'], 'SAFE')
        args, _ = mock_cv2.imshow.call_args
        _, img_array = args 
        np.testing.assert_array_equal(img_array[0, 0], [255, 0, 0], err_msg="Lo sfondo dovrebbe essere BLU (255,0,0)")
        

    def test_status_green_normal(self):
        """Test: 25 gradi -> Sfondo Verde"""
        self.mock_sensor_instance.temperature = 25.0
        self.mock_sensor_instance.humidity = 50
        
        status = self.temp_system.get_status()
        
        self.assertEqual(status['led_command'], 'SAFE')
        args, _ = mock_cv2.imshow.call_args
        _, img_array = args
        np.testing.assert_array_equal(img_array[0, 0], [0, 255, 0], err_msg="Lo sfondo dovrebbe essere VERDE")
        

    def test_status_red_hot(self):
        """Test: > 28 gradi -> Sfondo Rosso e ALERT"""
        self.mock_sensor_instance.temperature = 35.0
        self.mock_sensor_instance.humidity = 50
        
        status = self.temp_system.get_status()
        
        self.assertEqual(status['led_command'], 'ALERT')
        args, _ = mock_cv2.imshow.call_args
        _, img_array = args
        np.testing.assert_array_equal(img_array[0, 0], [0, 0, 255], err_msg="Lo sfondo dovrebbe essere ROSSO")
        

    def test_sensor_read_error(self):
        """Test: Gestione RuntimeError in modo ISOLATO"""
        # Simulate error on temperature property
        with patch.object(type(self.mock_sensor_instance), 'temperature', new_callable=PropertyMock, create=True) as mock_temp_prop:
            mock_temp_prop.side_effect = RuntimeError("Checksum Error")
            
            status = self.temp_system.get_status()
            
            self.assertIsNone(status)
            

    def test_sensor_none_value(self):
        """Test: Sensore restituisce None"""
        self.mock_sensor_instance.temperature = None
        status = self.temp_system.get_status()
        self.assertIsNone(status)
        

if __name__ == '__main__':
    unittest.main()