package ElevatorAllocations {
    private import ElevatorStructure::*;
    private import ElevatorBehavior::*;

    // ==========================================
    // Allocation of Behavioral Actions to Structural Parts
    // ==========================================
    
    // User Interface Actions
    allocate ReceiveRequest to SmartElevatorSystem::uiSubsystem;
    allocate SelectDestination to SmartElevatorSystem::uiSubsystem;

    // Control Subsystem Actions
    allocate ScheduleMovement to SmartElevatorSystem::controller;

    // Motor Subsystem Actions
    allocate MoveElevator to SmartElevatorSystem::motorSubsystem;
    allocate MoveToDestination to SmartElevatorSystem::motorSubsystem;

    // Position Subsystem Actions
    allocate ArriveAtFloor to SmartElevatorSystem::positionSubsystem;

    // Door Subsystem Actions
    allocate OpenDoor to SmartElevatorSystem::doorSubsystem;

    // Elevator Cabin / Passenger Operations
    allocate BoardPassenger to SmartElevatorSystem::elevatorCar;
    allocate ExitPassenger to SmartElevatorSystem::elevatorCar;

    // Safety Subsystem Actions
    allocate DetectOverload to SmartElevatorSystem::safetySubsystem;
}
