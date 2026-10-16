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
    requirement def <'FR-08'> DetectOverloadConditions {
        doc /* The system shall detect overload conditions. */
    }
    requirement def <'FR-09'> PreventMotionOverload {
        doc /* The system shall prevent motion during overload. */
    }
    requirement def <'FR-10'> PreventMotionDoorsOpen {
        doc /* The system shall prevent motion while doors are open. */
    }
    requirement def <'FR-11'> MaintainCabinLighting {
        doc /* The system shall maintain cabin illumination while the elevator is in service. */
    }
    requirement def <'FR-12'> OperateVentilation {
        doc /* The system shall operate cabin ventilation fans when passengers are detected. */
    }
    requirement def <'FR-13'> SupportRemoteDiagnostics {
        doc /* The system shall support remote querying of its current operational state. */
    }
    requirement def <'FR-14'> OptimizeWaitTime {
        doc /* The system shall optimize passenger waiting time based on request queues. */
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
    requirement def <'SR-05'> UtilizeBackupPower {
        doc /* The system shall utilize backup battery power to reach the nearest floor during a main power failure. */
    }
    requirement def <'SR-06'> ProvideIntercom {
        doc /* The system shall provide a two-way emergency communication intercom in the cabin. */
    }
    requirement def <'SR-07'> ExecuteFireRecall {
        doc /* The system shall automatically return to the ground floor and open doors when a building fire alarm is detected. */
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
    requirement def <'PR-03'> SupportMaximumLoad {
        doc /* The system shall support up to 1000 kg load. */
    }
    requirement def <'PR-04'> DoorOperationSpeed {
        doc /* The system shall fully open or close the doors within 3.0 seconds. */
    }
    requirement def <'PR-05'> MaintenanceResponseTime {
        doc /* The system shall enter maintenance mode within 1.0 second of a valid technician request. */
    }

}