import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import importlib

class TestDMSGyro(unittest.TestCase):
    
    def setUp(self):
        self.mock_board = MagicMock()
        self.mock_adafruit = MagicMock()
        self.mock_sensor_cls = MagicMock()
        self.mock_adafruit.MPU6050 = self.mock_sensor_cls
        self.modules_patcher = patch.dict(sys.modules, {
            'board': self.mock_board,
            'adafruit_mpu6050': self.mock_adafruit
        })
        self.modules_patcher.start()

        import dms_gyro
        importlib.reload(dms_gyro)
        self.dms_gyro_module = dms_gyro
        self.gyro_system = dms_gyro.DMSGyro()
        self.mock_sensor_instance = self.mock_sensor_cls.return_value


    def tearDown(self):
        self.modules_patcher.stop()


    def test_initialization_fix(self):
        """Verifica che il sensore venga inizializzato e l'ID fix applicato"""
        self.assertTrue(self.gyro_system.active)
        self.assertEqual(self.mock_adafruit._MPU6050_DEVICE_ID, 0x70)


    def test_safe_driving(self):
        """Scenario: Guida normale (1G circa)"""
        # Accelerazione finta: X=0, Y=0, Z=9.81 (Gravità standard)
        type(self.mock_sensor_instance).acceleration = PropertyMock(return_value=(0.0, 0.0, 9.81))
        
        status = self.gyro_system.get_status()
        
        self.assertEqual(status['led_command'], "SAFE")
        self.assertAlmostEqual(status['g_force'], 1.0, places=1)


    def test_crash_detection(self):
        """Scenario: Incidente (Decelerazione violenta > 3G)"""
        # Accelerazione violenta: 40 m/s^2 (~4G)
        type(self.mock_sensor_instance).acceleration = PropertyMock(return_value=(60.0, 0.0, 0.0))
        
        status = self.gyro_system.get_status()
        
        self.assertEqual(status['led_command'], "DANGER")
        self.assertEqual(status['ui_text'], "IMPATTO RILEVATO!")
        self.assertTrue(status['g_force'] > 4.0)
        

    def test_read_error(self):
        """Scenario: Errore di lettura I2C"""
        type(self.mock_sensor_instance).acceleration = PropertyMock(side_effect=OSError("I2C Error"))
        
        status = self.gyro_system.get_status()
        self.assertIsNone(status)


if __name__ == '__main__':
    unittest.main()