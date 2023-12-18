"""Extension of :module:`libantplus.interface` for ANT+."""
from dataclasses import dataclass

from libantplus.interface import AntInterface, UnsupportedPage
from libantplus.message import Id
from libantplus.plus.page import Page70

ant_plus_network_key = 0x45C372BDFB21A5B9


class AntPlusInterface(AntInterface):
    """Extension of :class:`AntInterface` for ANT+."""

    interleave = 0
    interleave_reset: int

    network_key = ant_plus_network_key
    channel_frequency = 57

    @dataclass
    class P71_Data:
        """Store data for P71."""

        LastReceivedCommandID = 255
        SequenceNr = 255
        CommandStatus = 255
        Data1 = 0xFF
        Data2 = 0xFF
        Data3 = 0xFF
        Data4 = 0xFF

    def __init__(self, master=True, device_number=0):
        super().__init__(master, device_number)
        self.p71_data = self.P71_Data()

    def initialize(self):
        """Initialize interface."""
        self.interleave = 0

    def broadcast_message(self):
        """Assemble the message to be sent."""
        message = self._broadcast_message(self.interleave)
        self.interleave += 1
        if self.interleave == self.interleave_reset:
            self.interleave = 0
        return message

    def _broadcast_message(self, interleave: int):
        raise NotImplementedError

    def _broadcast_page(self, page_number: int, message_id=Id.BroadcastData):
        raise NotImplementedError

    def _handle_received_message(self, message, message_dict):
        if (
            message_dict["id"] == Id.AcknowledgedData
            and message_dict["page_number"] == 70
        ):
            page_70_dict = Page70.unpage_to_dict(message_dict["info"])
            try:
                if page_70_dict["response_with_acknowledged"]:
                    response = []
                    for _ in range(0, page_70_dict["number_of_responses"]):
                        response.append(
                            self._broadcast_page(
                                page_70_dict["requested_page"],
                                message_id=Id.AcknowledgedData,
                            )
                        )
                    return response
                if not page_70_dict["response_with_acknowledged"]:
                    response = []
                    for _ in range(0, page_70_dict["number_of_responses"]):
                        response.append(
                            self._broadcast_page(page_70_dict["requested_page"])
                        )
                    return response
            except UnsupportedPage as e:
                self.logger.info("Page 70: %s", e.message)
        return AntInterface._handle_received_message(self, message, message_dict)
