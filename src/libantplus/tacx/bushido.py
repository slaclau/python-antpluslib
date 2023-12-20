"""Interfaces for communicating as and with Tacx Bushido trainers."""
from libantplus.data.sport import TrainerData
from libantplus.plus.interface import AntPlusInterface
from libantplus.plus.page import (
    TacxPage0,
    TacxPage172,
    TacxPage173,
    TacxPage220,
    TacxPage221,
    TacxInfoSubPage,
    TacxHUMode,
    BushidoPage1,
    BushidoSlavePage1,
    BushidoPage2,
    BushidoPage4,
    BushidoPage8,
    BushidoPage16,
    BushidoPage34,
    BushidoPage35,
)
from libantplus.message import Id, AntMessage


class Bushido(AntPlusInterface):  # noqa PLW223
    """Base class for Bushido classes."""

    channel_frequency = 60
    channel_period = 4096
    channel_search_timeout = 255
    network_key = None


class BushidoBrake(Bushido):
    """Interface for communicating as and with Tacx Bushido brakes."""

    device_type_id = 81

    interleave_reset = 32

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        if data_page_number == 1:
            if self.master:
                page_dict = BushidoSlavePage1.unpage_to_dict(info)
            else:
                page_dict = BushidoPage1.unpage_to_dict(info)
        elif data_page_number == 2:
            page_dict = BushidoPage2.unpage_to_dict(info)
        elif data_page_number == 4:
            page_dict = BushidoPage4.unpage_to_dict(info)
        elif data_page_number == 8:
            page_dict = BushidoPage8.unpage_to_dict(info)
        elif data_page_number == 8:
            page_dict = BushidoPage16.unpage_to_dict(info)
        elif data_page_number == 34:
            page_dict = BushidoPage34.unpage_to_dict(info)
        elif data_page_number == 35:
            page_dict = BushidoPage35.unpage_to_dict(info)
        self.logger.info("Received %s", page_dict)

    def _handle_acknowledged_data(self, data_page_number: int, info: bytes):
        self.logger.warning("Received unexpected acknowledged message.")
        self._handle_broadcast_data(data_page_number, info)

    def _broadcast_message(self, interleave: int):
        if interleave % 3 == 0:
            msg = self._broadcast_page(16)
        elif interleave % 3 == 1:
            msg = self._broadcast_page(1)

        elif interleave % 3 == 2:
            msg = self._broadcast_page(2)
        return msg

    def _broadcast_page(self, page_number: int, message_id=Id.BroadcastData):
        if page_number == 1:
            page = BushidoPage1.page_from_dict(
                channel=self.channel, data1=1000, data2=2000, data3=3000
            )
        elif page_number == 2:
            page = BushidoPage2.page_from_dict(
                channel=self.channel, speed=1000, cadence=100, balance=51
            )
        elif page_number == 16:
            page = BushidoPage16.page_from_dict(
                channel=self.channel, alarm=0, temperature=50
            )
        if page:
            self.logger.info("Broadcasting page %d", page_number)
        else:
            raise RuntimeError(f"Page {page_number} is not implemented")
        return AntMessage.compose(message_id, page)

    @staticmethod
    def get_page_from_number(page_number, master=True):
        """Return the subclass of AntPAge corresponding to the page number."""
        if page_number == 1:
            if master:
                return BushidoPage1
            return BushidoSlavePage1
        if page_number == 2:
            return BushidoPage2
        if page_number == 4:
            return BushidoPage4
        if page_number == 8:
            return BushidoPage8
        if page_number == 16:
            return BushidoPage16
        if page_number == 34:
            return BushidoPage34
        if page_number == 35:
            return BushidoPage35
        return BushidoHeadUnit.get_page_from_number(page_number, master)


