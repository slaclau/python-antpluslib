"""Provide interface for communicating as and with ANT+ speed and cadence sensors."""

import time

from libantplus.plus.interface import AntPlusInterface
from libantplus.message import Id, AntMessage
from libantplus.plus.page import SCSPage
from libantplus.data import sport

DeviceTypeID_bike_speed_cadence = 121


class AntSCS(AntPlusInterface):
    """Interface for communicating as a speed and cadence sensor."""

    interleave_reset = 0
    device_type_id = DeviceTypeID_bike_speed_cadence
    channel_period = 8086

    def __init__(self, master=True, device_number=0):
        super().__init__(master)
        self.pedal_echo_previous_count = None  # There is no previous
        self.cadence_event_time = None  # Initiate the even variables
        self.cadence_event_count = None
        self.last_cadence_event_time = None

        self.speed_previous_count = None
        self.speed_event_time = None
        self.speed_event_count = None
        self.last_speed_event_time = None

        self.circumference = 2.070  # 2.096  # Note: SimulANT has 2.070 as default

        self.previous_received_values = None

        self.initialize()

    def initialize(self):
        """Initialize values to zero."""
        self.pedal_echo_previous_count = 0  # There is no previous
        self.cadence_event_time = 0  # Initiate the even variables
        self.cadence_event_count = 0
        self.last_cadence_event_time = time.time()

        self.speed_previous_count = 0
        self.speed_event_time = 0
        self.speed_event_count = 0
        self.last_speed_event_time = time.time()

        self.previous_received_values = None

    def _broadcast_message(self, interleave: int):
        return self._broadcast_page(0)

    def _broadcast_page(self, page_number: int, message_id=Id.BroadcastData):
        assert isinstance(self.data_source, sport.SpeedData)
        assert isinstance(self.data_source, sport.CadenceData)
        with self.data_source.lock:
            SpeedKmh = self.data_source.speed
            SpeedEchoTime = self.data_source.speed_event_time
            SpeedEchoCount = self.data_source.speed_revolution_count

            Cadence = self.data_source.cadence
            PedalEchoTime = self.data_source.cadence_event_time
            PedalEchoCount = self.data_source.cadence_revolution_count

        if PedalEchoTime is not None and PedalEchoCount is not None:
            self.cadence_event_time = PedalEchoTime
            self.cadence_event_count = PedalEchoCount
        elif (Cadence > 0) and (
            (time.time() - self.last_cadence_event_time) >= (60 / float(Cadence))
        ):
            self.cadence_event_count += 1
            self.cadence_event_time += (60 / float(Cadence)) * 1024
        if SpeedEchoTime is not None and SpeedEchoCount is not None:
            self.speed_event_time = SpeedEchoTime
            self.speed_event_count = SpeedEchoCount
        else:
            if (
                PedalEchoTime is None
                or PedalEchoCount is None
                and (
                    (SpeedKmh > 0)
                    and (
                        (time.time() - self.last_speed_event_time)
                        >= 1 / float(SpeedKmh / 3.6 / self.circumference)
                    )
                )
            ):
                self.speed_event_count += int(
                    (time.time() - self.last_speed_event_time)
                    / (1 / float(SpeedKmh / 3.6 / self.circumference))
                )
                self.speed_event_time += (
                    1 / float(SpeedKmh / 3.6 / self.circumference)
                ) * 1024
            elif (
                self.cadence_event_count != self.pedal_echo_previous_count
                and Cadence > 0
                and SpeedKmh > 0
            ):
                # ---------------------------------------------------------------------
                # Cadence variables
                # Based upon the number of pedal-cycles that are done and the given
                # cadence, calculate the elapsed time.
                # PedalEchoTime is not used, because that give rounding errors and
                # an instable reading.
                # ---------------------------------------------------------------------
                PedalCycles = self.cadence_event_count - self.pedal_echo_previous_count
                ElapsedTime = (
                    PedalCycles / Cadence * 60
                )  # count / count/min * seconds/min = seconds
                self.cadence_event_time += ElapsedTime * 1024  # 1/1024 seconds
                self.cadence_event_count += PedalCycles

                # ---------------------------------------------------------------------
                # Speed variables
                # First calculate how many wheel-cycles can be done
                # Then (based upon rounded #of cycles) calculate the elapsed time
                # ---------------------------------------------------------------------
                WheelCadence = (
                    SpeedKmh / 3.6 / self.circumference
                )  # km/hr / kseconds/hr / meters  = cycles/s
                WheelCycles = round(
                    ElapsedTime * WheelCadence, 0
                )  # seconds * /s                  = cycles

                ElapsedTime = WheelCycles / SpeedKmh * 3.6 * self.circumference
                self.speed_event_time += ElapsedTime * 1024
                self.speed_event_count += WheelCycles

        # -------------------------------------------------------------------------
        # Rollover after 0xffff
        # -------------------------------------------------------------------------
        self.cadence_event_time = (
            int(self.cadence_event_time) & 0xFFFF
        )  # roll-over at 65535 = 64 seconds
        self.cadence_event_count = (
            int(self.cadence_event_count) & 0xFFFF
        )  # roll-over at 65535
        self.speed_event_time = (
            int(self.speed_event_time) & 0xFFFF
        )  # roll-over at 65535 = 64 seconds
        self.speed_event_count = (
            int(self.speed_event_count) & 0xFFFF
        )  # roll-over at 65535

        # -------------------------------------------------------------------------
        # Prepare for next event
        # -------------------------------------------------------------------------
        if self.cadence_event_count != self.pedal_echo_previous_count:
            self.pedal_echo_previous_count = self.cadence_event_count
            self.last_cadence_event_time = time.time()

        if self.speed_event_count != self.speed_previous_count:
            self.speed_previous_count = self.speed_event_count
            self.last_speed_event_time = time.time()

        # -------------------------------------------------------------------------
        # Compose message
        # -------------------------------------------------------------------------
        page = SCSPage.page(
            self.channel,
            self.cadence_event_time,
            self.cadence_event_count,
            self.speed_event_time,
            self.speed_event_count,
        )
        self.logger.info(
            "Broadcasting speed (%0.2f km/h) and cadence (%d) page: %d, %d, %d, %d",
            SpeedKmh,
            Cadence,
            self.cadence_event_time,
            self.cadence_event_count,
            self.speed_event_time,
            self.speed_event_count,
        )
        return AntMessage.compose(message_id, page)

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        assert isinstance(self.data_target, sport.CadenceData)
        assert isinstance(self.data_target, sport.SpeedData)

        values = list(SCSPage.unpage(info)[1:])
        with self.data_target.lock:
            previous_values = [
                self.data_target.cadence_event_time,
                self.data_target.cadence_revolution_count,
                self.data_target.speed_event_time,
                self.data_target.speed_revolution_count,
            ]
            for i in range(0, len(previous_values)):
                if previous_values[i] is None:
                    previous_values[i] = 0
                if previous_values[i] > values[i]:
                    values[i] += 0xFFFF
            if values[0] > previous_values[0]:
                self.data_target.cadence = (
                    (values[1] - previous_values[1])
                    / (values[0] - previous_values[0])
                    * 60
                    * 1024
                )
            self.data_target.cadence_event_time = values[0]
            self.data_target.cadence_revolution_count = values[1]
            if values[2] > previous_values[2]:
                self.data_target.speed = (
                    (values[3] - previous_values[3])
                    / (values[2] - previous_values[2])
                    * self.circumference
                    * 1024
                    * 3.6
                )
            self.data_target.speed_event_time = values[2]
            self.data_target.speed_revolution_count = values[3]
        self.logger.info(
            "Received speed %0.2f km/h and cadence %d",
            self.data_target.speed,
            self.data_target.cadence,
        )

    def _handle_acknowledged_data(self, data_page_number, info):
        self.logger.warning("Received unexpected acknowledged message.")
        self._handle_broadcast_data(data_page_number, info)
