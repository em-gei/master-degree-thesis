import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Stub hardware-only modules before importing dms_audio so the module-level
# `import pyaudio` doesn't raise ModuleNotFoundError.
_mock_pyaudio = MagicMock()
_mock_pyaudio.paInt16 = 8  # real pyaudio constant used at module level
sys.modules.setdefault('pyaudio', _mock_pyaudio)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))
import dms_audio

class TestDMSAudio(unittest.TestCase):
    
    @patch('dms_audio.pyaudio.PyAudio')
    def setUp(self, _):
        print(f"\n[AUDIO TEST START] {self._testMethodName}")
        self.audio_system = dms_audio.DMSAudio(device_index=0, threshold_db=85)
        self.mock_pa_instance = self.audio_system.p
        self.mock_stream = MagicMock()
        self.mock_pa_instance.open.return_value = self.mock_stream


    def test_initialization(self):
        """Verify initial state and configuration"""
        self.assertEqual(self.audio_system.THRESHOLD_DB, 85)
        self.assertEqual(self.audio_system.device_index, 0)
        self.assertFalse(self.audio_system.running)
        self.assertFalse(self.audio_system.crash_detected)
        print("PASSED: Inizializzazione corretta.")


    def test_start_listening(self):
        """Verify start_listening opens the stream correctly"""
        with patch('threading.Thread') as mock_thread:
            self.audio_system.start_listening()
            self.mock_pa_instance.open.assert_called_once()
            _, kwargs = self.mock_pa_instance.open.call_args
            
            self.assertEqual(kwargs['rate'], dms_audio.RATE)
            self.assertEqual(kwargs['input_device_index'], 0)
            self.assertTrue(kwargs['input'])
            
            mock_thread.return_value.start.assert_called_once()
            self.assertTrue(self.audio_system.running)
            print("PASSED: Stream audio aperto e thread avviato.")


    def test_stop(self):
        """Verify stop cleans up resources"""
        self.audio_system.stream = self.mock_stream
        self.audio_system.running = True
        
        self.audio_system.stop()
        
        self.assertFalse(self.audio_system.running)
        self.mock_stream.stop_stream.assert_called_once()
        self.mock_stream.close.assert_called_once()
        self.mock_pa_instance.terminate.assert_called_once()
        print("PASSED: Risorse rilasciate correttamente.")


    def test_monitor_loop_quiet(self):
        """Test logic with QUIET audio (should NOT trigger crash)"""
        quiet_data = bytes([0] * 2048)
        
        def side_effect(*args, **kwargs):
            self.audio_system.running = False 
            return quiet_data
        
        self.mock_stream.read.side_effect = side_effect
        self.audio_system.stream = self.mock_stream
        self.audio_system.running = True
        
        self.audio_system._monitor_loop()
        self.assertFalse(self.audio_system.crash_detected)
        print("PASSED: Nessun allarme con audio silenzioso.")
        

    def test_monitor_loop_loud_crash(self):
        """Test logic with LOUD audio (SHOULD trigger crash)"""
        # 32700 generates about 90dB (> 85, default threshold value)
        loud_array = np.full(1024, 32700, dtype=np.int16) 
        loud_data = loud_array.tobytes()
        
        def side_effect(*args, **kwargs):
            self.audio_system.running = False 
            return loud_data
        
        self.mock_stream.read.side_effect = side_effect
        self.audio_system.stream = self.mock_stream
        self.audio_system.running = True
        self.audio_system._monitor_loop()
        self.assertTrue(self.audio_system.crash_detected)
        print("PASSED: Allarme RILEVATO con audio forte.")
        

if __name__ == '__main__':
    unittest.main()