package ElevatorBehavior {

    private import ScalarValues::*;
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

  // 2. Action Sequences
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

  // 3. Event Definitions

        item def FloorRequestReceived;
        item def DestinationReached;
        item def DoorFullyOpen;
        item def DoorFullyClosed;
        item def TimerExpired;
        item def EmergencyDetected;
        item def EmergencyCleared;
        item def OverloadDetected;
        item def OverloadCleared;
        item def MaintenanceRequested;
        item def MaintenanceCompleted;
        item def FaultDetected;
        item def FaultCleared;


    // =========================
    // Elevator State Machine
    // =========================

    state def ElevatorStates {

        in attribute currentFloor : Integer;
        in attribute targetFloor : Integer;

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

    transition requestUp
        first Idle
        accept FloorRequestReceived
        if targetFloor > currentFloor
        then MovingUp;

    transition requestDown
        first Idle
        accept FloorRequestReceived
        if targetFloor < currentFloor
        then MovingDown;


    // Movement -> Door Opening

    transition reachedFromAbove
        first MovingUp
        accept DestinationReached
        then DoorOpening;

    transition reachedFromBelow
        first MovingDown
        accept DestinationReached
        then DoorOpening;

    // Door Operations

    transition doorOpened
        first DoorOpening
        accept DoorFullyOpen
        then DoorOpen;

    transition closeAfterTimer
        first DoorOpen
        accept TimerExpired
        then DoorClosing;

    transition doorClosed
        first DoorClosing
        accept DoorFullyClosed
        then Idle;   

    // Emergency Handling

    transition emergencyFromIdle
        first Idle
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromMovingUp
        first MovingUp
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromMovingDown
        first MovingDown
        accept EmergencyDetected
        then Emergency;

    transition clearEmergency
        first Emergency
        accept EmergencyCleared
        then Idle;  
         
    // Emergency from the remaining states

    transition emergencyFromDoorOpening
        first DoorOpening
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromDoorOpen
        first DoorOpen
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromDoorClosing
        first DoorClosing
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromOverloaded
        first Overloaded
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromMaintenance
        first Maintenance
        accept EmergencyDetected
        then Emergency;

    transition emergencyFromFault
        first Fault
        accept EmergencyDetected
        then Emergency;

    // Overload Handling
    transition detectOverload
        first Idle
        accept OverloadDetected
        then Overloaded;
    
    transition clearOverload
        first Overloaded
        accept OverloadCleared
        then Idle;  
   
    // Maintenance mode

    transition enterMaintenance
        first Idle
        accept MaintenanceRequested
        then Maintenance;

    transition exitMaintenance
        first Maintenance
        accept MaintenanceCompleted
        then Idle; 
        
        
        // Fault handling

    transition detectFault
        first Idle
        accept FaultDetected
        then Fault;

    transition faultWhileMovingUp
        first MovingUp
        accept FaultDetected
        then Fault;

    transition faultWhileMovingDown
        first MovingDown
        accept FaultDetected
        then Fault;

    transition clearFault
        first Fault
        accept FaultCleared
        then Idle;
    }



}
