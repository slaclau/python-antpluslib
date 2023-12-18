"""Contains sport extensions of :class:`Data`."""

from dataclasses import dataclass
from random import randint, random
from threading import Thread

from fortius_ant.ant.data.data import Data


@dataclass
class HeartRateData(Data):
    """Heart rate data class."""

    heart_rate: int = 0xFF
    heart_rate_event_time = None
    heart_rate_event_count = None


@dataclass
class PowerData(Data):
    """Power data class."""


@dataclass
class SpeedData(Data):
    """Speed data class."""

    speed: float = 0
    speed_event_time: None | int = None
    speed_revolution_count: None | int = None


@dataclass
class CadenceData(Data):
    """Cadence data class."""

    cadence: float = 0
    cadence_event_time: None | int = None
    cadence_revolution_count: None | int = None


@dataclass()
class SportData(HeartRateData, PowerData, SpeedData, CadenceData):
    """Sport main data class."""

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

        thread = Thread(target=_simulate, daemon=True)
        thread.start()
