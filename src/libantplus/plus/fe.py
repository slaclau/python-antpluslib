"""Interface for communicating as and with ANT+ fitness equipment."""
import time

from libantplus.plus.interface import AntPlusInterface
from libantplus.message import Id, AntMessage, Manufacturer_tacx
from libantplus.plus.page import (
    FEPage16,
    FEPage17,
    FEPage25,
    FEPage48,
    FEPage54,
    Page80,
    Page81,
)
from libantplus.data import sport
from libantplus.interface import UnsupportedPage
from libantplus.dongle import TransmissionType
from libantplus.data.sport import TrainerData

ModelNumber_FE = 2875  # short antifier-value=0x8385, Tacx Neo=2875
SerialNumber_FE = 19590705  # int   1959-7-5
HWrevision_FE = 1  # char
SWrevisionMain_FE = 1  # char
SWrevisionSupp_FE = 1  # char

DeviceTypeID_fitness_equipment = 17


class AntFE(AntPlusInterface):
    """Interface for communicating as and with ANT+ HRMs."""

    interleave_reset = 132
    device_type_id = DeviceTypeID_fitness_equipment

    master_transmission_type = (
        TransmissionType.INDEPENDENT + TransmissionType.GLOBAL_PAGES
    )

    def __init__(self, master=True, device_number=0):
        super().__init__(master=master, device_number=device_number)
        self.interleave = None
        self.event_count = None
        self.accumulated_power = None
        self.accumulated_time = None
        self.distance_travelled = None
        self.accumulated_last_time = None
        self.initialize()

    def initialize(self):
        """Initialize values to zero."""
        super().initialize()
        self.interleave = 0
        self.event_count = 0
        self.accumulated_power = 0
        self.accumulated_time = 0
        self.distance_travelled = 0
        self.accumulated_last_time = time.time()

    def _broadcast_message(self, interleave: int):
        if self.interleave in [64, 65]:
            return self._broadcast_page(80)
        if self.interleave in [130, 131]:
            return self._broadcast_page(81)
        if self.interleave < 64 and (self.interleave % 4) in (2, 3):
            return self._broadcast_page(25)
        if self.interleave > 65 and (self.interleave % 4) in (0, 1):
            return self._broadcast_page(25)
        return self._broadcast_page(16)

    def _broadcast_page(self, page_number: int, message_id=Id.BroadcastData):
        assert isinstance(self.data, sport.TrainerData)
        with self.data.lock:
            elapsed_time = self.data.elapsed_time
            distance = self.data.distance
            speed = self.data.speed
            wheel_circumference = self.data.wheel_circumference
            heart_rate = self.data.heart_rate
            power = self.data.power
            accumulated_power = self.data.accumulated_power
            power_event_count = self.data.power_event_count
            cadence = self.data.cadence
            resistance = self.data.resistance
            maximum_resistance = self.data.maximum_resistance
            basic_supported = self.data.basic_supported
            power_supported = self.data.power_supported
            simulation_supported = self.data.simulation_supported

        if accumulated_power is None or power_event_count is None:
            accumulated_power = self.accumulated_power + power
            power_event_count = self.event_count + 1

        t = time.time()
        if elapsed_time is None:
            elapsed_time = self.accumulated_time + (t - self.accumulated_last_time)
        self.accumulated_last_time = t

        if distance is None:
            distance = self.distance_travelled + (speed / 3.6) * (
                elapsed_time - self.accumulated_time
            )

        if maximum_resistance is None:
            maximum_resistance = 0xFFFF

        power = round(power)

        accumulated_power = 0xFFFF & accumulated_power
        power_event_count = 0xFF & power_event_count

        if page_number == 16:
            page = FEPage16.page_from_dict(
                channel=self.channel,
                elapsed_time=round(elapsed_time * 4) & 0xFF,
                distance=round(distance) & 0xFF,
                speed=round(speed / 3.6 * 1000),
                heart_rate=heart_rate,
                distance_enabled=True,
            )
        elif page_number == 17:
            page = FEPage17.page_from_dict(
                channel=self.channel,
                cycle_length=round(wheel_circumference * 100),
                resistance=round(resistance * 2),
            )
        elif page_number == 25:
            page = FEPage25.page_from_dict(
                channel=self.channel,
                event_count=power_event_count,
                cadence=cadence,
                accumulated_power=accumulated_power,
                power=power,
            )
        elif page_number == 54:
            page = FEPage54.page_from_dict(
                channel=self.channel,
                maximum_resistance=maximum_resistance,
                basic=basic_supported,
                power=power_supported,
                simulation=simulation_supported,
            )
        elif page_number == 80:
            page = Page80.page_from_dict(
                channel=self.channel,
                hw_revision=HWrevision_FE,
                manufacturer=Manufacturer_tacx,
                model_number=ModelNumber_FE,
            )
        elif page_number == 81:
            page = Page81.page_from_dict(
                channel=self.channel,
                sw_revision_supplemental=SWrevisionSupp_FE,
                sw_revision=SWrevisionMain_FE,
                serial_number=SerialNumber_FE,
            )
        else:
            raise UnsupportedPage(page_number=page_number)

        self.accumulated_power = accumulated_power
        self.event_count = power_event_count
        self.accumulated_time = elapsed_time
        self.distance_travelled = distance
        self.logger.info("Broadcasting page %d: %s", page_number, page)
        return AntMessage.compose(message_id, page)

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        self.logger.warning("Received unknown page %d", data_page_number)

    def _handle_acknowledged_data(self, data_page_number, info):
        assert isinstance(self.data, TrainerData)
        with self.data.lock:
            if data_page_number == 48 and self.data.basic_supported:
                self.data.mode = self.data.TrainerTargetMode.resistance
                self.data.target = FEPage48.unpage_to_dict(info)["resistance"] / 2
                self.logger.info(
                    "Switching to resistance mode with resistance %0.1f %",
                    self.data.target,
                )
            else:
                self.logger.warning(
                    "Received unknown acknowledged page %d", data_page_number
                )
