"""Specialized scanner interface."""
import csv
from fortius_ant.ant.interface import AntInterface
from fortius_ant.ant import util


class ScannerInterface(AntInterface):
    """Retransmit received data on target interface."""

    target_channel: int
    paired = True

    def __init__(self, interface, filename="scanner-log.csv"):
        self.output_file = open(filename, "w", encoding="UTF-8")
        self.csv_writer = csv.DictWriter(
            self.output_file,
            fieldnames=[
                "device_number",
                "device_type_id",
                "source",
                "message",
                "message_dict",
                "page_number",
                "page_dict",
                "timestamp",
            ],
        )
        self.csv_writer.writeheader()
        assert isinstance(interface, AntInterface)
        super().__init__(interface.master, interface.device_number)
        self.interface = interface
        self.logger = self.logger.getChild(interface.__class__.__name__)

        self.device_type_id = interface.device_type_id
        self.device_number = interface.device_number

        self.master = interface.master

        self.network_key = interface.network_key
        self.transmit_power = interface.transmit_power

        self.channel_period = interface.channel_period
        self.channel_frequency = interface.channel_frequency
        self.channel_search_timeout = interface.channel_search_timeout

        self.channel_type = interface.channel_type

        self.transmission_type = interface.transmission_type

        self.last_timestamps = []
        self.device_numbers = []

    def handle_received_message(self, message, message_dict):
        """Log message interval if extended data timestamp is present."""
        try:
            channel_id = message_dict["parsed_extended_data"]["channel_id"]
            device_number = channel_id["device_number"]
            out = {
                "device_number": device_number,
                "device_type_id": channel_id["device_type_id"],
                "message": message,
                "message_dict": message_dict,
                "page_number": message_dict["page_number"],
                "timestamp": message_dict["parsed_extended_data"]["timestamp"],
            }
            if device_number not in self.device_numbers:
                self.device_numbers.append(device_number)
                self.last_timestamps.append(None)
            index = self.device_numbers.index(device_number)
            last_timestamp = self.last_timestamps[index]
            if last_timestamp is not None:
                timestamp = message_dict["parsed_extended_data"]["timestamp"]
                if timestamp < last_timestamp:
                    timestamp += 2**16
                interval = timestamp - last_timestamp
                source = "master"
                out["source"] = source
                if interval < 100:
                    source = "slave"
                self.logger.debug(
                    "Device: %d, message interval is %d so message is probably from %s",
                    device_number,
                    interval,
                    source,
                )
                error_margin = 10
                if interval > self.channel_period + error_margin:
                    self.logger.warning(
                        "Message interval is much greater than specified channel "
                        "period, messages may have been missed"
                    )

            self.last_timestamps[index] = message_dict["parsed_extended_data"][
                "timestamp"
            ]
            Interface = util.get_interface(
                message_dict["parsed_extended_data"]["channel_id"]["device_type_id"]
            )
            try:
                master = source == "master"
                Page = Interface.get_page_from_number(
                    message_dict["page_number"], master
                )
                self.logger.debug(
                    "Assigned to interface: %s, page: %s", Interface, Page
                )
                try:
                    page_dict = Page.unpage_to_dict(message_dict["info"])
                except (NotImplementedError, AttributeError):
                    try:
                        page_dict = Page.unpage(message_dict["info"])
                    except AttributeError:
                        out["page_dict"] = message_dict["info"]
                out["page_dict"] = page_dict
                self.logger.info(
                    "From %d:%s: parsed to %s", out["device_type_id"], source, page_dict
                )
            except (UnboundLocalError, NotImplementedError):
                pass
            self.csv_writer.writerow(out)
        except KeyError:
            pass
        rtn = AntInterface.handle_received_message(self, message, message_dict)
        if rtn is not None:
            self.logger.info("Writing %s to dongle", rtn)
        return rtn

    def _handle_broadcast_data(self, data_page_number: int, info: bytes):
        """No further handling required."""

    def _handle_acknowledged_data(self, data_page_number: int, info: bytes):
        """No further handling required."""

    def broadcast_message(self):
        """This is an rx only interface."""
