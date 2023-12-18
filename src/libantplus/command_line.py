"""Command line test program."""

import logging

from fortius_ant.ant import dongle, interface, bridge
from fortius_ant.ant.data import sport
from fortius_ant.ant.plus import hrm, scs
from fortius_ant.ant.tacx import bushido

usb_dongle = None
testing = False


def set_debug_level(level: int):
    logging.getLogger().setLevel(level)


def test(type, master=True, fixed_values=False):
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    device_number = 1 if master else 0
    if type == "hrm":
        intf = hrm.AntHRM(master=master, device_number=device_number)
    elif type == "scs":
        intf = scs.AntSCS(master=master, device_number=device_number)
    sport_data = sport.SportData()
    if master:
        sport_data.simulate(fixed_values=fixed_values)
        intf.data_source = sport_data
    else:
        intf.data_target = sport_data
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_channel(intf)
    testing = True


def stop_test():
    global usb_dongle, testing
    assert testing
    assert usb_dongle.release()
    usb_dongle = None
    testing = False


def test_bushido():
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    intf = bushido.BushidoBrake(master=False)
    intf2 = bushido.BushidoHeadUnit(master=False)
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_channel(intf)
    usb_dongle.configure_channel(intf2)
    testing = True


def test_bridge():
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    logging.getLogger().setLevel(logging.DEBUG)
    master = bushido.BushidoBrake(device_number=1)
    slave = bushido.BushidoBrake(master=False)
    ant_bridge = bridge.AntBridge(master, slave)
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_channel(ant_bridge.master)
    usb_dongle.configure_channel(ant_bridge.slave)
    testing = True
