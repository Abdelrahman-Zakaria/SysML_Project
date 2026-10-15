package ElevatorVerification {
    private import ElevatorRequirements::*;
    private import ElevatorStructure::*;

    verification def VerifyTravelTime {
        subject system : SmartElevatorSystem;
        objective {
            verify requirement MaxTravelTime;
        }
    }

    verification def VerifyDoorObstructionHandling {
        subject doorSubsystem : DoorSubsystem;
        objective {
            verify requirement DetectDoorObstruction;
        }
    }

    verification def VerifyEmergencyModeTransition {
        subject safetySubsystem : SafetySubsystem;
        objective {
            verify requirement EnterEmergencyMode;
        }
    }

    verification def VerifyRequestLatency {
        subject controller : Controller;
        objective {
            verify requirement RequestProcessingLatency;
        }
    }
}