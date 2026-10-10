package ElevatorBehavior {
    // define actions 

    action def ReceiveRequest;
    action def ScheduleMovement;
    action def MoveElevator;
    action def ArriveAtFloor;
    action def OpenDoor;
    action def BoardPassenger;
    action def SelectDestination;
    action def MoveToDestination;
    action def ExitPassenger;


    action def ElevatorTrip {
        action receiveRequest : ReceiveRequest;
        action scheduleMovement : ScheduleMovement;
        action moveElevator : MoveElevator;
        action arriveAtFloor : ArriveAtFloor;
        action openDoor1 : OpenDoor;
        action boardPassenger : BoardPassenger;
        action selectDestination : SelectDestination;
        action moveToDestination : MoveToDestination;
        action openDoor2 : OpenDoor;
        action exitPassenger : ExitPassenger;

        first receiveRequest then scheduleMovement;
        first scheduleMovement then moveElevator;
        first moveElevator then arriveAtFloor;
        first arriveAtFloor then openDoor1;
        first openDoor1 then boardPassenger;
        first boardPassenger then selectDestination;
        first selectDestination then moveToDestination;
        first moveToDestination then openDoor2;
        first openDoor2 then exitPassenger;
    }


    // =========================
    // Elevator State Machine
    // =========================

    state def ElevatorStates {

        state Idle;
        state MovingUp;
        state MovingDown;

        state DoorOpening;
        state DoorOpen;
        state DoorClosing;

        state Overloaded;
        state Emergency;
        state Maintenance;
        state Fault;
    }



}
