"""Command line test program."""

import logging

from libantplus import dongle, bridge, scanner
from libantplus.data import sport
from libantplus.plus import hrm, scs, fe
from libantplus.tacx import bushido
from datetime import datetime

usb_dongle = None
testing = False


def set_debug_level(level: int):
    logging.getLogger().setLevel(level)


def test(
    interface_type,
    master=True,
    fixed_values=False,
    extended={},
    loglevel=logging.INFO,
    log_messages=False,
):
    logging.getLogger().setLevel(loglevel)
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    device_number = 1 if master else 0
    if interface_type == "hrm":
        intf = hrm.AntHRM(master=master, device_number=device_number)
    elif interface_type == "scs":
        intf = scs.AntSCS(master=master, device_number=device_number)
    elif interface_type == "fe":
        intf = fe.AntFE(master=master, device_number=device_number)
    elif interface_type == "bhu":
        intf = bushido.BushidoHeadUnit(master=master, device_number=device_number)
    elif interface_type == "bbu":
        intf = bushido.BushidoBrake(master=master, device_number=device_number)
    if interface_type in ("hrm", "scs"):
        sport_data = sport.CyclingData()
        if master:
            sport_data.simulate(fixed_values=fixed_values)
        intf.data = sport_data
    elif interface_type in ("bhu", "fe"):
        sport_data = sport.TrainerData()
        if master:
            sport_data.simulate(fixed_values=fixed_values)
        intf.data = sport_data
    if log_messages:
        usb_dongle.save_messages_to_file = True
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    if extended:
        usb_dongle.configure_extended_messages(**extended)
    usb_dongle.configure_channel(intf)
    testing = True


def stop_test():
    global usb_dongle, testing
    assert testing
    assert usb_dongle.release()
    usb_dongle = None
    testing = False


def test_bushido_hu():
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    intf = bushido.BushidoHeadUnit(master=False)
    sport_data = sport.TrainerData()
    intf.data = sport_data
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_channel(intf)
    testing = True


def test_bushido_brake():
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    intf = bushido.BushidoBrake(device_number=5)
    sport_data = sport.TrainerData()
    intf.data = sport_data
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_channel(intf)
    testing = True


def test_rx_scan(type, use_scanner=False, device_number=0, filename="scanner-log.csv"):
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    if type == "hrm":
        intf = hrm.AntHRM(device_number=device_number)
    elif type == "scs":
        intf = scs.AntSCS(device_number=device_number)
    elif type == "fe":
        intf = fe.AntFE(device_number=device_number)
    elif type == "bhu":
        intf = bushido.BushidoHeadUnit(device_number=device_number)
    elif type == "bbu":
        intf = bushido.BushidoBrake(device_number=device_number)
    elif type == "bushido":
        intf = bushido.Bushido(device_number=device_number)
    if not use_scanner:
        usb_dongle.save_messages_to_file = True
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_extended_messages(channel_id=True, timestamp=True)
    if use_scanner:
        usb_dongle.configure_continuous_scan(
            scanner.ScannerInterface(intf, filename=filename)
        )
    else:
        usb_dongle.configure_continuous_scan(intf)
    testing = True


def test_bushido():
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    intf_b = bushido.BushidoBrake(device_number=5)
    intf_h = bushido.BushidoHeadUnit(master=False)
    sport_data = sport.TrainerData()
    intf_h.data = sport_data
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    usb_dongle.configure_channel(intf_b)
    # usb_dongle.configure_channel(intf_h)
    testing = True


def test_bridge():
    global usb_dongle, testing
    assert not testing
    usb_dongle = dongle.USBDongle()
    usb_dongle.startup()
    usb_dongle.start_read_thread()
    usb_dongle.start_handler_thread()
    bridge.AntBridge.configure(usb_dongle, bushido.BushidoBrake, 1)
    bridge.AntBridge.configure(usb_dongle, bushido.BushidoHeadUnit, 2)
    testing = True
