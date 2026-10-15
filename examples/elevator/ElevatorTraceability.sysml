package ElevatorTraceability {
    private import ElevatorRequirements::*;

    // Derived lower-level requirements establishing functional hierarchy
    requirement def <'SR-01a'> DoorSensorSensitivity {
        doc /* Object detection sensors shall trigger on obstacles larger than 10mm in thickness. */
    }

    requirement def <'PR-01a'> AccelerationRampUp {
        doc /* Motor drive acceleration rate shall achieve nominal cruise speed within 2.0 seconds. */
    }

    // Traceability links using deriveRequirement
    deriveRequirement SR-01a from SR-01 DetectDoorObstruction;
    deriveRequirement PR-01a from PR-01 MaxTravelTime;
}