package ElevatorParametrics {
    private import ScalarValues::*;
    private import ElevatorStructure::*;

    // ==========================================
    // Constraint Definitions
    // ==========================================

    // 1. Travel Time Constraint: TravelTime = NumberOfFloors * TimePerFloor
    calc def TravelTimeCalc {
        in numberOfFloors : Integer;
        in timePerFloor : Real; // seconds per floor
        return travelTime : Real = numberOfFloors * timePerFloor;
    }

    constraint def TravelTimeConstraint {
        in numberOfFloors : Integer;
        in timePerFloor : Real;
        in calculatedTravelTime : Real;

        calculatedTravelTime == numberOfFloors * timePerFloor
    }

    // 2. Load Utilization Constraint: LoadUtilization = CurrentLoad / MaximumLoad
    calc def LoadUtilizationCalc {
        in currentLoad : Real;
        in maximumLoad : Real;
        return utilizationRatio : Real = currentLoad / maximumLoad;
    }

    constraint def LoadUtilizationConstraint {
        in currentLoad : Real;
        in maximumLoad : Real;
        in utilization : Real;

        utilization == currentLoad / maximumLoad
    }

    // 3. Average Wait Time Constraint: AverageWaitTime = TotalPassengerWaitTime / NumberOfRequests
    calc def AverageWaitTimeCalc {
        in totalWaitTime : Real;
        in numberOfRequests : Integer;
        return avgWaitTime : Real = totalWaitTime / numberOfRequests;
    }

    constraint def AverageWaitTimeConstraint {
        in totalWaitTime : Real;
        in numberOfRequests : Integer;
        in avgWaitTime : Real;

        avgWaitTime == totalWaitTime / numberOfRequests
    }

    // 4. Battery Rescue Feasibility: battery energy must cover travel to the nearest floor
    calc def BatteryRescueCheck {
        in batteryEnergy : Real;     // available battery energy
        in energyPerFloor : Real;    // energy needed per floor travelled
        in floorsToNearest : Integer;
        return feasible : Boolean = batteryEnergy >= energyPerFloor * floorsToNearest;
    }

    constraint def BatteryRescueConstraint {
        in batteryEnergy : Real;
        in energyPerFloor : Real;
        in floorsToNearest : Integer;

        batteryEnergy >= energyPerFloor * floorsToNearest
    }

    // ==========================================
    // Analysis Case Model
    // ==========================================
    analysis def PeakHourWaitTimeAnalysis {
        subject elevatorSystem : SmartElevatorSystem;

        // Input parameters derived from system state
        in attribute observedTotalWaitTime : Real = 450.0; // seconds
        in attribute totalRequestsProcessed : Integer = 15;

        // Output result calculated via parametric relationship
        out attribute calculatedAvgWaitTime : Real;

        // Constraint evaluation
        constraint waitTimeAnalysis : AverageWaitTimeConstraint {
            in totalWaitTime = observedTotalWaitTime;
            in numberOfRequests = totalRequestsProcessed;
            in avgWaitTime = calculatedAvgWaitTime;
        }
    }
}