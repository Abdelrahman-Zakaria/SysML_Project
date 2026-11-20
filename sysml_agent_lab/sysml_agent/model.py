"""Milestone 1 - an immutable, SysML v2-flavoured mock model.

Everything here is a frozen dataclass holding tuples, so a Model can never be
mutated in place. "Changing" a model always means building a new one with
``dataclasses.replace``. That is what lets propose_operation guarantee that the
original model is untouched.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

# The only domains the validator accepts. Parts and requirements carry one,
# and a `satisfy` link is only sensible when both ends share a domain.
VALID_DOMAINS: frozenset = frozenset({"power", "propulsion", "navigation"})


@dataclass(frozen=True)
class Part:
    id: str
    name: str
    domain: str


@dataclass(frozen=True)
class Requirement:
    id: str
    name: str
    text: str
    domain: str


@dataclass(frozen=True)
class Satisfy:
    """SysML v2: `satisfy requirement <requirement_id> by <part_id>;`"""

    requirement_id: str
    part_id: str


@dataclass(frozen=True)
class Model:
    name: str
    parts: tuple = ()
    requirements: tuple = ()
    satisfies: tuple = ()

    def all_ids(self) -> tuple:
        """Every element ID (parts first, then requirements), duplicates kept."""
        return tuple(p.id for p in self.parts) + tuple(r.id for r in self.requirements)

    def fingerprint(self) -> str:
        """Stable SHA-256 of the model content.

        Lets later milestones tie a validation result to the exact candidate
        it was computed on.
        """
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_mock_model() -> Model:
    """A small autonomous rover. R-005 is intentionally left unsatisfied."""
    return Model(
        name="RoverSystem",
        parts=(
            Part("P-BAT", "BatteryPack", "power"),
            Part("P-PDU", "PowerDistributionUnit", "power"),
            Part("P-MOT", "DriveMotorAssembly", "propulsion"),
            Part("P-WHL", "WheelDriveTrain", "propulsion"),
            Part("P-GPS", "GnssReceiver", "navigation"),
            Part("P-NAV", "NavigationComputer", "navigation"),
        ),
        requirements=(
            Requirement("R-001", "Endurance",
                        "The rover shall operate for at least 4 hours on a single battery charge.",
                        "power"),
            Requirement("R-002", "CruiseSpeed",
                        "The rover shall sustain a speed of 1.5 m/s on level terrain.",
                        "propulsion"),
            Requirement("R-003", "PositionAccuracy",
                        "The rover shall determine its position to within 2 meters.",
                        "navigation"),
            Requirement("R-004", "BusVoltage",
                        "The rover shall regulate bus voltage within 24 V +/- 5 percent.",
                        "power"),
            Requirement("R-005", "ObstacleAvoidance",
                        "The rover shall avoid obstacles larger than 0.3 m.",
                        "navigation"),
        ),
        satisfies=(
            Satisfy("R-001", "P-BAT"),
            Satisfy("R-002", "P-MOT"),
            Satisfy("R-003", "P-GPS"),
            Satisfy("R-004", "P-PDU"),
        ),
    )
