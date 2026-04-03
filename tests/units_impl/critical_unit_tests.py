import unittest
from unittest.mock import MagicMock
import sys
import os

# --- IMPORT MOCKING ---
# Mock the HAL (Hardware Abstraction Layer) modules BEFORE importing CriticalUnit.
# This prevents Python from executing the dms_*.py files and throwing
# 'ModuleNotFoundError' for Raspberry Pi specific libraries (like 'board').
sys.modules['dms_alcohol'] = MagicMock()
sys.modules['dms_gyro'] = MagicMock()

# Add source directories to sys.path so bare imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'units_impl'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))

from critical_unit import CriticalUnit

class TestCriticalUnit(unittest.TestCase):
    
    def setUp(self):
        """Initialize the unit. The hardware sensors are automatically mocked."""
        self.unit = CriticalUnit()
        
        # Keep references to the mocked instances to manipulate their outputs
        self.mock_alc = self.unit.alcohol_sensor
        self.mock_gyro = self.unit.gyro_sensor

    def test_safe_driving_state(self):
        """Test that the unit returns False for all flags when sensors report SAFE."""
        self.mock_alc.get_status.return_value = {"led_command": "SAFE"}
        self.mock_gyro.get_status.return_value = {"led_command": "SAFE"}
        
        data = self.unit.get_data()
        
        self.assertFalse(data["crash_detected"])
        self.assertFalse(data["alcohol_over_limit"])

    def test_alcohol_detected(self):
        """Test that alcohol over limit is correctly parsed."""
        self.mock_alc.get_status.return_value = {"led_command": "DANGER"}
        self.mock_gyro.get_status.return_value = {"led_command": "SAFE"}
        
        data = self.unit.get_data()
        
        self.assertFalse(data["crash_detected"])
        self.assertTrue(data["alcohol_over_limit"])

    def test_crash_detected(self):
        """Test that a physical crash is correctly parsed."""
        self.mock_alc.get_status.return_value = {"led_command": "SAFE"}
        self.mock_gyro.get_status.return_value = {"led_command": "DANGER"}
        
        data = self.unit.get_data()
        
        self.assertTrue(data["crash_detected"])
        self.assertFalse(data["alcohol_over_limit"])

if __name__ == '__main__':
    unittest.main(verbosity=2)