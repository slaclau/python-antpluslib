"""Interface with usb dongle."""
from collections import deque
from enum import Enum, IntEnum
import os
import threading
import time
import queue
import logging

import usb.core
from usb.core import NoBackendError, USBError


from libantplus import debug, logfile
from libantplus.message import (
    ResetSystemMessage,
    RequestMessage,
    SetChannelFrequencyMessage,
    SetChannelPeriodMessage,
    SetChannelIdMessage,
    AssignChannelMessage,
    UnassignChannelMessage,
    ChannelResponseMessage,
    StartupMessage,
    CapabilitiesMessage,
    VersionMessage,
    WrongMessageId,
    InvalidMessageError,
    Id,
    SetChannelTransmitPowerMessage,
    SetChannelSearchTimeoutMessage,
    OpenChannelMessage,
    CloseChannelMessage,
    SYNC,
    AntMessage,
    SetNetworkKeyMessage,
)

power_0db = 0x03


logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

parent_logger = logging.getLogger(__name__)

formatter = logging.Formatter(
    "%(asctime)s.%(msecs)03d-%(name)s-%(levelname)s-%(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
)
handler.setFormatter(formatter)


class ChannelType(Enum):
    """Types of ant channel."""

    BidirectionalReceive = 0x00  # Slave
    BidirectionalTransmit = 0x10  # Master

    UnidirectionalReceiveOnly = 0x40  # Slave
    UnidirectionalTransmitOnly = 0x50  # Master

    SharedBidirectionalReceive = 0x20  # Slave
    SharedBidirectionalTransmit = 0x30  # Master


class TransmissionType(IntEnum):
    """Channel transmission type enum."""

    PAIRING = 0
    INDEPENDENT = 1
    SHARED1 = 2
    SHARED2 = 3

    GLOBAL_PAGES = 4