class BushidoHeadUnit(Bushido):
    """Interface for communicating as and with Tacx Bushido head units."""

    device_type_id = 82

    mode: TacxHUMode | None = None

    interleave_reset = 32

    def _next_mode(self):
        if self.mode == TacxHUMode.standalone:
            return TacxHUMode.pc
        if self.mode == TacxHUMode.pc:
            return TacxHUMode.reset_distance
        if self.mode == TacxHUMode.reset_distance:
            return TacxHUMode.paused
        if self.mode == TacxHUMode.paused:
            return TacxHUMode.training
        return None

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        if not self.master:
            assert isinstance(self.data, TrainerData)
            if data_page_number == 173:
                page_dict = TacxPage173.unpage_to_dict(info)
                if page_dict["sub_page"] == TacxInfoSubPage.serial:
                    last_mode = self.mode
                    self.mode = page_dict["mode"]
                    if self.mode != last_mode:
                        self.logger.info("Switched to %s from %s", self.mode, last_mode)
                    if self._next_mode() is not None:
                        self.logger.info(
                            "Sending mode change command to %s", self._next_mode()
                        )
                        return AntMessage.compose(
                            Id.BroadcastData,
                            TacxPage172.page_from_dict(
                                channel=self.channel,
                                sub_page=TacxInfoSubPage.mode,
                                mode=self._next_mode(),
                            ),
                        )
                else:
                    self.logger.info("Received %s", page_dict)
            elif data_page_number == 221:
                page_dict = TacxPage221.unpage_to_dict(info)
                if page_dict["sub_page"] == 1:
                    with self.data.lock:
                        self.data.speed = page_dict["speed"] / 10.0
                        self.data.power = page_dict["power"]
                        self.data.cadence = page_dict["cadence"]
                        self.data.balance = page_dict["balance"]
                elif page_dict["sub_page"] == 2:
                    with self.data.lock:
                        self.data.heart_rate = page_dict["heart_rate"]
                self.logger.info("Received %s", page_dict)
            return self.broadcast_slave_message()

        raise NotImplementedError

    def _handle_rx_fail(self):
        return self.broadcast_slave_message()

    def _broadcast_message(self, interleave: int):
        raise RuntimeError("Bushido head unit is not intended to be used as a master.")

    def broadcast_slave_message(self):
        """Broadcast messages to master."""
        self.interleave += 1
        if self.interleave == self.interleave_reset:
            self.interleave = 0
            return self._broadcast_page(0)
        if self.interleave == 1:
            self.logger.info("Requesting version information")
            return AntMessage.compose(
                Id.BroadcastData,
                TacxPage172.page_from_dict(
                    channel=self.channel,
                    sub_page=TacxInfoSubPage.version,
                ),
            )
        if self.interleave == 2:
            self.logger.info("Requesting brake version information")
            return AntMessage.compose(
                Id.BroadcastData,
                TacxPage172.page_from_dict(
                    channel=self.channel,
                    sub_page=TacxInfoSubPage.brake_version,
                ),
            )
        if self.interleave == 3:
            self.logger.info("Requesting brake serial information")
            return AntMessage.compose(
                Id.BroadcastData,
                TacxPage172.page_from_dict(
                    channel=self.channel,
                    sub_page=TacxInfoSubPage.brake_serial,
                ),
            )
        return self._broadcast_page(220)

    def _handle_acknowledged_data(self, data_page_number, info):
        self.logger.warning("Received unexpected acknowledged message.")
        self._handle_broadcast_data(data_page_number, info)

    def _broadcast_page(self, page_number: int, message_id=Id.BroadcastData):
        assert isinstance(self.data, TrainerData)
        if page_number == 0:
            self.logger.info("Broadcasting keep alive message")
            page = TacxPage0.page(self.channel)
        elif page_number == 220:
            if self.interleave % 2 == 0:
                self.logger.info("Broadcasting page 220_01")
                with self.data.lock:
                    page = TacxPage220.page_from_dict(
                        channel=self.channel,
                        sub_page=1,
                        mode=self.data.mode.value,
                        target=round(self.data.target),
                        weight=self.data.rider_weight + self.data.bike_weight,
                        reset=False,
                    )
            else:
                self.logger.info("Broadcasting page 220_02")
                with self.data.lock:
                    page = TacxPage220.page_from_dict(
                        channel=self.channel,
                        sub_page=2,
                        wind_coefficient=round(self.data.wind_coefficient * 1000),
                        wind_speed=round(self.data.wind_speed / 3.6),
                        rolling_resistance=0,
                    )
        if page is not None:
            return AntMessage.compose(message_id, page)
        return None

    @staticmethod
    def get_page_from_number(page_number, master=True):
        """Return the subclass of AntPAge corresponding to the page number."""
        if page_number == 0:
            return TacxPage0
        if page_number == 172:
            return TacxPage172
        if page_number == 173:
            return TacxPage173
        if page_number == 220:
            return TacxPage220
        if page_number == 221:
            return TacxPage221
        return None
