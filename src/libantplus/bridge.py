"""Bridge between two ANT interfaces."""
from libantplus.interface import AntInterface
from libantplus.message import AntMessage, Id


class AntBridge:
    """Bridge a master and slave interface together."""

    class BridgeInterface(AntInterface):
        """Retransmit received data on target interface."""

        target_channel: int

        def __init__(self, interface):
            assert isinstance(interface, AntInterface)
            super().__init__(interface.master, interface.device_number)
            self.interface = interface
            if self.interface.master:
                self.type = "master"
            else:
                self.type = "slave"
            self.logger = self.logger.getChild(
                interface.__class__.__name__ + "-" + self.type
            )

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

        def _handle_broadcast_data(self, data_page_number: int, info: bytes):
            self.logger.info(
                "Retransmit broadcast message %s from channel %d to channel %d",
                info,
                self.channel,
                self.target_channel,
            )
            array_info = bytearray(info)
            array_info[0] = self.target_channel
            info = bytes(array_info)
            return AntMessage.compose(Id.BroadcastData, info)

        def _handle_acknowledged_data(self, data_page_number: int, info: bytes):
            self.logger.info(
                "Retransmit acknowledged message %s from channel %d to channel %d",
                info,
                self.channel,
                self.target_channel,
            )
            array_info = bytearray(info)
            array_info[0] = self.target_channel
            info = bytes(array_info)
            return AntMessage.compose(Id.AcknowledgedData, info)

        def broadcast_message(self):
            """Do not broadcast actively, only retransmit."""

    def __init__(self, master, slave):
        assert isinstance(master, AntInterface)
        assert isinstance(slave, AntInterface)
        assert master.master
        assert not slave.master
        self.master = self.BridgeInterface(master)
        self.slave = self.BridgeInterface(slave)

    @classmethod
    def configure(cls, dongle, Interface, device_number):
        """Configure a bridge of the specified interface."""
        master = Interface(device_number=device_number)
        slave = Interface(master=False)

        bridge = cls(master, slave)
        dongle.configure_channel(bridge.slave)
        dongle.configure_channel(bridge.master)

        bridge.slave.target_channel = bridge.master.channel
        bridge.master.target_channel = bridge.slave.channel
