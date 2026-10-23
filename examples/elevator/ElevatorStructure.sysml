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
    item def FloorRequest {
        attribute targetFloor : Integer;
        attribute directionRequest : ElevatorDirection;
    }
    
    item def PositionData {
        attribute currentFloor : Integer;
        attribute exactPosition : Real;
    }
    
    item def DoorCommand {
        attribute commandedStatus : DoorStatus;
    }
    
    item def AlarmMessage {
        attribute isAlarmTriggered : Boolean;
    }
    
    item def SafetyEvent {
        attribute isOverloaded : Boolean;
        attribute emergencyActive : Boolean;
    }

    item def MotorCommand {
        attribute targetSpeed : Real;
        attribute targetDirection : ElevatorDirection;
    }

    item def MaintenanceLog {
        attribute isMaintenanceMode : Boolean;
        attribute diagnosticCode : Integer;
    }

    item def AudioCommand {
        attribute playMusic : Boolean;
        attribute announcementId : Integer;
        attribute playOverloadWarning : Boolean;
    }

    item def LoadData {
    attribute loadWeight : Real;
    attribute capacity : Real;
    }

    // =======================
    // Interface Definitions
    // =======================
    interface def UserRequestInterface {
        end source;
        end target;
    }
    interface def PositionInterface {
        end source;
        end target;
    }
    interface def DoorControlInterface {
        end source;
        end target;
    }
    interface def MotorControlInterface {
        end source;
        end target;
    }
    interface def SafetyInterface {
        end source;
        end target;
    }
    interface def MaintenanceInterface { 
         end source; 
         end target; 
    }
    interface def AudioControlInterface {
        end source;
        end target;
    }

    interface def LoadInterface {
    end source;
    end target;
    }

    // =======================================
    // Subsystem Part Definitions with Ports
    // =======================================
    part def ElevatorCar {
        attribute currentFloor : Integer;
        attribute loadWeight : Real;
        attribute capacity : Real = 1000.0; // kg
        port loadPort : LoadInterface;
    }

    part def Controller {
        attribute targetFloor : Integer;
        attribute direction : ElevatorDirection;
        attribute isOverloaded : Boolean = false;
        
        port requestPort : UserRequestInterface;
        port positionPort : PositionInterface;
        port doorControlPort : DoorControlInterface;
        port motorControlPort : MotorControlInterface;
        port safetyPort : SafetyInterface;
        port maintenancePort : MaintenanceInterface;
        port audioPort : AudioControlInterface;
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
        port loadPort : LoadInterface;
    }

    part def UserInterfaceSubsystem {
        attribute floorButtonPressed : Integer;
        attribute alarmButtonPressed : Boolean;
        port requestPort : UserRequestInterface;
    }

    part def MaintenanceSubsystem {
        attribute inMaintenanceMode : Boolean;
        attribute lastServiceDate : String;
        port maintenancePort : MaintenanceInterface;
    }

    part def SoundSubsystem {
        attribute volumeLevel : Real;
        attribute isPlaying : Boolean;
        port audioPort : AudioControlInterface;
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
        part soundSubsystem : SoundSubsystem;

        // Connections with Item Flows (Deliverable 10)
        connect uiSubsystem.requestPort to controller.requestPort {
            flow of FloorRequest;
        }
        
        connect positionSubsystem.positionPort to controller.positionPort {
            flow of PositionData;
        }
        
        connect controller.doorControlPort to doorSubsystem.doorControlPort {
            flow of DoorCommand;
        }
        
        connect controller.motorControlPort to motorSubsystem.motorControlPort {
            flow of MotorCommand;
        }
        
        connect safetySubsystem.safetyPort to controller.safetyPort {
            flow of SafetyEvent;
        }
        
        connect maintenanceSubsystem.maintenancePort to controller.maintenancePort {
            flow of MaintenanceLog;
        }

        connect controller.audioPort to soundSubsystem.audioPort {
            flow of AudioCommand; 
        }

        connect elevatorCar.loadPort to safetySubsystem.loadPort {
        flow of LoadData;
        }
    }
}
