"""Interface for communicating as and with ANT+ HRMs."""
import time

from libantplus.plus.interface import AntPlusInterface
from libantplus.message import Id, AntMessage, Manufacturer_garmin
from libantplus.plus.page import HRMPage
from libantplus.data import sport
from libantplus.interface import UnsupportedPage

ModelNumber_HRM = 0x33  # char  antifier-value
SerialNumber_HRM = 5975  # short 1959-7-5
HWrevision_HRM = 1  # char
SWversion_HRM = 1  # char

channel_HRM = 1  # ANT+ channel for Heart Rate Monitor
DeviceTypeID_heart_rate = 120


class AntHRM(AntPlusInterface):
    """Interface for communicating as and with ANT+ HRMs."""

    interleave_reset = 204
    device_type_id = DeviceTypeID_heart_rate
    channel_period = 8070

    features_supported = 0x00
    features_enabled = 0x00

    def __init__(self, master=True, device_number=0):
        super().__init__(master, device_number)
        self.interleave = None
        self.heart_beat_counter = None
        self.heart_beat_event_time = None
        self.heart_beat_time = None
        self.page_change_toggle = None
        self.initialize()

    def initialize(self):
        """Initialize variables to zero."""
        super().initialize()
        self.interleave = 0
        self.heart_beat_counter = 0
        self.heart_beat_event_time = 0
        self.heart_beat_time = 0
        self.page_change_toggle = 0

    def _broadcast_message(self, interleave: int):
        if self.interleave in [
            0,
            1,
            2,
            3,
        ]:  # Transmit 4 times Page 2 = Manufacturer info
            return self._broadcast_page(2)
        if self.interleave in [
            68,
            69,
            70,
            71,
        ]:  # Transmit 4 times Page 3 = Product information
            return self._broadcast_page(3)
        if self.interleave in [
            136,
            137,
            138,
            139,
        ]:  # Transmit 4 times Page 6 = Capabilities
            return self._broadcast_page(6)

        # Transmit 64 times Page 0 = Main data page
        return self._broadcast_page(0)

    def _broadcast_page(self, page_number: int, message_id=Id.BroadcastData):
        assert isinstance(self.data, sport.HeartRateData)
        with self.data.lock:
            heart_rate = self.data.heart_rate
            event_time = self.data.heart_rate_event_time
            event_count = self.data.heart_rate_event_count

        if event_time is not None and event_count is not None:
            self.heart_beat_event_time = event_time
            self.heart_beat_counter = event_count

        elif (time.time() - self.heart_beat_time) >= (60 / float(heart_rate)):
            self.heart_beat_counter += 1  # Increment heart beat count
            self.heart_beat_event_time += 60 / float(
                heart_rate
            )  # Reset last time of heart beat
            self.heart_beat_time = time.time()  # Current time for next processing

            if self.heart_beat_event_time >= 64:
                self.heart_beat_event_time = 0
            if self.heart_beat_counter >= 256:
                self.heart_beat_counter = 0

        if self.interleave % 4 == 0:
            self.page_change_toggle ^= 0x80  # toggle bit every 4 counts
        if page_number == 2:
            DataPageNumber = 2
            Spec1 = Manufacturer_garmin
            Spec2 = SerialNumber_HRM & 0x00FF  # Serial Number LSB
            Spec3 = (
                SerialNumber_HRM & 0xFF00
            ) >> 8  # Serial Number MSB     # 1959-07-05
            # comment       = "(HR data p2)"

        elif page_number == 3:
            DataPageNumber = 3
            Spec1 = HWrevision_HRM
            Spec2 = SWversion_HRM
            Spec3 = ModelNumber_HRM
            # comment       = "(HR data p3)"
        elif page_number == 6:
            DataPageNumber = 6
            Spec1 = 0xFF  # Reserved
            Spec2 = self.features_supported
            Spec3 = self.features_enabled
            # comment       = "(HR data p6)"
        elif page_number == 0:
            DataPageNumber = 0
            Spec1 = 0xFF  # Reserved
            Spec2 = 0xFF  # Reserved
            Spec3 = 0xFF  # Reserved
            # comment       = "(HR data p0)"
        else:
            raise UnsupportedPage

        page = HRMPage.page(
            self.page_change_toggle | DataPageNumber,
            self.channel,
            Spec1,
            Spec2,
            Spec3,
            int(1024 * self.heart_beat_event_time),
            self.heart_beat_counter,
            int(heart_rate),
        )
        self.logger.info(
            "Broadcasting page %d with heart rate %d", page_number, heart_rate
        )
        return AntMessage.compose(message_id, page)

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        data_page_number = data_page_number & 0x7F
        assert isinstance(self.data, sport.HeartRateData)
        self.data: sport.HeartRateData
        with self.data.lock:
            self.data.heart_rate = HRMPage.unpage(info)[-1]
        self.logger.info("Received heart rate %d", self.data.heart_rate)
        if data_page_number == 0:
            pass
        elif data_page_number == 2:
            self.manufacturer = HRMPage.unpage(info)[1]
            self.serial_number = (
                HRMPage.unpage(info)[2] * 0xFF + HRMPage.unpage(info)[3]
            )
        elif data_page_number == 3:
            self.hw_version = HRMPage.unpage(info)[1]
            self.sw_version = HRMPage.unpage(info)[2]
            self.model_number = HRMPage.unpage(info)[3]
        elif data_page_number == 6:
            self.features_supported = HRMPage.unpage(info)[2]
            self.features_enabled = HRMPage.unpage(info)[3]
        else:
            self.logger.info("Ignoring data page %d", data_page_number)

    def _handle_acknowledged_data(self, data_page_number, info):
        self.logger.warning("Received unexpected acknowledged message.")
        self._handle_broadcast_data(data_page_number, info)
