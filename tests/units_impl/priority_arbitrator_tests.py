import unittest
import sys
import os

# Add source directory to sys.path so bare imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'units_impl'))

from priority_arbitrator import PriorityArbitrator

class TestPriorityArbitrator(unittest.TestCase):
    
    def setUp(self):
        """Initialize the arbitrator before each test."""
        self.arbitrator = PriorityArbitrator()
        self.base_critical = {"crash_detected": False, "alcohol_over_limit": False}
        self.base_ml = {"prediction": "VIGILE"}
        self.base_env = {"gas_danger": False, "heat_stress": False, "low_light": False, "audio_anomaly": False}

    def test_normal_driving(self):
        """Test the state of perfect driving (No alerts)."""
        decision = self.arbitrator.evaluate_system_state(self.base_critical, self.base_ml, self.base_env)
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_NORMAL)
        self.assertEqual(len(decision["active_warnings"]), 0)

    def test_level_0_environmental_warnings(self):
        """Test adding environmental warnings without altering the ALERT state."""
        env_data = self.base_env.copy()
        env_data["low_light"] = True
        env_data["heat_stress"] = True
        
        decision = self.arbitrator.evaluate_system_state(self.base_critical, self.base_ml, env_data)
        
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_NORMAL)
        self.assertIn("WARNING_LOW_LIGHT_ENABLE_IR", decision["active_warnings"])
        self.assertIn("WARNING_HEAT_STRESS", decision["active_warnings"])

    def test_level_1_crash_overrides_everything(self):
        """Test that a CRASH has absolute priority, even if the ML says VIGILE."""
        critical_data = self.base_critical.copy()
        critical_data["crash_detected"] = True
        
        decision = self.arbitrator.evaluate_system_state(critical_data, self.base_ml, self.base_env)
        
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_CRITICAL_STOP)
        self.assertEqual(decision["trigger_reason"], "CRASH_DETECTED")

    def test_level_1_toxic_gas_overrides_ml(self):
        """Test that the toxic gas overrides the ML predictions."""
        env_data = self.base_env.copy()
        env_data["gas_danger"] = True
        ml_data = {"prediction": "VIGILE"} # Il ML non vede il gas
        
        decision = self.arbitrator.evaluate_system_state(self.base_critical, ml_data, env_data)
        
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_CRITICAL_STOP)
        self.assertEqual(decision["trigger_reason"], "TOXIC_GAS_DETECTED")

    def test_level_2_ml_malore(self):
        """Testing the correct identification of an illness using machine learning."""
        ml_data = {"prediction": "MALORE"}
        
        decision = self.arbitrator.evaluate_system_state(self.base_critical, ml_data, self.base_env)
        
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_CRITICAL_STOP)
        self.assertEqual(decision["trigger_reason"], "ML_MALORE_DETECTED")

    def test_level_2_ml_distrazione(self):
        """Test a low-level alert for Distraction."""
        ml_data = {"prediction": "DISTRAZIONE"}
        
        decision = self.arbitrator.evaluate_system_state(self.base_critical, ml_data, self.base_env)
        
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_ALARM_LOW)
        self.assertEqual(decision["trigger_reason"], "ML_DISTRAZIONE_DETECTED")

    def test_conflict_resolution(self):
        """
            Il guidatore è ubriaco, si sta addormentando e c'è buio. 
            L'alcool (Level 1) DEVE vincere sulla sonnolenza (Level 2).
        """
        critical_data = {"crash_detected": False, "alcohol_over_limit": True}
        ml_data = {"prediction": "SONNOLENZA"}
        env_data = {"gas_danger": False, "heat_stress": False, "low_light": True, "audio_anomaly": False}
        
        decision = self.arbitrator.evaluate_system_state(critical_data, ml_data, env_data)
        
        self.assertEqual(decision["primary_action"], self.arbitrator.ACTION_CRITICAL_STOP)
        self.assertEqual(decision["trigger_reason"], "ALCOHOL_LIMIT_EXCEEDED")
        self.assertIn("WARNING_LOW_LIGHT_ENABLE_IR", decision["active_warnings"])

if __name__ == '__main__':
    unittest.main(verbosity=2)