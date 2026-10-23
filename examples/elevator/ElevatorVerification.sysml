package ElevatorVerification {
    private import ElevatorRequirements::*;
    private import ElevatorStructure::*;
    private import ElevatorArchitecture::*;
    
    // ==========================================
    // 1. Functional Verifications (FR-01 to FR-15)    // ==========================================

    verification def VerifyAcceptFloorRequests {
        subject uiSubsystem : UserInterfaceSubsystem;
        objective {
            doc /* Issue a hall-call floor request and confirm it is accepted and passed on to the controller. */
            verify req_acceptFloorRequests;
        }
    }

    verification def VerifyAcceptDestinationRequests {
        subject uiSubsystem : UserInterfaceSubsystem;
        objective {
            doc /* Enter a destination from the cabin and confirm it is accepted and passed on to the controller. */
            verify req_acceptDestinationRequests;
        }
    }

    verification def VerifyTransportPassengers {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Run a trip between two floors and confirm the cabin arrives at the requested floor. */
            verify req_transportPassengers;
        }
    }

    verification def VerifyOpenDoorsAtDestination {
        subject doorSubsystem : DoorSubsystem;
        objective {
            doc /* On arrival at the destination floor, confirm doorStatus goes to OPENING and then OPEN. */
            verify req_openDoorsAtDestination;
        }
    }

    verification def VerifyCloseDoorsBeforeMovement {
        subject doorSubsystem : DoorSubsystem;
        objective {
            doc /* Request movement while the doors are not CLOSED and confirm the cabin does not start moving until doorStatus is CLOSED. */
            verify req_closeDoorsBeforeMovement;
        }
    }

    verification def VerifyDisplayCurrentFloor {
        subject uiSubsystem : UserInterfaceSubsystem;
        objective {
            doc /* Move the cabin between floors and confirm the cabin display shows the current floor reported by the position subsystem. */
            verify req_displayCurrentFloor;
        }
    }

    verification def VerifyProcessEmergencyRequests {
        subject safetySubsystem : SafetySubsystem;
        objective {
            doc /* Press the cabin alarm button and confirm the emergency request is processed (emergencyActive set, alarm raised). */
            verify req_processEmergencyRequests;
        }
    }

    verification def VerifyDetectOverloadConditions {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Load the cabin above its 1000 kg capacity and confirm overloadDetected becomes true; confirm it is not raised at or below capacity. The exact boundary at 1000 kg is not specified and needs team confirmation. */
            verify req_detectOverloadConditions;
        }
    }

    verification def VerifyPreventMotionOverload {
        subject system : SmartElevatorSystem;
        objective {
            doc /* With overloadDetected true, issue a floor request and confirm the cabin does not move (isRunning stays false); confirm motion is allowed again after the overload clears. */
            verify req_preventMotionOverload;
        }
    }

    verification def VerifyPreventMotionDoorsOpen {
        subject system : SmartElevatorSystem;
        objective {
            doc /* With doorStatus not CLOSED, issue a floor request and confirm the cabin does not move. */
            verify req_preventMotionDoorsOpen;
        }
    }

    verification def VerifyMaintainCabinLighting {
        subject elevatorCar : ElevatorCar;
        objective {
            doc /* While the elevator is in service, confirm cabin illumination stays on. No lighting element is modeled yet. */
            verify req_maintainCabinLighting;
        }
    }

    verification def VerifyOperateVentilation {
        subject elevatorCar : ElevatorCar;
        objective {
            doc /* With passengers detected in the cabin, confirm the ventilation fans operate. No ventilation or passenger-detection element is modeled yet. */
            verify req_operateVentilation;
        }
    }

    verification def VerifySupportRemoteDiagnostics {
        subject maintenanceSubsystem : MaintenanceSubsystem;
        objective {
            doc /* Query the current operational state remotely and confirm the response reflects the actual state. No remote link is modeled yet. */
            verify req_supportRemoteDiagnostics;
        }
    }

    verification def VerifyOptimizeWaitTime {
        subject controller : Controller;
        objective {
            doc /* Apply a set of queued requests and confirm the controller's scheduling gives a lower average wait time than serving them strictly in arrival order. Average wait time is computed as in AverageWaitTimeConstraint. */
            verify req_optimizeWaitTime;
        }
    }
    verification def VerifyPlayAudioDuringMotion {
        subject soundSubsystem : SoundSubsystem;
        objective {
            doc /* Move the cabin between floors and confirm audio plays only while the cabin is moving; confirm it is muted when the cabin is stationary and halts when the doors begin opening. */
            verify req_playAudioDuringMotion;
        }
    }

    // ==========================================
    // 2. Safety Verifications (SR-01 to SR-07)
    // ==========================================

    verification def VerifyDetectDoorObstruction {
        subject doorSubsystem : DoorSubsystem;
        objective {
            doc /* Place an obstruction in the door pathway and confirm obstructionDetected becomes true. */
            verify req_detectDoorObstruction;
        }
    }

    verification def VerifyStopDoorClosingOnObstruction {
        subject doorSubsystem : DoorSubsystem;
        objective {
            doc /* Place an obstruction while the doors are closing and confirm closing stops immediately and the doors reverse. */
            verify req_stopDoorClosingOnObstruction;
        }
    }

    verification def VerifyStopElevatorCriticalFault {
        subject safetySubsystem : SafetySubsystem;
        objective {
            doc /* Inject a critical motor fault and a critical sensor fault while the cabin is moving and confirm movement halts in each case. What counts as critical needs team definition. */
            verify req_stopElevatorCriticalFault;
        }
    }

    verification def VerifyEnterEmergencyMode {
        subject safetySubsystem : SafetySubsystem;
        objective {
            doc /* Trigger the safety subsystem and confirm the system transitions to Emergency mode. */
            verify req_enterEmergencyMode;
        }
    }

    verification def VerifyUtilizeBackupPower {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Remove main power and confirm the cabin uses backup battery power to reach the nearest floor. No power element is modeled yet. */
            verify req_utilizeBackupPower;
        }
    }

    verification def VerifyProvideIntercom {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Activate the cabin intercom and confirm two-way communication. No intercom element is modeled yet. */
            verify req_provideIntercom;
        }
    }

    verification def VerifyExecuteFireRecall {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Raise a building fire alarm with the cabin at any floor and confirm it returns to the ground floor automatically and opens its doors. No fire-alarm input is modeled yet. */
            verify req_executeFireRecall;
        }
    }

    // ==========================================
    // 3. Performance Verifications (PR-01 to PR-05)
    // ==========================================

    verification def VerifyMaxTravelTime {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Measure departure-to-arrival time for requested floors and confirm each is within 30 seconds. */
            verify req_maxTravelTime;
        }
    }

    verification def VerifyRequestLatency {
        subject controller : Controller;
        objective {
            doc /* Measure the time from a user request to its acknowledgement and confirm it is within 500 ms. */
            verify req_requestProcessingLatency;
        }
    }

    verification def VerifySupportMaximumLoad {
        subject system : SmartElevatorSystem;
        objective {
            doc /* Load the cabin up to 1000 kg and confirm normal operation. The mechanical and drive rating is not modeled; this is a physical load test. */
            verify req_supportMaximumLoad;
        }
    }

    verification def VerifyDoorOperationSpeed {
        subject doorSubsystem : DoorSubsystem;
        objective {
            doc /* Measure a full door open and a full door close and confirm each completes within 3.0 seconds. */
            verify req_doorOperationSpeed;
        }
    }

    verification def VerifyMaintenanceResponseTime {
        subject maintenanceSubsystem : MaintenanceSubsystem;
        objective {
            doc /* Send a valid technician request and confirm inMaintenanceMode becomes true within 1.0 second. */
            verify req_maintenanceResponseTime;
        }
    }

    // ==========================================
    // 4. Added Verifications (Fire Recall, Backup Power)
    // ==========================================

    verification def VerifyFireAlarmInput {
        subject fireInterface : FireInterfaceSubsystem;
        objective {
            doc /* Raise a building fire alarm and confirm fireAlarmActive becomes true and a FireAlarmSignal reaches the controller. */
            verify req_executeFireRecall;
        }
    }

    verification def VerifyBackupPowerSwitchover {
        subject powerSubsystem : PowerSubsystem;
        objective {
            doc /* Remove main power and confirm activeSource changes from MAINS to BATTERY and a PowerStatus message reaches the controller. */
            verify req_utilizeBackupPower;
        }
    }
}