class Dongle:
    """Encapsulate dongle functionality."""

    device = None

    max_channels = None
    max_networks = None
    ant_version = None
    last_reset_type = None
    channels = None
    networks = None

    messages_deque: deque = deque()

    def __init__(self, device_id: int | None = None):
        """Create a dongle class with the required device id."""
        self.device_id = device_id
        self.messages: queue.Queue = queue.Queue()
        self.cycplus = False

        self.read_thread: threading.Thread | None = None
        self.read_thread_active = False

        self.handler_thread: threading.Thread | None = None
        self.handler_thread_active = False

        self.logger = parent_logger.getChild(self.__class__.__name__)
        self.read_logger = self.logger.getChild("read")
        self.handler_logger = self.logger.getChild("handler")

        self.network_flag = False

    def startup(self):
        """Call to configure dongle and properties on startup."""
        assert self._get_dongle()
        self.calibrate()

    def _get_network_number(self, network_key, timeout=10):
        if network_key is None:
            return 0
        if self.networks is None:
            self.networks = [None] * self.max_networks
        if network_key in self.networks:
            network = self.networks.index(network_key)
        else:
            try:
                network = self.networks.index(None, 1)
            except ValueError:
                raise NoMoreNetworks from None
            self._write(SetNetworkKeyMessage())
            start = time.time()
            while time.time() - start < timeout:
                if self.network_flag:
                    break
            if not self.network_flag:
                raise ValueError
            self.networks[network] = network_key
            self.network_flag = False
        return network

    def _clear_network(self, network_number):
        self.networks[network_number] = None

    def configure_channel(self, interface):
        """Send channel configuration messages to the dongle."""
        channel_number = self._get_next_channel()
        self.channels[channel_number] = interface
        interface.channel = channel_number
        network = self._get_network_number(interface.network_key)
        self._write(
            AssignChannelMessage(
                channel=channel_number,
                type=interface.channel_type,
                network=network,
            )
        )
        interface.wait_for_status(interface.Status.ASSIGNED)

        self._write(
            SetChannelIdMessage(
                channel=channel_number,
                type=interface.transmission_type,
                device_number=interface.device_number,
                device_type_id=interface.device_type_id,
            )
        )
        interface.wait_for_action(Id.ChannelID)

        if interface.channel_frequency != 66:
            self._write(
                SetChannelFrequencyMessage(
                    channel=channel_number,
                    frequency=interface.channel_frequency,
                )
            )
            interface.wait_for_action(Id.ChannelRfFrequency)

        if interface.channel_period != 8192:
            self._write(
                SetChannelPeriodMessage(
                    channel=channel_number, period=interface.channel_period
                )
            )
            interface.wait_for_action(Id.ChannelPeriod)

        if interface.transmit_power != power_0db:
            self._write(
                SetChannelTransmitPowerMessage(
                    channel=channel_number, power=interface.transmit_power
                )
            )
            interface.wait_for_action(Id.ChannelTransmitPower)

        if not interface.master:
            self._write(
                SetChannelSearchTimeoutMessage(
                    channel=channel_number, timeout=interface.channel_search_timeout
                )
            )
            interface.wait_for_action(Id.ChannelSearchTimeout)

        self._write(OpenChannelMessage(channel=channel_number))
        interface.wait_for_status(interface.Status.OPEN)

    def close_and_unassign_channel(self, channel_number):
        """Close and unassign channel."""
        interface = self.channels[channel_number]
        assert interface is not None
        self._write(CloseChannelMessage(channel=channel_number))
        assert interface.wait_for_status(interface.Status.CLOSED)
        self._write(UnassignChannelMessage(channel=channel_number))
        assert interface.wait_for_status(interface.Status.UNASSIGNED)
        self.channels[channel_number] = None

    def _wait_for_response(self, channel, message_id, code):
        if self.read_thread_active:
            response = self.read_message_from_deque()
        else:
            response = self._read()
        response_dict = ChannelResponseMessage.to_dict(response)
        assert response_dict["channel"] == channel
        assert response_dict["id"] == message_id
        assert response_dict["code"] == code

    def _wait_for_response_no_error(self, channel, message_id):
        return self._wait_for_response(
            channel, message_id, ChannelResponseMessage.Code.RESPONSE_NO_ERROR
        )

    def _get_next_channel(self):
        if self.channels is None:
            self.channels = [None] * self.max_channels
        channel = next(
            (i for i in range(0, self.max_channels) if self.channels[i] is None), -1
        )
        if channel == -1:
            raise NoMoreChannels
        return channel

    def _get_dongle(self) -> bool:
        raise NotImplementedError

    def reset(self, device=None):
        """Send reset command to dongle."""
        if device is None:
            device = self.device

            self.max_channels = None
            self.max_networks = None
            self.ant_version = None
            self.last_reset_type = None
            self.channels = None
            self.networks = None
        if device is not None:
            if self.handler_thread_active:
                self.stop_handler_thread()
            if self.read_thread_active:
                self.stop_read_thread()
            self._flush()
            device.write(0x01, ResetSystemMessage.create())
            self.logger.debug("Reset command sent to dongle.")

            time.sleep(0.500)
            if debug.on(debug.Function):
                logfile.Write("GetDongle - Read answer")
            if debug.on(debug.Function):
                logfile.Write("GetDongle - Check for an ANT+ reply")
            try:
                message = device.read(0x81, 5)
                message_dict = StartupMessage.to_dict(message)
                self.last_reset_type = message_dict["type"]
                self.logger.info(
                    "Dongle reset successfully by %s", self.last_reset_type
                )
                return True

            except usb.core.USBError as e:
                if debug.on(debug.Data1 | debug.Function):
                    logfile.Write(f"GetDongle - Exception: {e}")
            except WrongMessageId:
                pass
        self.logger.error("Dongle failed to reset.")
        return False

    def reset_if_allowed(self):
        """Send reset command if not a CYCPLUS dongle."""
        if not self.cycplus:
            self.reset()

    def release(self):
        """Release dongle."""
        raise NotImplementedError

    def calibrate(self):
        """Send dongle configuration commands.

        First send a request for the dongle's capabilities.
        """
        self._write(RequestMessage.create(id=Id.Capabilities))
        response = self._read()
        response_dict = CapabilitiesMessage.to_dict(response)
        self.max_channels = response_dict["max_channels"]
        self.max_networks = response_dict["max_networks"]

        self._write(RequestMessage.create(id=Id.ANTversion))
        response = self._read()
        response_dict = VersionMessage.to_dict(response)
        self.ant_version = response_dict["version"]

    def _write(self, message):
        raise NotImplementedError

    def _read(self):
        raise NotImplementedError

    def _flush(self):
        try:
            while True:
                self._read()
        except USBError:
            pass

    def write_then_read(self, message):
        """Write then immediately read."""
        self._write(message)
        return self._read()

    def start_read_thread(self):
        """Start read thread."""
        if not self.read_thread_active:
            self.read_thread_active = True
            self.read_thread = threading.Thread(target=self._read_thread_function)
            self.read_thread.start()
            self.read_logger.info("Read thread started.")

    def stop_read_thread(self):
        """Stop read thread."""
        if self.read_thread_active:
            self.read_thread_active = False
            self.read_thread.join()
            self.read_logger.info("Read thread stopped.")

    def start_handler_thread(self):
        """Start handler thread."""
        if not self.handler_thread_active:
            self.handler_thread_active = True
            self.handler_thread = threading.Thread(target=self._handler_thread_function)
            self.handler_thread.start()
            self.handler_logger.info("handler thread started.")

    def stop_handler_thread(self):
        """Stop handler thread."""
        if self.handler_thread_active:
            self.handler_thread_active = False
            self.handler_thread.join()
            self.handler_logger.info("Handler thread stopped.")

    def _read_thread_function(self):
        while self.read_thread_active:
            try:
                self.read_to_deque()
            except USBError:
                pass

    def _channel_response_handler(self, message):
        message_dict = ChannelResponseMessage.to_dict(message)
        code = message_dict["code"]
        message_id = message_dict["id"]
        if (
            code == ChannelResponseMessage.Code.RESPONSE_NO_ERROR
            and message_id == Id.SetNetworkKey
        ):
            self.network_flag = True
            return True
        return False

    def _handler_thread_function(self):
        while self.handler_thread_active:
            try:
                rtn = None
                message = self.read_message_from_deque()
                message_dict = AntMessage.decompose_to_dict(message)
                channel = message_dict["channel"]
                if channel == 0 and message_dict["id"] == Id.ChannelResponse:
                    if self._channel_response_handler(message):
                        continue
                self.handler_logger.debug(
                    "Passed %s to %s", message_dict, self.channels[channel]
                )
                rtn = self.channels[channel].handle_received_message(
                    message, message_dict
                )
                if isinstance(rtn, AntMessage):
                    self._write(rtn)
                    self.handler_logger.debug(
                        "Wrote %s to dongle.", AntMessage.decompose_to_dict(rtn)
                    )
                if isinstance(rtn, list):
                    for msg in rtn:
                        self._write(msg)
                        self.handler_logger.debug(
                            "Wrote %s to dongle.", AntMessage.decompose_to_dict(msg)
                        )
            except NoMessagesInDeque:
                pass
                # except AttributeError:
            #   self.handler_logger.warning(
            #        "Received message on unexpected channel %d", channel
            #  )
            except UnknownMessageID:
                self.handler_logger.warning(
                    "Received message with unknown id %d", message_dict["id"]
                )
            except InvalidMessageError:
                self.handler_logger.warning("Ignoring invalid message %s", message)

    def read_to_deque(self):
        """Read from usb to deque."""
        messages = self._read()
        self.read_logger.debug("Read %s to deque", messages)
        for item in messages:
            self.messages_deque.append(item)

    def read_message_from_deque(self):
        """Read a complete message from the deque."""
        item = None
        try:
            while item != SYNC:
                item = self.messages_deque.popleft()
            message = item.to_bytes()
        except IndexError:
            raise NoMessagesInDeque from None
        item = None
        try:
            length = self.messages_deque.popleft()
            message += length.to_bytes()

            for _ in range(2, length + 4):
                item = self.messages_deque.popleft()
                message += item.to_bytes()
            return message
        except IndexError:
            for item in reversed(message):
                self.messages_deque.appendleft(item)
            raise NoMessagesInDeque from None


