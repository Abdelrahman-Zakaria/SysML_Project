package ElevatorStructure {
    private import ScalarValues::*;

    // =======================
    // Enumerations & Types
    // =======================
    enum def DoorStatus {
        enum OPEN;
        enum CLOSED;
        enum OPENING;
        enum CLOSING;
    }

    enum def ElevatorDirection {
        enum UP;
        enum DOWN;
        enum IDLE;
    }

    // ===================
    // Item Definitions
    // ===================
    item def FloorRequest;
    item def PositionData;
    item def DoorCommand;
    item def AlarmMessage;
    item def SafetyEvent;

    // =======================
    // Interface Definitions
    // =======================
    interface def UserRequestInterface;
    interface def PositionInterface;
    interface def DoorControlInterface;
    interface def MotorControlInterface;
    interface def SafetyInterface;

    // =======================================
    // Subsystem Part Definitions with Ports
    // =======================================
    part def ElevatorCar {
        attribute currentFloor : Integer;
        attribute loadWeight : Real;
        attribute capacity : Real = 1000.0; // kg
    }

    part def Controller {
        attribute targetFloor : Integer;
        attribute direction : ElevatorDirection;
        
        port requestPort : UserRequestInterface;
        port positionPort : PositionInterface;
        port doorControlPort : DoorControlInterface;
        port motorControlPort : MotorControlInterface;
        port safetyPort : SafetyInterface;
    }

    part def DoorSubsystem {
        attribute doorStatus : DoorStatus;
        attribute obstructionDetected : Boolean;
        port doorControlPort : DoorControlInterface;
    }

    part def MotorSubsystem {
        attribute motorSpeed : Real;
        attribute isRunning : Boolean;
        port motorControlPort : MotorControlInterface;
    }

    part def PositionSubsystem {
        attribute currentFloorSensor : Integer;
        attribute rawPosition : Real;
        port positionPort : PositionInterface;
    }

    part def SafetySubsystem {
        attribute overloadDetected : Boolean;
        attribute emergencyActive : Boolean;
        port safetyPort : SafetyInterface;
    }

    part def UserInterfaceSubsystem {
        attribute floorButtonPressed : Integer;
        attribute alarmButtonPressed : Boolean;
        port requestPort : UserRequestInterface;
    }

    part def MaintenanceSubsystem {
        attribute inMaintenanceMode : Boolean;
        attribute lastServiceDate : String;
    }

    // =======================================
    // System Composition (Top-Level System)
    // =======================================
    part def SmartElevatorSystem {
        attribute totalFloors : Integer = 10;

        // Structural Composition (Part Usages)
        part elevatorCar : ElevatorCar;
        part controller : Controller;
        part doorSubsystem : DoorSubsystem;
        part motorSubsystem : MotorSubsystem;
        part positionSubsystem : PositionSubsystem;
        part safetySubsystem : SafetySubsystem;
        part uiSubsystem : UserInterfaceSubsystem;
        part maintenanceSubsystem : MaintenanceSubsystem;

        // Connections (Deliverable 10)
        connect uiSubsystem.requestPort to controller.requestPort;
        connect positionSubsystem.positionPort to controller.positionPort;
        connect controller.doorControlPort to doorSubsystem.doorControlPort;
        connect controller.motorControlPort to motorSubsystem.motorControlPort;
        connect safetySubsystem.safetyPort to controller.safetyPort;
    }
}
