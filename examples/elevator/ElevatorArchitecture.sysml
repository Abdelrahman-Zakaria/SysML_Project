package ElevatorArchitecture {
    private import ElevatorRequirements::*;
    private import ElevatorStructure::*;

     // ==========================================
// Functional Requirement Usages (FR-01 to FR-15)    // ==========================================
    requirement req_acceptFloorRequests : AcceptFloorRequests;
    requirement req_acceptDestinationRequests : AcceptDestinationRequests;
    requirement req_transportPassengers : TransportPassengers;
    requirement req_openDoorsAtDestination : OpenDoorsAtDestination;
    requirement req_closeDoorsBeforeMovement : CloseDoorsBeforeMovement;
    requirement req_displayCurrentFloor : DisplayCurrentFloor;
    requirement req_processEmergencyRequests : ProcessEmergencyRequests;
    requirement req_detectOverloadConditions : DetectOverloadConditions;
    requirement req_preventMotionOverload : PreventMotionOverload;
    requirement req_preventMotionDoorsOpen : PreventMotionDoorsOpen;
    requirement req_maintainCabinLighting : MaintainCabinLighting;
    requirement req_operateVentilation : OperateVentilation;
    requirement req_supportRemoteDiagnostics : SupportRemoteDiagnostics;
    requirement req_optimizeWaitTime : OptimizeWaitTime;
    requirement req_playAudioDuringMotion : PlayAudioDuringMotion;
    requirement req_activateOverloadAlarm : ActivateOverloadAlarm;

    // ==========================================
    // Safety Requirement Usages (SR-01 to SR-07)
    // ==========================================
    requirement req_detectDoorObstruction : DetectDoorObstruction;
    requirement req_stopDoorClosingOnObstruction : StopDoorClosingOnObstruction;
    requirement req_stopElevatorCriticalFault : StopElevatorCriticalFault;
    requirement req_enterEmergencyMode : EnterEmergencyMode;
    requirement req_utilizeBackupPower : UtilizeBackupPower;
    requirement req_provideIntercom : ProvideIntercom;
    requirement req_executeFireRecall : ExecuteFireRecall;

    // ==========================================
    // Performance Requirement Usages (PR-01 to PR-05)
    // ==========================================
    requirement req_maxTravelTime : MaxTravelTime;
    requirement req_requestProcessingLatency : RequestProcessingLatency;
    requirement req_supportMaximumLoad : SupportMaximumLoad;
    requirement req_doorOperationSpeed : DoorOperationSpeed;
    requirement req_maintenanceResponseTime : MaintenanceResponseTime;


    // ==========================================
    // Requirement Satisfaction Relationships
    // ==========================================
    
    // Functional Satisfactions

    satisfy req_acceptFloorRequests by SmartElevatorSystem::uiSubsystem;
    satisfy req_acceptDestinationRequests by SmartElevatorSystem::uiSubsystem;
    satisfy req_transportPassengers by SmartElevatorSystem::motorSubsystem;
    satisfy req_openDoorsAtDestination by SmartElevatorSystem::doorSubsystem;
    satisfy req_closeDoorsBeforeMovement by SmartElevatorSystem::doorSubsystem;
    satisfy req_closeDoorsBeforeMovement by SmartElevatorSystem::controller;
    satisfy req_displayCurrentFloor by SmartElevatorSystem::uiSubsystem;
    satisfy req_displayCurrentFloor by SmartElevatorSystem::positionSubsystem;
    satisfy req_processEmergencyRequests by SmartElevatorSystem::safetySubsystem;
    satisfy req_processEmergencyRequests by SmartElevatorSystem::uiSubsystem;
    satisfy req_detectOverloadConditions by SmartElevatorSystem::safetySubsystem;
    satisfy req_preventMotionOverload by SmartElevatorSystem::controller;
    satisfy req_preventMotionDoorsOpen by SmartElevatorSystem::controller;
    satisfy req_maintainCabinLighting by SmartElevatorSystem::elevatorCar;
    satisfy req_operateVentilation by SmartElevatorSystem::elevatorCar;
    satisfy req_supportRemoteDiagnostics by SmartElevatorSystem::maintenanceSubsystem;
    satisfy req_optimizeWaitTime by SmartElevatorSystem::controller;
    satisfy req_playAudioDuringMotion by SmartElevatorSystem::soundSubsystem;
    satisfy req_playAudioDuringMotion by SmartElevatorSystem::controller;
    satisfy req_activateOverloadAlarm by SmartElevatorSystem::safetySubsystem;
    satisfy req_activateOverloadAlarm by SmartElevatorSystem::controller;
    satisfy req_activateOverloadAlarm by SmartElevatorSystem::soundSubsystem;


    // Safety Satisfactions

    satisfy req_detectDoorObstruction by SmartElevatorSystem::doorSubsystem;
    satisfy req_stopDoorClosingOnObstruction by SmartElevatorSystem::doorSubsystem;
    satisfy req_stopElevatorCriticalFault by SmartElevatorSystem::safetySubsystem;
    satisfy req_stopElevatorCriticalFault by SmartElevatorSystem::controller;
    satisfy req_stopElevatorCriticalFault by SmartElevatorSystem::motorSubsystem;
    satisfy req_enterEmergencyMode by SmartElevatorSystem::safetySubsystem;
    satisfy req_utilizeBackupPower by SmartElevatorSystem::controller;
    satisfy req_utilizeBackupPower by SmartElevatorSystem::motorSubsystem;
    satisfy req_provideIntercom by SmartElevatorSystem::uiSubsystem;
    satisfy req_executeFireRecall by SmartElevatorSystem::controller;
    satisfy req_executeFireRecall by SmartElevatorSystem::doorSubsystem;

     // Performance Satisfactions

    satisfy req_maxTravelTime by SmartElevatorSystem::motorSubsystem;
    satisfy req_requestProcessingLatency by SmartElevatorSystem::controller;
    satisfy req_supportMaximumLoad by SmartElevatorSystem::elevatorCar;
    satisfy req_doorOperationSpeed by SmartElevatorSystem::doorSubsystem;
    satisfy req_maintenanceResponseTime by SmartElevatorSystem::maintenanceSubsystem;
}