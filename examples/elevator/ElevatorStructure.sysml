package ElevatorStructure {
    private import ScalarValues::*;

    // =====================
    // Enumerations & Types
    // =====================
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

    // ===========================
    // Subsystem Part Definitions
    // ===========================
    part def ElevatorCar {
        attribute currentFloor : Integer;
        attribute loadWeight : Real;
        attribute capacity : Real = 1000.0; // kg
    }

    part def Controller {
        attribute targetFloor : Integer;
        attribute direction : ElevatorDirection;
    }

    part def DoorSubsystem {
        attribute doorStatus : DoorStatus;
        attribute obstructionDetected : Boolean;
    }

    part def MotorSubsystem {
        attribute motorSpeed : Real;
        attribute isRunning : Boolean;
    }

    part def PositionSubsystem {
        attribute currentFloorSensor : Integer;
        attribute rawPosition : Real;
    }

    part def SafetySubsystem {
        attribute overloadDetected : Boolean;
        attribute emergencyActive : Boolean;
    }

    part def UserInterfaceSubsystem {
        attribute floorButtonPressed : Integer;
        attribute alarmButtonPressed : Boolean;
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
    }
}
