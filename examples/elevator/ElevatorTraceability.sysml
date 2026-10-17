package ElevatorTraceability {
    private import ElevatorRequirements::*;
    private import ElevatorArchitecture::*;
    private import RequirementDerivation::*;

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

    requirement def <'FR-08a'> OverloadThresholdCheck {
        doc /* Overload shall be detected when the cabin load weight exceeds the cabin rated capacity. */
    }

    requirement def <'FR-09a'> OverloadMotionInterlock {
        doc /* The controller shall not command cabin movement while an overload condition is detected. */
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

    requirement def <'PR-03a'> RatedCabinCapacity {
        doc /* The elevator car capacity shall be set to the rated maximum load of 1000 kg. */
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
        requirement req_FR08a : OverloadThresholdCheck;
        requirement req_FR09a : OverloadMotionInterlock;

        requirement req_SR01a : DoorSensorSensitivity;
        requirement req_SR02a : DoorReversalTime;
        requirement req_SR03a : SafetyBrakeEngagement;
        requirement req_SR04a : EmergencyLightingActivation;

        requirement req_PR01a : AccelerationRampUp;
        requirement req_PR02a : CANBusPriority;
        requirement req_PR03a : RatedCabinCapacity;
    }

    // Container usage: derivation ends bind to usages, not to features of a definition
    requirement systemRequirementTraceability : SystemRequirementTraceability;

    // ==========================================
    // Derivation Connection Definitions
    // ==========================================

    #derivation connection def FR01_to_FR01a {
        end #original origReq : AcceptFloorRequests;
        end #derive derivedReq : HallCallButtonDebounce;
    }
    #derivation connection def FR02_to_FR02a {
        end #original origReq : AcceptDestinationRequests;
        end #derive derivedReq : CabinKeypadInputValidation;
    }
    #derivation connection def FR03_to_FR03a {
        end #original origReq : TransportPassengers;
        end #derive derivedReq : SmoothAccelerationProfile;
    }
    #derivation connection def FR04_to_FR04a {
        end #original origReq : OpenDoorsAtDestination;
        end #derive derivedReq : LevelingAccuracy;
    }
    #derivation connection def FR05_to_FR05a {
        end #original origReq : CloseDoorsBeforeMovement;
        end #derive derivedReq : DoorInterlockCheck;
    }
    #derivation connection def FR06_to_FR06a {
        end #original origReq : DisplayCurrentFloor;
        end #derive derivedReq : DisplayUpdateRate;
    }
    #derivation connection def FR07_to_FR07a {
        end #original origReq : ProcessEmergencyRequests;
        end #derive derivedReq : EmergencyButtonHoldTime;
    }
    #derivation connection def FR08_to_FR08a {
        end #original origReq : DetectOverloadConditions;
        end #derive derivedReq : OverloadThresholdCheck;
    }
    #derivation connection def FR09_to_FR09a {
        end #original origReq : PreventMotionOverload;
        end #derive derivedReq : OverloadMotionInterlock;
    }
    #derivation connection def SR01_to_SR01a {
        end #original origReq : DetectDoorObstruction;
        end #derive derivedReq : DoorSensorSensitivity;
    }
    #derivation connection def SR02_to_SR02a {
        end #original origReq : StopDoorClosingOnObstruction;
        end #derive derivedReq : DoorReversalTime;
    }
    #derivation connection def SR03_to_SR03a {
        end #original origReq : StopElevatorCriticalFault;
        end #derive derivedReq : SafetyBrakeEngagement;
    }
    #derivation connection def SR04_to_SR04a {
        end #original origReq : EnterEmergencyMode;
        end #derive derivedReq : EmergencyLightingActivation;
    }
    #derivation connection def PR01_to_PR01a {
        end #original origReq : MaxTravelTime;
        end #derive derivedReq : AccelerationRampUp;
    }
    #derivation connection def PR02_to_PR02a {
        end #original origReq : RequestProcessingLatency;
        end #derive derivedReq : CANBusPriority;
    }
    #derivation connection def PR03_to_PR03a {
        end #original origReq : SupportMaximumLoad;
        end #derive derivedReq : RatedCabinCapacity;
    }

    // ==========================================
    // Derivation Connection Usages
    // ==========================================

    part traceabilityContext {

        #derivation connection trace_FR01_to_FR01a : FR01_to_FR01a {
            end origReq ::> req_acceptFloorRequests;
            end derivedReq ::> systemRequirementTraceability.req_FR01a;
        }
        #derivation connection trace_FR02_to_FR02a : FR02_to_FR02a {
            end origReq ::> req_acceptDestinationRequests;
            end derivedReq ::> systemRequirementTraceability.req_FR02a;
        }
        #derivation connection trace_FR03_to_FR03a : FR03_to_FR03a {
            end origReq ::> req_transportPassengers;
            end derivedReq ::> systemRequirementTraceability.req_FR03a;
        }
        #derivation connection trace_FR04_to_FR04a : FR04_to_FR04a {
            end origReq ::> req_openDoorsAtDestination;
            end derivedReq ::> systemRequirementTraceability.req_FR04a;
        }
        #derivation connection trace_FR05_to_FR05a : FR05_to_FR05a {
            end origReq ::> req_closeDoorsBeforeMovement;
            end derivedReq ::> systemRequirementTraceability.req_FR05a;
        }
        #derivation connection trace_FR06_to_FR06a : FR06_to_FR06a {
            end origReq ::> req_displayCurrentFloor;
            end derivedReq ::> systemRequirementTraceability.req_FR06a;
        }
        #derivation connection trace_FR07_to_FR07a : FR07_to_FR07a {
            end origReq ::> req_processEmergencyRequests;
            end derivedReq ::> systemRequirementTraceability.req_FR07a;
        }
        #derivation connection trace_FR08_to_FR08a : FR08_to_FR08a {
            end origReq ::> req_detectOverloadConditions;
            end derivedReq ::> systemRequirementTraceability.req_FR08a;
        }
        #derivation connection trace_FR09_to_FR09a : FR09_to_FR09a {
            end origReq ::> req_preventMotionOverload;
            end derivedReq ::> systemRequirementTraceability.req_FR09a;
        }
        #derivation connection trace_SR01_to_SR01a : SR01_to_SR01a {
            end origReq ::> req_detectDoorObstruction;
            end derivedReq ::> systemRequirementTraceability.req_SR01a;
        }
        #derivation connection trace_SR02_to_SR02a : SR02_to_SR02a {
            end origReq ::> req_stopDoorClosingOnObstruction;
            end derivedReq ::> systemRequirementTraceability.req_SR02a;
        }
        #derivation connection trace_SR03_to_SR03a : SR03_to_SR03a {
            end origReq ::> req_stopElevatorCriticalFault;
            end derivedReq ::> systemRequirementTraceability.req_SR03a;
        }
        #derivation connection trace_SR04_to_SR04a : SR04_to_SR04a {
            end origReq ::> req_enterEmergencyMode;
            end derivedReq ::> systemRequirementTraceability.req_SR04a;
        }
        #derivation connection trace_PR01_to_PR01a : PR01_to_PR01a {
            end origReq ::> req_maxTravelTime;
            end derivedReq ::> systemRequirementTraceability.req_PR01a;
        }
        #derivation connection trace_PR02_to_PR02a : PR02_to_PR02a {
            end origReq ::> req_requestProcessingLatency;
            end derivedReq ::> systemRequirementTraceability.req_PR02a;
        }
        #derivation connection trace_PR03_to_PR03a : PR03_to_PR03a {
            end origReq ::> req_supportMaximumLoad;
            end derivedReq ::> systemRequirementTraceability.req_PR03a;
        }
    }
}