import unittest
from unittest.mock import MagicMock, patch
import sys
import dms_core

class TestDMSCoreIntegration(unittest.TestCase):
    
    def setUp(self):
        print(f"\n🔵 {self._testMethodName}")
        

    def _setup_light_mock(self, mock_light_cls):
        mock_instance = mock_light_cls.return_value
        # Safe default return value
        mock_instance.get_status.return_value = {
            "ui_text": "DEBUG", 
            "lux_value": 0, 
            "light_mode": "DAY"
        }
        return mock_instance


    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSAlcohol')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_audio_crash_detected(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls,mock_alc_cls, mock_light_cls, mock_cv2):
        """
        Scenario: Audio rileva crash.
        Atteso: Il sistema segnala pericolo (LED) e poi esce (exit).
        """
        self._setup_light_mock(mock_light_cls)
        mock_audio_instance = mock_audio_cls.return_value
        mock_audio_instance.crash_detected = True
        mock_led_instance = mock_led_cls.return_value
        
        # 2. ESCAPE ROUTE: Mock exit() to not kill test runner when it executes
        with patch('builtins.exit', side_effect=SystemExit) as mock_exit:
            try:
                dms_core.main()
            except SystemExit:
                pass

            print("   Verifica: Audio Crash -> LED Danger + Exit")
            mock_led_instance.signal_danger.assert_called_once()
            mock_exit.assert_called_once()
            print("   ✅ PASSED")
            
    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSAlcohol')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_alcohol_danger(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls, mock_alc_cls, mock_light_cls, mock_cv2):
        """
        Alcol rilevato -> LED Danger (Vince su Camera Safe)
        """
        self._setup_light_mock(mock_light_cls)
        mock_audio_cls.return_value.crash_detected = False
        mock_cam_cls.return_value.get_status.return_value = {"led_command": "SAFE"}
        mock_alc_cls.return_value.get_status.return_value = {"led_command": "DANGER"}        
        mock_led_instance = mock_led_cls.return_value
        mock_cv2.waitKey.return_value = ord('q')

        dms_core.main()

        print("   Verifica: Alcol DANGER -> LED Danger")
        mock_led_instance.signal_danger.assert_called()
        print("   ✅ PASSED")


    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSAlcohol')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_camera_safe(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls, mock_alc_cls, mock_light_cls, mock_cv2):
        """
        Scenario: Audio OK, Camera dice SAFE.
        Atteso: LED Safe.
        """
        self._setup_light_mock(mock_light_cls)
        mock_audio_instance = mock_audio_cls.return_value
        mock_audio_instance.crash_detected = False
        mock_cam_instance = mock_cam_cls.return_value
        mock_cam_instance.get_status.return_value = {"led_command": "SAFE"}
        mock_alc_cls.return_value.get_status.return_value = {"led_command": "SAFE"}
        mock_led_instance = mock_led_cls.return_value
        # mock return value ('q' == 113) to activate break and exit from while loop after 1 iteration
        mock_cv2.waitKey.return_value = ord('q') 

        dms_core.main()

        print("   Verifica: Camera SAFE -> LED Safe")
        mock_led_instance.signal_safe.assert_called()
        print("   ✅ PASSED")
        

    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSAlcohol')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_camera_distraction_down(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls,mock_alc_cls, mock_light_cls, mock_cv2):
        """
        Scenario: Audio OK, Camera dice DOWN.
        Atteso: LED Distraction Down.
        """
        self._setup_light_mock(mock_light_cls)
        mock_audio_instance = mock_audio_cls.return_value
        mock_audio_instance.crash_detected = False
        mock_cam_instance = mock_cam_cls.return_value
        mock_cam_instance.get_status.return_value = {"led_command": "DOWN"}
        mock_led_instance = mock_led_cls.return_value
        mock_cv2.waitKey.return_value = ord('q') 

        dms_core.main()

        print("   Verifica: Camera DOWN -> LED Distraction Down")
        mock_led_instance.signal_distraction_down.assert_called()
        print("   ✅ PASSED")
        

    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_camera_no_face_alert(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls, mock_light_cls, mock_cv2):
        """
        Scenario: Audio OK, Camera restituisce None (nessun volto).
        Atteso: LED Alert (Anomalia/Standby).
        """
        self._setup_light_mock(mock_light_cls)
        mock_audio_instance = mock_audio_cls.return_value
        mock_audio_instance.crash_detected = False
        mock_cam_instance = mock_cam_cls.return_value
        mock_cam_instance.get_status.return_value = {
                "alarm_triggered": False,
                "led_command": "ALERT",
                "text": "NESSUN VOLTO RILEVATO"
            }
        mock_led_instance = mock_led_cls.return_value
        mock_cv2.waitKey.return_value = ord('q')

        dms_core.main()

        print("   Verifica: Camera None -> LED Alert")
        mock_led_instance.signal_alert.assert_called()
        print("   ✅ PASSED")
        

    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_camera_explicit_alert(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls, mock_light_cls, mock_cv2):
        """
        Scenario: Camera restituisce esplicitamente comando ALERT.
        Atteso: LED Alert.
        """
        mock_audio_instance = mock_audio_cls.return_value
        mock_audio_instance.crash_detected = False
        mock_cam_instance = mock_cam_cls.return_value
        mock_cam_instance.get_status.return_value = {"led_command": "ALERT"}
        mock_led_instance = mock_led_cls.return_value
        mock_cv2.waitKey.return_value = ord('q')

        dms_core.main()

        print("   Verifica: Camera Command ALERT -> LED Alert")
        mock_led_instance.signal_alert.assert_called()
        print("   ✅ PASSED")
        
    
    @patch('dms_core.cv2')
    @patch('dms_core.DMSLight')
    @patch('dms_core.DMSAlcohol')
    @patch('dms_core.DMSTemp')
    @patch('dms_core.DMSAudio')
    @patch('dms_core.DMSCamera')
    @patch('dms_core.DMSLed')
    def test_polling(self, mock_led_cls, mock_cam_cls, mock_audio_cls, mock_temp_cls,mock_alc_cls, mock_light_cls, mock_cv2):
        """
        Scenario: Verifica che i sensori di temperatura e luce vengano invocati
        """
        mock_audio_instance = mock_audio_cls.return_value
        mock_audio_instance.crash_detected = False
        mock_cam_instance = mock_cam_cls.return_value
        mock_cam_instance.get_status.return_value = {"led_command": "SAFE"}
        mock_temp_instance = mock_temp_cls.return_value
        mock_light_instance = self._setup_light_mock(mock_light_cls)
        
        # Simulate the passage of time
        with patch('dms_core.time.time', side_effect=[10, 11, 12, 13]):
            # Set waitKey to exit immediately
            mock_cv2.waitKey.return_value = ord('q')
            dms_core.main()

            # Verifica chiamata temperatura
            mock_temp_instance.get_status.assert_called()
            # Verifica chiamata luce
            mock_light_instance.get_status.assert_called()
            
            print("   ✅ PASSED")
        

if __name__ == '__main__':
    unittest.main()