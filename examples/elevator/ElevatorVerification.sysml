package ElevatorVerification {
    private import ElevatorRequirements::*;
    private import ElevatorStructure::*;

    // Verification cases tying requirements to subjects via the 'verify' keyword
    verification def VerifyTravelTime {
        subject system : SmartElevatorSystem;
        verify requirement req : MaxTravelTime;
    }

    verification def VerifyDoorObstructionHandling {
        subject doorSubsystem : DoorSubsystem;
        verify requirement req : DetectDoorObstruction;
    }

    verification def VerifyEmergencyModeTransition {
        subject safetySubsystem : SafetySubsystem;
        verify requirement req : EnterEmergencyMode;
    }

    verification def VerifyRequestLatency {
        subject controller : Controller;
        verify requirement req : RequestProcessingLatency;
    }
}