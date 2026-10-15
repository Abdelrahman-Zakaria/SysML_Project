package ElevatorArchitecture {
    private import ElevatorRequirements::*;
    private import ElevatorStructure::*;

    // ==========================================
    // Functional Requirement Usages (FR-01 to FR-07)
    // ==========================================
    requirement req_acceptFloorRequests : AcceptFloorRequests;
    requirement req_acceptDestinationRequests : AcceptDestinationRequests;
    requirement req_transportPassengers : TransportPassengers;
    requirement req_openDoorsAtDestination : OpenDoorsAtDestination;
    requirement req_closeDoorsBeforeMovement : CloseDoorsBeforeMovement;
    requirement req_displayCurrentFloor : DisplayCurrentFloor;
    requirement req_processEmergencyRequests : ProcessEmergencyRequests;

    // ==========================================
    // Safety Requirement Usages (SR-01 to SR-04)
    // ==========================================
    requirement req_detectDoorObstruction : DetectDoorObstruction;
    requirement req_stopDoorClosingOnObstruction : StopDoorClosingOnObstruction;
    requirement req_stopElevatorCriticalFault : StopElevatorCriticalFault;
    requirement req_enterEmergencyMode : EnterEmergencyMode;

    // ==========================================
    // Performance Requirement Usages (PR-01 to PR-02)
    // ==========================================
    requirement req_maxTravelTime : MaxTravelTime;
    requirement req_requestProcessingLatency : RequestProcessingLatency;

    // ==========================================
    // Requirement Satisfaction Relationships
    // ==========================================
    
    // Functional Satisfactions
    satisfy req_acceptFloorRequests by SmartElevatorSystem::uiSubsystem;
    satisfy req_acceptDestinationRequests by SmartElevatorSystem::uiSubsystem;
    satisfy req_transportPassengers by SmartElevatorSystem::motorSubsystem;
    satisfy req_openDoorsAtDestination by SmartElevatorSystem::doorSubsystem;
    satisfy req_closeDoorsBeforeMovement by SmartElevatorSystem::doorSubsystem;
    satisfy req_displayCurrentFloor by SmartElevatorSystem::uiSubsystem;
    satisfy req_processEmergencyRequests by SmartElevatorSystem::safetySubsystem;

    // Safety Satisfactions
    satisfy req_detectDoorObstruction by SmartElevatorSystem::doorSubsystem;
    satisfy req_stopDoorClosingOnObstruction by SmartElevatorSystem::doorSubsystem;
    satisfy req_stopElevatorCriticalFault by SmartElevatorSystem::safetySubsystem;
    satisfy req_enterEmergencyMode by SmartElevatorSystem::safetySubsystem;

    // Performance Satisfactions
    satisfy req_maxTravelTime by SmartElevatorSystem::motorSubsystem;
    satisfy req_requestProcessingLatency by SmartElevatorSystem::controller;
}