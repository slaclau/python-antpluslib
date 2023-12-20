"""Utility functions."""

from libantplus import interface
from libantplus.plus import scs, hrm
from libantplus.tacx import bushido


def _get_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from _get_subclasses(subclass)
        yield subclass


def get_interface(device_type_id):
    interfaces = _get_subclasses(interface.AntInterface)
    interfaces_dict = {}
    for intf in interfaces:
        interfaces_dict[intf.device_type_id] = intf
    return interfaces_dict[device_type_id]
