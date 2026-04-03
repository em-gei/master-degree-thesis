import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

# Stub hardware-only modules before importing dms_alcohol so the module-level
# `import board / digitalio / cv2` statements don't raise ModuleNotFoundError.
# Don't stub numpy — it's installed and other tests need the real one.
# setUp will replace these stubs with proper MagicMock instances via patch.dict + reload.
for _mod in ('board', 'digitalio', 'cv2'):
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'sensors_impl'))
import dms_alcohol

class TestDMSAlcohol(unittest.TestCase):
    
    def setUp(self):
        self.mock_board = MagicMock()
        self.mock_digitalio = MagicMock()
        self.mock_cv2 = MagicMock()
        self.mock_cv2.FONT_HERSHEY_SIMPLEX = 1
        self.mock_numpy = MagicMock()
        self.mock_pin = MagicMock()
        self.mock_digitalio.DigitalInOut.return_value = self.mock_pin
        self.modules_patcher = patch.dict(sys.modules, {
            'board': self.mock_board,
            'digitalio': self.mock_digitalio,
            'cv2': self.mock_cv2,
            'numpy': self.mock_numpy
        })

        self.modules_patcher.start()
        # Module reload to get mocks
        importlib.reload(dms_alcohol)
        self.alcohol_system = dms_alcohol.DMSAlcohol()
        

    def tearDown(self):
        self.modules_patcher.stop()
        

    def test_alcohol_detected(self):
        """Test: Pin LOW (False) -> DANGER + Finestra Aperta"""
        self.mock_pin.value = False 

        status = self.alcohol_system.get_status()
        
        self.assertEqual(status['led_command'], 'DANGER')
        self.assertEqual(status['priority'], 3)
        self.mock_cv2.imshow.assert_called_with(dms_alcohol.WINDOW_NAME, unittest.mock.ANY)


    def test_no_alcohol(self):
        """Test: Pin HIGH (True) -> SAFE + Finestra Chiusa"""
        self.mock_pin.value = True
        self.alcohol_system.alert_window_open = True
        
        status = self.alcohol_system.get_status()
        
        self.assertEqual(status['led_command'], 'SAFE')
        self.mock_cv2.destroyWindow.assert_called()
        

if __name__ == '__main__':
    unittest.main()