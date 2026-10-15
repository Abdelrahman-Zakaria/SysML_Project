package ElevatorTraceability {
    private import ElevatorRequirements::*;

    // ==========================================
    // Derived Lower-Level Requirement Definitions
    // ==========================================

    requirement def <'FR-01a'> HallCallButtonDebounce {
        doc /* Hall call button presses shall be debounced within 50 ms to prevent false double triggers. */
    }

    requirement def <'FR-02a'> CabinKeypadInputValidation {
        doc /* Cabin keypad destination inputs shall be validated against valid building floors 1 to 10. */
    }

    requirement def <'FR-03a'> SmoothAccelerationProfile {
        doc /* Cabin motion speed profiles shall limit acceleration jerk to under 1.2 m/s³. */
    }

    requirement def <'FR-04a'> LevelingAccuracy {
        doc /* Cabin shall bring floor threshold within ±5mm alignment before sending door open signal. */
    }

    requirement def <'FR-05a'> DoorInterlockCheck {
        doc /* Motor interlock circuit must confirm physical door latch engagement prior to brake release. */
    }

    requirement def <'FR-06a'> DisplayUpdateRate {
        doc /* Floor indicator displays shall refresh within 100 ms of optical position sensor trigger. */
    }

    requirement def <'FR-07a'> EmergencyButtonHoldTime {
        doc /* Emergency button must be depressed for at least 1.0 second to prevent accidental activation. */
    }

    requirement def <'SR-01a'> DoorSensorSensitivity {
        doc /* Object detection sensors shall trigger on obstacles larger than 10mm in thickness. */
    }

    requirement def <'SR-02a'> DoorReversalTime {
        doc /* Door motor drive shall initiate opening reversal within 100 ms of obstacle detection. */
    }

    requirement def <'SR-03a'> SafetyBrakeEngagement {
        doc /* Mechanical emergency brakes shall engage automatically within 200 ms of drive power failure. */
    }

    requirement def <'SR-04a'> EmergencyLightingActivation {
        doc /* Backup lighting and alarm chime shall activate immediately upon emergency mode entry. */
    }

    requirement def <'PR-01a'> AccelerationRampUp {
        doc /* Motor drive acceleration rate shall achieve nominal cruise speed within 2.0 seconds. */
    }

    requirement def <'PR-02a'> CANBusPriority {
        doc /* Request message frames shall use high-priority CAN ID headers to guarantee fast transmission. */
    }

    // ==========================================
    // Requirement Traceability Breakdown
    // ==========================================

    requirement def SystemRequirementTraceability {
        requirement req_FR01a : HallCallButtonDebounce;
        requirement req_FR02a : CabinKeypadInputValidation;
        requirement req_FR03a : SmoothAccelerationProfile;
        requirement req_FR04a : LevelingAccuracy;
        requirement req_FR05a : DoorInterlockCheck;
        requirement req_FR06a : DisplayUpdateRate;
        requirement req_FR07a : EmergencyButtonHoldTime;

        requirement req_SR01a : DoorSensorSensitivity;
        requirement req_SR02a : DoorReversalTime;
        requirement req_SR03a : SafetyBrakeEngagement;
        requirement req_SR04a : EmergencyLightingActivation;

        requirement req_PR01a : AccelerationRampUp;
        requirement req_PR02a : CANBusPriority;
    }
}