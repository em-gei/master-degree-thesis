class PriorityArbitrator:
    def __init__(self):
        self.ACTION_CRITICAL_STOP = "EMERGENCY_STOP_VEHICLE"
        self.ACTION_ALARM_HIGH = "TRIGGER_HIGH_ALARM"
        self.ACTION_ALARM_LOW = "TRIGGER_LOW_ALARM"
        self.ACTION_NORMAL = "NORMAL_OPERATION"

    def evaluate_system_state(self, critical_data, ml_data, env_data):
        """
        Evaluates the overall system state and determines the action to take.
        Returns a dictionary containing the primary action and any secondary warnings.
        """
        final_action = self.ACTION_NORMAL
        active_warnings = []

        # =====================================================================
        # LEVEL 0: PREVENTIVE ENVIRONMENTAL DIAGNOSTICS (The Modifiers)
        # =====================================================================
        if env_data.get("low_light"):
            active_warnings.append("WARNING_LOW_LIGHT_ENABLE_IR")
        if env_data.get("heat_stress"):
            active_warnings.append("WARNING_HEAT_STRESS")
        if env_data.get("audio_anomaly"):
            active_warnings.append("WARNING_EXTERNAL_ANOMALY")

        # =====================================================================
        # LEVEL 1: ABSOLUTE PHYSICAL AND DETERMINISTIC EMERGENCIES (Maximum Priority)
        # =====================================================================
        if critical_data.get("crash_detected"):
            return self._build_response(self.ACTION_CRITICAL_STOP, "CRASH_DETECTED", active_warnings)
            
        if critical_data.get("alcohol_over_limit"):
            return self._build_response(self.ACTION_CRITICAL_STOP, "ALCOHOL_LIMIT_EXCEEDED", active_warnings)

        if env_data.get("gas_danger"):
            return self._build_response(self.ACTION_CRITICAL_STOP, "TOXIC_GAS_DETECTED", active_warnings)

        # =====================================================================
        # LEVEL 2: PREDICTIVE MACHINE LEARNING (Driver Behavior)
        # =====================================================================
        ml_prediction = ml_data.get("prediction", "VIGILE")

        if ml_prediction == "MALORE":
            return self._build_response(self.ACTION_CRITICAL_STOP, "ML_MALORE_DETECTED", active_warnings)

        if ml_prediction == "SONNOLENZA":
            return self._build_response(self.ACTION_ALARM_HIGH, "ML_SONNOLENZA_DETECTED", active_warnings)

        if ml_prediction == "DISTRAZIONE":
            return self._build_response(self.ACTION_ALARM_LOW, "ML_DISTRAZIONE_DETECTED", active_warnings)

        # =====================================================================
        # LEVEL 3: NORMAL OPERATION
        # =====================================================================
        return self._build_response(self.ACTION_NORMAL, "DRIVER_VIGILE", active_warnings)

    def _build_response(self, action, trigger_reason, warnings):
        """Helper for structuring standardized output"""
        return {
            "primary_action": action,
            "trigger_reason": trigger_reason,
            "active_warnings": warnings
        }