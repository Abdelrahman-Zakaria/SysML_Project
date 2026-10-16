package ElevatorVerification {
    private import ElevatorRequirements::*;
    private import ElevatorStructure::*;

    // ==========================================
    // 1. Functional Verifications (FR-01 to FR-07)
    // ==========================================
    verification def VerifyAcceptFloorRequests {
        subject uiSubsystem : UserInterfaceSubsystem;
        objective { verify requirement AcceptFloorRequests; }
    }

    verification def VerifyAcceptDestinationRequests {
        subject uiSubsystem : UserInterfaceSubsystem;
        objective { verify requirement AcceptDestinationRequests; }
    }

    verification def VerifyTransportPassengers {
        subject system : SmartElevatorSystem;
        objective { verify requirement TransportPassengers; }
    }

    verification def VerifyOpenDoorsAtDestination {
        subject doorSubsystem : DoorSubsystem;
        objective { verify requirement OpenDoorsAtDestination; }
    }

    verification def VerifyCloseDoorsBeforeMovement {
        subject doorSubsystem : DoorSubsystem;
        objective { verify requirement CloseDoorsBeforeMovement; }
    }

    verification def VerifyDisplayCurrentFloor {
        subject uiSubsystem : UserInterfaceSubsystem;
        objective { verify requirement DisplayCurrentFloor; }
    }

    verification def VerifyProcessEmergencyRequests {
        subject safetySubsystem : SafetySubsystem;
        objective { verify requirement ProcessEmergencyRequests; }
    }

    // ==========================================
    // 2. Safety Verifications (SR-01 to SR-04)
    // ==========================================
    verification def VerifyDetectDoorObstruction {
        subject doorSubsystem : DoorSubsystem;
        objective { verify requirement DetectDoorObstruction; }
    }

    verification def VerifyStopDoorClosingOnObstruction {
        subject doorSubsystem : DoorSubsystem;
        objective { verify requirement StopDoorClosingOnObstruction; }
    }

    verification def VerifyStopElevatorCriticalFault {
        subject safetySubsystem : SafetySubsystem;
        objective { verify requirement StopElevatorCriticalFault; }
    }

    verification def VerifyEnterEmergencyMode {
        subject safetySubsystem : SafetySubsystem;
        objective { verify requirement EnterEmergencyMode; }
    }

    // ==========================================
    // 3. Performance Verifications (PR-01 to PR-02)
    // ==========================================
    verification def VerifyMaxTravelTime {
        subject system : SmartElevatorSystem;
        objective { verify requirement MaxTravelTime; }
    }

    verification def VerifyRequestLatency {
        subject controller : Controller;
        objective { verify requirement RequestProcessingLatency; }
    }
}