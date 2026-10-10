package ElevatorStructure {

    part def SmartElevatorSystem {
        part elevatorCar : ElevatorCar;
        part controller : Controller;
        part doorSubsystem : DoorSubsystem;
    }

    part def ElevatorCar;
    part def Controller;
    part def DoorSubsystem;
}
