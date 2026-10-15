package ElevatorAllocations {
    private import ElevatorStructure::*;
    private import ElevatorBehavior::*;

    part allocationModel {
        // Behavioral Usages
        action scheduleMovement : ElevatorBehavior::ScheduleMovement;
        action moveElevator : ElevatorBehavior::MoveElevator;
        action openDoor : ElevatorBehavior::OpenDoor;
        action arriveAtFloor : ElevatorBehavior::ArriveAtFloor;
        action receiveRequest : ElevatorBehavior::ReceiveRequest;
        action detectOverload : ElevatorBehavior::DetectOverload;

        // Structural Usages
        part controller : ElevatorStructure::Controller;
        part motorSubsystem : ElevatorStructure::MotorSubsystem;
        part doorSubsystem : ElevatorStructure::DoorSubsystem;
        part positionSubsystem : ElevatorStructure::PositionSubsystem;
        part userInterfaceSubsystem : ElevatorStructure::UserInterfaceSubsystem;
        part safetySubsystem : ElevatorStructure::SafetySubsystem;

        // Explicit Instance Allocations
        allocate scheduleMovement to controller;
        allocate moveElevator to motorSubsystem;
        allocate openDoor to doorSubsystem;
        allocate arriveAtFloor to positionSubsystem;
        allocate receiveRequest to userInterfaceSubsystem;
        allocate detectOverload to safetySubsystem;
    }
}