class USBDongle(Dongle):
    """Uses pyusb to communicate with usb dongle."""

    def _get_dongle(self) -> bool:
        self.cycplus = False

        if self.device_id is None:
            dongle_types = {(4104, "Suunto"), (4105, "Garmin"), (4100, "Older")}
        else:
            dongle_types = {(self.device_id, "(provided)")}

        found_available_ant_stick = False

        for dongle_type in dongle_types:
            ant_pid = dongle_type[0]
            if debug.on(debug.Function):
                logfile.Write(
                    f"_get_dongle - Check for dongle {ant_pid} {dongle_type[1]}"
                )
            try:
                devices = usb.core.find(find_all=True, idProduct=ant_pid)
            except NoBackendError as e:
                logfile.Console(f"GetDongle - Exception: {e}")
            else:
                for self.device in devices:
                    assert self.device is not None
                    if debug.on(debug.Function):
                        s = (
                            f"GetDongle - Try dongle: manufacturer="
                            f"{self.device.manufacturer}, product={self.device.product}"
                            f", vendor={hex(self.device.idVendor)}, product="
                            f"{hex(self.device.idProduct)}({self.device.idProduct})"
                        )
                        logfile.Console(s.replace("\0", ""))
                    if debug.on(debug.Data1 | debug.Function):
                        logfile.Print(self.device)

                    if os.name == "posix":
                        if debug.on(debug.Function):
                            logfile.Write("GetDongle - Detach kernel drivers")
                        for config in self.device:
                            for i in range(config.bNumInterfaces):
                                if self.device.is_kernel_driver_active(i):
                                    self.device.detach_kernel_driver(i)
                    if debug.on(debug.Function):
                        logfile.Write("GetDongle - Set configuration")
                    try:
                        self.device.set_configuration()
                        found_available_ant_stick = self._check_if_ant(self.device)
                        if found_available_ant_stick:
                            manufacturer = self.device.manufacturer
                            manufacturer = manufacturer.replace("\0", "")
                            if "CYCPLUS" in manufacturer:
                                self.cycplus = True
                            return True
                    except USBError as e:
                        if debug.on(debug.Function):
                            logfile.Write(f"USBError: {e}")
        self.device = None
        return found_available_ant_stick

    def _check_if_ant(self, device):
        for _ in range(2):
            if debug.on(debug.Function):
                logfile.Write("GetDongle - Send reset string to dongle")
            if self.reset(device):
                return True
        return False

    def _write(self, message):
        if self.device is not None:
            return self.device.write(0x01, message)
        raise NoDongle

    def _read(self):
        if self.device is not None:
            return self.device.read(0x81, 64)
        raise NoDongle

    def release(self):
        """Release dongle."""
        if self.max_channels is not None:
            for i in range(0, self.max_channels):
                if self.channels[i] is not None:
                    self.close_and_unassign_channel(i)
        self._flush()
        if self.device is not None:
            assert self.reset()
            for cfg in self.device:
                for intf in cfg:
                    usb.util.release_interface(self.device, intf)
            usb.util.dispose_resources(self.device)
            self.device = None
            self.logger.info("Dongle released.")
            return True
        self.logger.warning("Dongle failed to release.")
        return False


class NoDongle(Exception):
    """Raise when no physical dongle is set."""


class NoMoreChannels(Exception):
    """Raise when all channels are in use."""


class NoMoreNetworks(Exception):
    """Raise when all networks have been assigned."""


class NoMessagesInDeque(Exception):
    """Raise when the deque has no more complete messages."""


class UnknownMessageID(Exception):
    """Raise when attempting to handle an unknown message ID."""

    def __init__(self, info: bytes, message_id: int, interface: str):
        self.info = info
        self.message_id = message_id
        self.interface = interface
        self.message = f"Message id {message_id} is not known by {interface}"
