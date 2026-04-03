import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# --- IMPORT MOCKING ---
# Mock the HAL modules to bypass Raspberry Pi hardware libraries during testing.
sys.modules['dms_air'] = MagicMock()
sys.modules['dms_temp'] = MagicMock()
sys.modules['dms_light'] = MagicMock()
sys.modules['dms_audio'] = MagicMock()

# Add source directories to sys.path so bare imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'units_impl'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))

from environment_unit import EnvironmentUnit

class TestEnvironmentUnit(unittest.TestCase):
    
    def setUp(self):
        """Initialize the unit. The hardware sensors are automatically mocked."""
        self.unit = EnvironmentUnit()
        
        # Keep references to the mocked instances
        self.mock_air = self.unit.air_sensor
        self.mock_temp = self.unit.temp_sensor
        self.mock_light = self.unit.light_sensor
        self.mock_audio = self.unit.audio_sensor

        # --- CRITICAL FIX: RESET MOCK COUNTERS ---
        # Because the mocked classes return the same shared instance across all tests,
        # we MUST reset their call histories before each test runs to avoid accumulation.
        self.mock_air.reset_mock()
        self.mock_temp.reset_mock()
        self.mock_light.reset_mock()
        self.mock_audio.reset_mock()

    @patch('environment_unit.time.time')
    def test_safe_environment(self, mock_time):
        """Test that all flags are False when the environment is safe."""
        mock_time.return_value = 100.0 
        
        self.mock_air.get_status.return_value = {"led_command": "SAFE"}
        self.mock_temp.get_status.return_value = {"led_command": "SAFE"}
        self.mock_light.get_status.return_value = {"light_mode": "DAY"}
        self.mock_audio.crash_detected = False
        
        data = self.unit.get_data()
        
        self.assertFalse(data["gas_danger"])
        self.assertFalse(data["heat_stress"])
        self.assertFalse(data["low_light"])
        self.assertFalse(data["audio_anomaly"])

    @patch('environment_unit.time.time')
    def test_toxic_gas_detected(self, mock_time):
        """Test immediate detection of toxic gas (no throttling on this sensor)."""
        mock_time.return_value = 100.0 
        
        self.mock_air.get_status.return_value = {"led_command": "ALERT"}
        self.mock_temp.get_status.return_value = {"led_command": "SAFE"}
        self.mock_light.get_status.return_value = {"light_mode": "DAY"}
        self.mock_audio.crash_detected = False
        
        data = self.unit.get_data()
        self.assertTrue(data["gas_danger"])

    @patch('environment_unit.time.time')
    def test_throttling_logic_and_heat_stress(self, mock_time):
        """Test that temperature is read and then cached for 5 seconds."""
        # T=100.0s: First read. We start at 100s to bypass the __init__ 0.0s lock.
        mock_time.return_value = 100.0
        self.mock_temp.get_status.return_value = {"led_command": "ALERT"}
        
        data_t0 = self.unit.get_data()
        self.assertTrue(data_t0["heat_stress"])
        # Now the call count will be EXACTLY 1 because of the reset_mock() in setUp!
        self.assertEqual(self.mock_temp.get_status.call_count, 1)

        # T=102.0s: Fast-forward 2 seconds. Sensor now says SAFE.
        # BUT we are within the 5s window, so it should use the cache.
        mock_time.return_value = 102.0
        self.mock_temp.get_status.return_value = {"led_command": "SAFE"}
        
        data_t2 = self.unit.get_data()
        # Should STILL be True because it's using the cached ALERT value
        self.assertTrue(data_t2["heat_stress"])
        # Verify the hardware was NOT polled again (call count remains 1)
        self.assertEqual(self.mock_temp.get_status.call_count, 1)

    @patch('environment_unit.time.time')
    def test_audio_anomaly_reset(self, mock_time):
        """Test that audio anomaly is caught and then automatically reset to False."""
        mock_time.return_value = 100.0 
        self.mock_audio.crash_detected = True
        
        # First check: should detect the anomaly and auto-reset the flag
        data1 = self.unit.get_data()
        self.assertTrue(data1["audio_anomaly"])
        self.assertFalse(self.mock_audio.crash_detected) # Check it was reset
        
        # Second check: anomaly should be gone
        data2 = self.unit.get_data()
        self.assertFalse(data2["audio_anomaly"])

if __name__ == '__main__':
    unittest.main(verbosity=2)