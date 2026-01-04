import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import dms_audio
import time

class TestDMSAudio(unittest.TestCase):
    
    @patch('dms_audio.pyaudio.PyAudio')
    def setUp(self, mock_pyaudio_cls):
        """Setup before each test. Mocks the PyAudio hardware."""
        print(f"\n🔵 [AUDIO TEST START] {self._testMethodName}")
        # Instantiate the class (which instantiates the mock PyAudio)
        self.audio_system = dms_audio.DMSAudio(device_index=0, threshold_db=90)
        # Get reference to the mock object created inside the class
        self.mock_pa_instance = self.audio_system.p
        # Mock the stream object that PyAudio.open() returns
        self.mock_stream = MagicMock()
        self.mock_pa_instance.open.return_value = self.mock_stream

    def test_initialization(self):
        """Verify initial state and configuration"""
        self.assertEqual(self.audio_system.THRESHOLD_DB, 90)
        self.assertEqual(self.audio_system.device_index, 0)
        self.assertFalse(self.audio_system.running)
        self.assertFalse(self.audio_system.crash_detected)
        print("   ✅ PASSED: Inizializzazione corretta.")

    def test_start_listening(self):
        """Verify start_listening opens the stream correctly"""
        with patch('threading.Thread') as mock_thread:
            self.audio_system.start_listening()
            
            # Check if PyAudio.open was called with correct parameters
            self.mock_pa_instance.open.assert_called_once()
            _, kwargs = self.mock_pa_instance.open.call_args
            
            self.assertEqual(kwargs['rate'], 44100)
            self.assertEqual(kwargs['input_device_index'], 0)
            self.assertTrue(kwargs['input'])
            
            # Check if thread was started
            mock_thread.return_value.start.assert_called_once()
            self.assertTrue(self.audio_system.running)
            print("   ✅ PASSED: Stream audio aperto e thread avviato.")

    def test_stop(self):
        """Verify stop cleans up resources"""
        # Manually set the stream mock to simulate it being open
        self.audio_system.stream = self.mock_stream
        self.audio_system.running = True
        
        self.audio_system.stop()
        
        self.assertFalse(self.audio_system.running)
        self.mock_stream.stop_stream.assert_called_once()
        self.mock_stream.close.assert_called_once()
        self.mock_pa_instance.terminate.assert_called_once()
        print("   ✅ PASSED: Risorse rilasciate correttamente.")

    def test_monitor_loop_quiet(self):
        """Test logic with QUIET audio (should NOT trigger crash)"""
        # Create a chunk of silence (zeros)
        # 1024 samples * 2 bytes (int16) = 2048 bytes
        quiet_data = bytes([0] * 2048)
        
        # Setup the mock to return silence once, then stop the loop
        def side_effect(*args, **kwargs):
            self.audio_system.running = False # Stop loop after 1 read
            return quiet_data
        
        self.mock_stream.read.side_effect = side_effect
        
        # Inject the mock stream
        self.audio_system.stream = self.mock_stream
        self.audio_system.running = True
        
        # Run the loop synchronously (no thread) to test logic
        self.audio_system._monitor_loop()
        
        self.assertFalse(self.audio_system.crash_detected)
        print("   ✅ PASSED: Nessun allarme con audio silenzioso.")

    def test_monitor_loop_loud_crash(self):
        """Test logic with LOUD audio (SHOULD trigger crash)"""
        # Create a chunk of max volume noise (random int16 high values)
        # 32700 is close to max int16 (32767), very loud
        loud_array = np.full(1024, 32700, dtype=np.int16) 
        loud_data = loud_array.tobytes()
        
        # Setup the mock to return noise once, then stop the loop
        def side_effect(*args, **kwargs):
            self.audio_system.running = False 
            return loud_data
        
        self.mock_stream.read.side_effect = side_effect
        
        self.audio_system.stream = self.mock_stream
        self.audio_system.running = True
        
        # Run logic
        self.audio_system._monitor_loop()
        
        self.assertTrue(self.audio_system.crash_detected)
        print("   ✅ PASSED: Allarme RILEVATO con audio forte.")

if __name__ == '__main__':
    unittest.main() 