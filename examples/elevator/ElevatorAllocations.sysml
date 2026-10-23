package ElevatorAllocations {
    private import ElevatorStructure::*;
    private import ElevatorBehavior::*;

    // ==========================================
    // 1. Declare Action Usages (Features)
    // ==========================================
    action receiveRequest : ReceiveRequest;
    action selectDestination : SelectDestination;
    action scheduleMovement : ScheduleMovement;
    action moveElevator : MoveElevator;
    action moveToDestination : MoveToDestination;
    action arriveAtFloor : ArriveAtFloor;
    action openDoor : OpenDoor;
    action boardPassenger : BoardPassenger;
    action exitPassenger : ExitPassenger;
    action detectOverload : DetectOverload;
    action runDiagnostics : RunDiagnostics;
    action enterMaintenanceMode : EnterMaintenanceMode;
    action startAudio : StartAudio;
    action stopAudio : StopAudio;
    action recallToGround : RecallToGround;
    action switchToBattery : SwitchToBattery;
    action startIntercom : StartIntercom;
    action endIntercom : EndIntercom;

    // ==========================================
    // 2. Allocate Action Features to Part Features
    // ==========================================
    
    // User Interface Actions
    allocate receiveRequest to SmartElevatorSystem::uiSubsystem;
    allocate selectDestination to SmartElevatorSystem::uiSubsystem;

    // Control Subsystem Actions
    allocate scheduleMovement to SmartElevatorSystem::controller;

    // Motor Subsystem Actions
    allocate moveElevator to SmartElevatorSystem::motorSubsystem;
    allocate moveToDestination to SmartElevatorSystem::motorSubsystem;

    // Position Subsystem Actions
    allocate arriveAtFloor to SmartElevatorSystem::positionSubsystem;

    // Door Subsystem Actions
    allocate openDoor to SmartElevatorSystem::doorSubsystem;

    // Elevator Cabin / Passenger Operations
    allocate boardPassenger to SmartElevatorSystem::elevatorCar;
    allocate exitPassenger to SmartElevatorSystem::elevatorCar;

    // Safety Subsystem Actions
    allocate detectOverload to SmartElevatorSystem::safetySubsystem;

    // Maintenance Subsystem Actions
    allocate runDiagnostics to SmartElevatorSystem::maintenanceSubsystem;
    allocate enterMaintenanceMode to SmartElevatorSystem::maintenanceSubsystem;

    allocate startAudio to SmartElevatorSystem::soundSubsystem;
    allocate stopAudio to SmartElevatorSystem::soundSubsystem;

    // Fire Recall Actions
    allocate recallToGround to SmartElevatorSystem::controller;

    // Power Subsystem Actions
    allocate switchToBattery to SmartElevatorSystem::powerSubsystem;

    // Intercom Actions
    allocate startIntercom to SmartElevatorSystem::intercomSubsystem;
    allocate endIntercom to SmartElevatorSystem::intercomSubsystem;
}