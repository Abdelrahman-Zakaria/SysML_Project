package ElevatorRequirements {
    private import ScalarValues::*;

    // ==========================================
    // Functional Requirements (FR)
    // ==========================================
    requirement def <'FR-01'> AcceptFloorRequests {
        doc /* The system shall accept hall-call floor requests. */
    }
    requirement def <'FR-02'> AcceptDestinationRequests {
        doc /* The system shall accept cabin destination requests. */
    }
    requirement def <'FR-03'> TransportPassengers {
        doc /* The system shall transport passengers between floors. */
    }
    requirement def <'FR-04'> OpenDoorsAtDestination {
        doc /* The system shall open doors upon arriving at the destination floor. */
    }
    requirement def <'FR-05'> CloseDoorsBeforeMovement {
        doc /* The system shall close doors fully before initiating elevator movement. */
    }
    requirement def <'FR-06'> DisplayCurrentFloor {
        doc /* The system shall display the current floor to passengers in the cabin. */
    }
    requirement def <'FR-07'> ProcessEmergencyRequests {
        doc /* The system shall process emergency alarm requests from the cabin. */
    }

    // ==========================================
    // Safety Requirements (SR)
    // ==========================================
    requirement def <'SR-01'> DetectDoorObstruction {
        doc /* The system shall detect physical obstructions in the door pathway. */
    }
    requirement def <'SR-02'> StopDoorClosingOnObstruction {
        doc /* The system shall immediately stop and reverse door closing if an obstruction is detected. */
    }
    requirement def <'SR-03'> StopElevatorCriticalFault {
        doc /* The system shall halt elevator movement if a critical motor or sensor fault is detected. */
    }
    requirement def <'SR-04'> EnterEmergencyMode {
        doc /* The system shall transition to Emergency mode when triggered by the safety subsystem. */
    }

    // ==========================================
    // Performance Requirements (PR)
    // ==========================================
    requirement def <'PR-01'> MaxTravelTime {
        doc /* The system shall reach any requested floor within 30 seconds of departure. */
    }
    requirement def <'PR-02'> RequestProcessingLatency {
        doc /* The system shall process and acknowledge user requests within 500 ms. */
    }
}