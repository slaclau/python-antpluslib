"""Provide an inheritable class for implementing an ANT device."""

__version__ = "2023-04-16"
# 2023-04-16    Rewritten in class based fashion

from enum import Enum
import logging
import time

from libantplus.dongle import (
    ChannelType,
    TransmissionType,
    UnknownMessageID,
)
from libantplus.message import (
    AntMessage,
    Id,
    ChannelResponseMessage,
    RequestMessage,
    SetChannelIdMessage,
)
from libantplus.data.data import Data

default_network_key = 0xC1677A553B21E4E8
power_0db = 0x03


parent_logger = logging.getLogger(__name__)


class AntInterface:
    """Interface for communicating as an ANT device."""

    class Status(Enum):
        UNASSIGNED = 0
        ASSIGNED = 1
        OPEN = 2
        CLOSING = 3
        CLOSED = 4

    manufacturer: int
    serial_number: int
    hw_version: int
    sw_version: int
    model_number: int

    channel: int
    device_type_id = 0
    device_number: int

    master: bool
    paired = False

    network_key: int | None = None
    transmit_power = power_0db

    channel_period = int(32768 / 4)
    channel_frequency = 66
    channel_search_timeout = 24

    master_channel_type = ChannelType.BidirectionalTransmit
    slave_channel_type = ChannelType.BidirectionalReceive
    channel_type = None

    master_transmission_type = TransmissionType.INDEPENDENT
    slave_transmission_type = TransmissionType.PAIRING
    transmission_type = None

    data: Data | None = None

    status = Status.UNASSIGNED
    action = None

    def __init__(self, master=True, device_number=0):
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.master = master
        self.device_number = device_number

        if self.master:
            self.channel_type = self.master_channel_type
            self.transmission_type = self.master_transmission_type
        else:
            self.channel_type = self.slave_channel_type
            self.transmission_type = self.slave_transmission_type

    def broadcast_message(self):
        """Broadcast ANT message."""
        raise NotImplementedError

    def handle_received_message(self, message, message_dict):
        """Handle ANT message."""
        if message_dict["channel"] != self.channel:
            raise WrongChannel
        return self._handle_received_message(message, message_dict)

    def _handle_received_message(self, message, message_dict):
        message_id = message_dict["id"]
        info = message_dict["info"]
        data_page_number = message_dict["page_number"]
        self.logger.debug("Received %s", message_dict)
        message_class = AntMessage.type_from_id(message_id)
        if message_class is not None:
            self.logger.debug("Decoded to %s", message_class.to_dict(message))
        if message_id == Id.ChannelID:
            return self._handle_channel_id_message(message)
        if message_id == Id.ChannelResponse:
            return self._handle_channel_response_message(message)
        if message_id == Id.BroadcastData:
            if not self.paired:
                return self._request_channel_id()
            return self._handle_broadcast_data(data_page_number, info)
        if message_id == Id.AcknowledgedData:
            if not self.paired:
                return self._request_channel_id()
            return self._handle_acknowledged_data(data_page_number, info)
        if message_id == Id.BurstData:
            return self._handle_burst_data(info)
        raise UnknownMessageID

    def _handle_channel_id_message(self, message: bytes):
        message_dict = SetChannelIdMessage.to_dict(message)
        self.logger.info("Received channel id: %s", message_dict)
        if message_dict["channel"] == self.channel:
            self.paired = True
            self.device_number = message_dict["device_number"]
            self.device_type_id = message_dict["device_type_id"]
            self.transmission_type = message_dict["transmission_type"]

    def _handle_channel_response_message(self, message: bytes):
        message_dict = ChannelResponseMessage.to_dict(message)
        code = message_dict["code"]
        if code == ChannelResponseMessage.Code.EVENT_TX and self.master:
            return self.broadcast_message()
        if code == ChannelResponseMessage.Code.EVENT_CHANNEL_CLOSED:
            old_status = self.status
            self.status = self.Status.CLOSED
            if self.status != old_status:
                self.logger.info(
                    "Status changed from %s to %s", old_status, self.status
                )
        elif code == ChannelResponseMessage.Code.RESPONSE_NO_ERROR:
            message_id = message_dict["id"]
            old_status = self.status
            if message_id == Id.AssignChannel:
                self.status = self.Status.ASSIGNED
            elif message_id == Id.OpenChannel:
                self.status = self.Status.OPEN
            elif message_id == Id.CloseChannel:
                self.status = self.Status.CLOSING
            elif message_id == Id.UnassignChannel:
                self.status = self.Status.UNASSIGNED
            self.action = message_id
            self.logger.info("RESPONSE_NO_ERROR to %s", self.action)
            if self.status != old_status:
                self.logger.info(
                    "Status changed from %s to %s", old_status, self.status
                )
        elif code in [
            ChannelResponseMessage.Code.EVENT_RX_FAIL,
            ChannelResponseMessage.Code.EVENT_RX_FAIL_GO_TO_SEARCH,
            ChannelResponseMessage.Code.EVENT_RX_SEARCH_TIMEOUT,
        ]:
            self.logger.warning("Received %s", code)
            if code == ChannelResponseMessage.Code.EVENT_RX_FAIL:
                return self._handle_rx_fail()
        else:
            self.logger.debug("Received %s", code)
        return None

    def _handle_rx_fail(self):
        pass

    def _handle_burst_data(self, info: bytes):
        self.logger.info("Ignoring burst message")

    def _request_channel_id(self):
        return RequestMessage(channel=self.channel, id=Id.ChannelID)

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        raise NotImplementedError

    def _handle_acknowledged_data(self, data_page_number: int, info: bytes):
        raise NotImplementedError

    def wait_for_status(self, status, timeout=10):
        """Return true when `self.status` equals `status`."""
        start = time.time()
        while time.time() - start < timeout:
            if self.status == status:
                return True
        return False

    def wait_for_action(self, action, timeout=10):
        """Return true when `self.action` equals `action`."""
        start = time.time()
        while time.time() - start < timeout:
            if self.action == action:
                return True
        return False

    @staticmethod
    def get_page_from_number(page_number, master=True):
        """Return the subclass of AntPAge corresponding to the page number."""
        raise NotImplementedError


class WrongChannel(Exception):
    """Raise when attempting to handle messages on the wrong channel."""


class UnknownDataPage(Exception):
    """Raise when attempting to handle an unknown data page."""

    def __init__(self, info: bytes = b"", page_number: int = -1):
        self.info = info
        self.page_number = page_number
        self.message = f"Page {page_number} is not known"


class UnsupportedPage(Exception):
    """Raise when an unsupported page is requested."""

    def __init__(self, info: bytes = b"", page_number: int = -1):
        self.info = info
        self.page_number = page_number
        self.message = f"Page {page_number} is not supported"
