# Smart Elevator Control System
## SysML v2 Team Project Specification

## Project Objective

Develop a complete SysML v2 model for a Smart Elevator Control System serving a 10-floor office building. The goal is to practice SysML v2 language concepts including requirements, structure, interfaces, behavior, states, allocations, analysis, verification, and traceability.
---

# System Description

The system shall:

- Transport passengers between floors.
- Accept hall-call and cabin requests.
- Control elevator movement.
- Control door operation.
- Detect overload conditions.
- Detect obstructions.
- Handle emergency scenarios.
- Provide maintenance and diagnostic capabilities.
- Optimize passenger waiting time.

The building contains:

- 10 Floors
- 1 Elevator Car
- Hall Call Panels
- Cabin Control Panel
- Elevator Controller
- Door Mechanism
- Motor System
- Position Sensors
- Weight Sensor
- Emergency Alarm
- Maintenance Console

---

# Stakeholders

## Primary Stakeholders

- Passenger
- Building Owner
- Maintenance Technician
- Safety Inspector

## Stakeholder Needs

- Safe transportation
- Fast response time
- Reliable operation
- Easy maintenance
- Regulatory compliance

---

# SysML v2 Modeling Scope

Students must model the following SysML v2 concepts:

## Requirements Modeling

- Requirement Definitions
- Requirement Usages
- Requirement Hierarchies
- Requirement Satisfaction
- Requirement Verification
- Requirement Traceability

Minimum: 25 requirements

## Structural Modeling

- Package Definitions
- Part Definitions
- Part Usages
- Attributes
- Item Definitions
- Composition Relationships

## Interface Modeling

- Interface Definitions
- Ports
- Connections
- Item Flows

## Behavioral Modeling

- Action Definitions
- Action Usages
- Flow Connections
- Functional Decomposition

## State-Based Modeling

- State Definitions
- Events
- State Transitions
- Guards

## Analysis Modeling

- Value Types
- Attributes
- Constraint Definitions
- Analysis Cases

## Architecture Relationships

- Allocation Relationships
- Satisfaction Relationships
- Verification Relationships

---

# System Requirements

## Functional Requirements

- FR-01 Accept floor requests.
- FR-02 Accept destination requests.
- FR-03 Transport passengers between floors.
- FR-04 Open doors at destination floor.
- FR-05 Close doors before movement.
- FR-06 Display current floor.
- FR-07 Process emergency requests.
- FR-08 Detect overload conditions.
- FR-09 Prevent motion during overload.
- FR-10 Prevent motion while doors are open.

## Safety Requirements

- SR-01 Detect door obstruction.
- SR-02 Stop door closing on obstruction.
- SR-03 Stop elevator during critical fault.
- SR-04 Enter emergency mode when required.

## Performance Requirements

- PR-01 Reach any floor within 30 seconds.
- PR-02 Process requests within 500 ms.
- PR-03 Support up to 1000 kg load.

you should extend these to at least 25 requirements.

---

# Required SysML v2 Structural Elements

## Part Definitions

- SmartElevatorSystem
- ElevatorCar
- Controller
- DoorSubsystem
- MotorSubsystem
- PositionSubsystem
- SafetySubsystem
- UserInterfaceSubsystem
- MaintenanceSubsystem

## Example Attributes

- currentFloor
- direction
- loadWeight
- capacity
- doorStatus

## Item Definitions

- FloorRequest
- PositionData
- DoorCommand
- AlarmMessage
- SafetyEvent

---

# Required SysML v2 Interfaces

## Interface Definitions

- UserRequestInterface
- PositionInterface
- DoorControlInterface
- MotorControlInterface
- SafetyInterface

## Ports

- requestPort
- positionPort
- motorControlPort
- doorControlPort
- safetyPort

you must model all connections between subsystems using SysML v2 ports and connections.

---

# Required Behavioral Model

Model the following flow using Action Definitions and Action Usages:

Receive Request
→ Schedule Movement
→ Move Elevator
→ Arrive At Floor
→ Open Door
→ Board Passenger
→ Select Destination
→ Move To Destination
→ Open Door
→ Exit Passenger

Students may refine the workflow further.

---

# Required State Machine

## States

- Idle
- MovingUp
- MovingDown
- DoorOpening
- DoorOpen
- DoorClosing
- Overloaded
- Emergency
- Maintenance
- Fault

## Example Transitions

- Idle → RequestReceived → MovingUp
- MovingUp → DestinationReached → DoorOpening
- DoorOpen → TimerExpired → DoorClosing
- Any State → EmergencyDetected → Emergency

---

# Allocation Model

Allocate behavior to system components.

Examples:

- Schedule Requests → Controller
- Move Elevator → MotorSubsystem
- Open Door → DoorSubsystem
- Detect Floor → PositionSubsystem
- Detect Overload → SafetySubsystem

---

# Parametric and Analysis Model

## Constraint Definitions

### Travel Time

TravelTime = NumberOfFloors × TimePerFloor

### Load Utilization

LoadUtilization = CurrentLoad / MaximumLoad

### Average Wait Time

AverageWaitTime = TotalPassengerWaitTime / NumberOfRequests

Students shall create at least two constraint definitions and one analysis case.

---
# Required Deliverables

1. Package Hierarchy
2. Requirement Model (25+ Requirements)
3. Requirement Traceability Model
4. Requirement Satisfaction Relationships
5. Requirement Verification Relationships
6. Part Definition Model
7. System Composition Model
8. Interface Definition Model
9. Item Definition Model
10. Ports and Connections Model
11. Action Definitions
12. Behavioral Flow Model
13. State Machine Model
14. Allocation Model
15. Constraint Definitions
16. Analysis Case
17. Final Integrated SysML v2 Model
18. Presentation

