"""Contains sport extensions of :class:`Data`."""

from dataclasses import dataclass
from enum import Enum
from random import randint, random
from threading import Thread

from libantplus.data.data import Data


@dataclass
class HeartRateData(Data):
    """Heart rate data class."""

    heart_rate: int = 0xFF
    heart_rate_event_time = None
    heart_rate_event_count = None


@dataclass
class PowerData(Data):
    """Power data class."""

    power: float = 0
    power_event_count = None
    accumulated_power = None
    balance: int = 0


@dataclass
class SpeedData(Data):
    """Speed data class."""

    wheel_circumference = 2.070  # 2.096  # Note: SimulANT has 2.070 as default

    speed: float = 0  # km/h
    speed_event_time: None | int = None
    speed_revolution_count: None | int = None


@dataclass
class CadenceData(Data):
    """Cadence data class."""

    cadence: float = 0
    cadence_event_time: None | int = None
    cadence_revolution_count: None | int = None


@dataclass()
class CyclingData(HeartRateData, PowerData, SpeedData, CadenceData):
    """Cycling main data class."""

    def simulate(self, fixed_values=False):
        """Simulate values for testing."""

        def _simulate():
            if fixed_values:
                self.heart_rate = 100
                self.cadence = 90
                self.speed = 20.5
            else:
                while True:
                    self.heart_rate = randint(1, 255)
                    self.cadence = randint(60, 120)
                    self.speed = random() * 50
                    self.power = randint(0, 4000)

        thread = Thread(target=_simulate, daemon=True)
        thread.start()


@dataclass
class TrainerData(CyclingData):
    """Trainer main data class."""

    elapsed_time = None  # s
    distance = None  # m

    class TrainerTargetMode(Enum):
        """Trainer modes."""

        resistance = 0
        gradient = 1
        power = 2
        heart_rate = 3

    mode = TrainerTargetMode.resistance
    basic_supported = True
    power_supported = True
    simulation_supported = True

    target = 0.0  # watts or bpm or %
    resistance = 0.0  # %
    maximum_resistance = None

    rider_weight = 75  # kg
    bike_weight = 10  # kg

    wind_coefficient = 0.51  # kg/m
    wind_speed = 0.0  # km/h
    drafting_factor = 1
    rolling_resistance = 0.004
