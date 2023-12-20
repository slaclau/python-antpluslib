"""Provide a class structure for ANT+ data pages."""

__version__ = "2023-04-16"
# 2023-04-16    Rewritten in class based fashion

from enum import Enum
import struct

import libantplus.structConstants as sc


class AntPage(bytes):
    """Base class for ANT+ data pages."""

    message_format: str
    data_page_number: int

    def __init__(self, data: bytes):
        super(bytes, data)

    @classmethod
    def page(cls, *args):
        """Convert the supplied data to a data page."""
        args = (
            args[0],
            cls.data_page_number,
        ) + args[1:]
        return cls(struct.pack(cls.message_format, *args))

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Convert the supplied dict to a page."""
        raise NotImplementedError

    @classmethod
    def unpage(cls, page) -> tuple:
        """Convert the supplied page to a tuple of its data."""
        return struct.unpack(cls.message_format, page)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Convert the supplied page to a dict of its data."""
        raise NotImplementedError

    @classmethod
    def get_num_args(cls) -> int:
        return len(cls.message_format) - 2


class Page2(AntPage):
    """Page 2 contains control information."""

    data_page_number = 2

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fCurrentNotifications = sc.unsigned_char
    fReserved1 = sc.unsigned_char
    fReserved2 = sc.unsigned_char
    fReserved3 = sc.unsigned_char
    fReserved4 = sc.unsigned_char
    fReserved5 = sc.unsigned_char
    fDeviceCapabilities = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fCurrentNotifications
        + fReserved1
        + fReserved2
        + fReserved3
        + fReserved4
        + fReserved5
        + fDeviceCapabilities
    )


class Page70(AntPage):
    """Page 70 is a request for another page to be sent."""

    data_page_number = 70

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSlaveSerialNumber = sc.unsigned_short
    fDescriptorByte1 = sc.unsigned_char
    fDescriptorByte2 = sc.unsigned_char
    fReqTransmissionResp = sc.unsigned_char
    fRequestedPageNumber = sc.unsigned_char
    fCommandType = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fSlaveSerialNumber
        + fDescriptorByte1
        + fDescriptorByte2
        + fReqTransmissionResp
        + fRequestedPageNumber
        + fCommandType
    )

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Convert request page to dict."""
        unpage = cls.unpage(page)
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "slave_serial_number": unpage[2],
            "descriptor_1": unpage[3],
            "descriptor_2": unpage[4],
            "requested_response": unpage[5],
            "number_of_responses": unpage[5] & 0x7F,
            "response_with_acknowledged": bool((unpage[5] & 0x80) >> 7),
            "requested_page": unpage[6],
            "command_type": unpage[7],
        }


class Page80(AntPage):
    """Page 80 contains manufacturer information."""

    data_page_number = 80

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fReserved1 = sc.unsigned_char
    fReserved2 = sc.unsigned_char
    fHWrevision = sc.unsigned_char
    fManufacturerID = sc.unsigned_short
    fModelNumber = sc.unsigned_short

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fReserved1
        + fReserved2
        + fHWrevision
        + fManufacturerID
        + fModelNumber
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        reserved1 = 0xFF
        reserved2 = 0xFF
        hw_revision = kwargs["hw_revision"]
        manufacturer = kwargs["manufacturer"]
        model_number = kwargs["model_number"]
        return cls.page(
            channel, reserved1, reserved2, hw_revision, manufacturer, model_number
        )


class Page81(AntPage):
    """Page 81 contains device information."""

    data_page_number = 81

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fReserved1 = sc.unsigned_char
    fSWrevisionSupp = sc.unsigned_char
    fSWrevisionMain = sc.unsigned_char
    fSerialNumber = sc.unsigned_int

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fReserved1
        + fSWrevisionSupp
        + fSWrevisionMain
        + fSerialNumber
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        reserved = 0xFF
        sw_revision_supplemental = kwargs["sw_revision_supplemental"]
        sw_revision = kwargs["sw_revision"]
        serial_number = kwargs["serial_number"]
        return cls.page(
            channel, reserved, sw_revision_supplemental, sw_revision, serial_number
        )


class Page82(AntPage):
    """Page 82 contains the battery status."""

    data_page_number = 82

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fReserved1 = sc.unsigned_char
    fBatteryIdentifier = sc.unsigned_char
    fCumulativeTime1 = sc.unsigned_char
    fCumulativeTime2 = sc.unsigned_char
    fCumulativeTime3 = sc.unsigned_char
    fBatteryVoltage = sc.unsigned_char
    fDescriptiveBitField = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fReserved1
        + fBatteryIdentifier
        + fCumulativeTime1
        + fCumulativeTime2
        + fCumulativeTime3
        + fBatteryVoltage
        + fDescriptiveBitField
    )

    @classmethod
    def page(cls, *args):
        args = (args[0], 0xFF, 0x00, 0, 0, 0, 0, 0x0F | 0x10 | 0x00)
        return super(Page82, cls).page(*args)


class Page221_01(AntPage):
    """Sub page 1 for page 221 (Legacy trainers)."""

    data_page_number = 221
    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x01
    fSpeed = sc.unsigned_short  # speed (km/h) * 10
    fPower = sc.unsigned_short  # power (W)
    fCadence = sc.unsigned_char  # cadence (rpm)
    fBalance = sc.unsigned_char  # L/R power balance (%)

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fSpeed
        + fPower
        + fCadence
        + fBalance
    )


class Page221_02(AntPage):
    """Sub page 2 for page 221 (Legacy trainers)."""

    data_page_number = 221
    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x02

    fDistance = sc.unsigned_int  # distance (m)
    fHeartrate = sc.unsigned_char  # heartrate (bpm) (Vortex/Bushido only?)
    fPadding = sc.pad

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fDistance
        + fHeartrate
        + fPadding
    )


class Page221_03(AntPage):
    """Sub page 3 for page 221 (Legacy trainers)."""

    data_page_number = 221
    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x03

    fAlarm = sc.unsigned_short  # alarm bitmask
    fTemperature = sc.unsigned_char  # brake temperature (°C ?)
    fPowerback = sc.unsigned_short  # Powerback (W)
    fPadding = sc.pad

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fAlarm
        + fTemperature
        + fPowerback
        + fPadding
    )


class FEPage16(AntPage):
    """Page 16 contains generic trainer information."""

    data_page_number = 16
    EquipmentType = 0x19  # Trainer

    # Old: Capabilities = 0x30 | 0x03 | 0x00 | 0x00 # IN_USE | HRM | Distance | Speed
    #               bit  7......0   #185 Rewritten as below for better documenting bit-pattern
    HRM = 0b00000011  # 0b____ __xx bits 0-1  3 = hand contact sensor    (2020-12-28: Unclear why this option chosen)
    Distance = 0b00000000  # 0b____ _x__ bit 2     0 = No distance in byte 3  (2020-12-28: Unclear why this option chosen)
    VirtualSpeedFlag = 0b00000000  # 0b____ x___ bit 3     0 = Real speed in byte 4/5 (2020-12-28: Could be virtual speed)
    FEstate = 0b00110000  # 0b_xxx ____ bits 4-6  3 = IN USE
    LapToggleBit = 0b00000000  # 0bx___ ____ bit 7     0 = No lap toggle

    Capabilities = HRM | Distance | VirtualSpeedFlag | FEstate | LapToggleBit

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fEquipmentType = sc.unsigned_char
    fElapsedTime = sc.unsigned_char
    fDistanceTravelled = sc.unsigned_char
    fSpeed = sc.unsigned_short
    fHeartRate = sc.unsigned_char
    fCapabilities = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fEquipmentType
        + fElapsedTime
        + fDistanceTravelled
        + fSpeed
        + fHeartRate
        + fCapabilities
    )

    @classmethod
    def page(cls, *args):
        if len(args) < 7:
            args = (
                args[0],
                cls.EquipmentType,
            ) + args[1:]
            args = args + (cls.Capabilities,)
        return super(FEPage16, cls).page(*args)

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        equipment_type = (
            kwargs["equipment_type"]
            if "equipment_type" in kwargs
            else cls.EquipmentType
        )
        elapsed_time = kwargs["elapsed_time"]
        distance = kwargs["distance"]
        speed = kwargs["speed"]
        heart_rate = kwargs["heart_rate"]
        hrm_source = kwargs["hrm"] if "hrm" in kwargs else cls.HRM
        distance_enabled = (
            (kwargs["distance_enabled"] << 2) if "distance_enabled" in kwargs else 0
        )
        virtual_speed = (
            (kwargs["virtual_speed"] << 3) if "virtual_speed" in kwargs else 0
        )
        capabilities = hrm_source + distance_enabled + virtual_speed
        state = cls.FEstate >> 4
        bit_field = capabilities + (state << 4)
        return cls.page(
            channel,
            equipment_type,
            elapsed_time,
            distance,
            speed,
            heart_rate,
            bit_field,
        )

    @classmethod
    def get_num_args(cls) -> int:
        return super(FEPage16, cls).get_num_args() - 2


class FEPage17(AntPage):
    """Page 17 contains fitness equipment settings information."""

    data_page_number = 17

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)

    fReserved1 = sc.unsigned_char
    fReserved2 = sc.unsigned_char
    fCycleLength = sc.unsigned_char
    fIncline = sc.short
    fResistance = sc.unsigned_char
    fBits = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fReserved1
        + fReserved2
        + fCycleLength
        + fIncline
        + fResistance
        + fBits
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        reserved1 = 0xFF
        reserved2 = 0xFF
        cycle_length = kwargs["cycle_length"] if "cycle_length" in kwargs else 0xFF
        incline = kwargs["incline"] if "incline" in kwargs else 0x7FFF
        resistance = kwargs["resistance"]
        bits = 3 << 4
        return cls.page(
            channel, reserved1, reserved2, cycle_length, incline, resistance, bits
        )


class FEPage25(AntPage):
    """Page 25 contains specific trainer information."""

    data_page_number = 25

    Flags = 0x30  # Hmmm.... leave as is but do not understand the value

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fEvent = sc.unsigned_char
    fCadence = sc.unsigned_char
    fAccPower = sc.unsigned_short
    fInstPower = sc.unsigned_short  # The first four bits have another meaning!!
    fFlags = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fEvent
        + fCadence
        + fAccPower
        + fInstPower
        + fFlags
    )

    @classmethod
    def page(cls, *args):
        args = args + (cls.Flags,)
        return super(FEPage25, cls).page(*args)

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        event_count = kwargs["event_count"]
        cadence = kwargs["cadence"]
        accumulated_power = kwargs["accumulated_power"]
        power = kwargs["power"]
        status_bits = 0
        assert power <= 4094
        power = power + (status_bits << 12)
        return cls.page(channel, event_count, cadence, accumulated_power, power)

    @classmethod
    def get_num_args(cls) -> int:
        return super(FEPage25, cls).get_num_args() - 1


class FEPage48(AntPage):
    """FE basic resistance page."""

    data_page_number = 48

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fReserved = sc.unsigned_char * 6
    fResistance = sc.unsigned_char

    message_format = fChannel + fDataPageNumber + fReserved + fResistance

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Page from channel and resistance."""
        channel = kwargs["channel"]
        resistance = kwargs["resistance"]
        return cls.page(channel, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, resistance)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Unpage to channel, page number, and resistance."""
        unpage = cls.unpage(page)
        return {"channel": unpage[0], "page_number": unpage[1], "resistance": unpage[8]}


class FEPage54(AntPage):
    """FE capabilities page."""

    data_page_number = 54

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fReserved = sc.unsigned_char * 4
    fMaximumResistance = sc.unsigned_short
    fCapabilities = sc.unsigned_char
    message_format = (
        fChannel + fDataPageNumber + fReserved + fMaximumResistance + fCapabilities
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        reserved = 0xFF
        maximum_resistance = kwargs["maximum_resistance"]
        basic = kwargs["basic"] if "basic" in kwargs else 0
        power = kwargs["power"] if "power" in kwargs else 0
        simulation = kwargs["simulation"] if "simulation" in kwargs else 0

        capabilities = basic + (power << 1) + (simulation << 2)
        return cls.page(
            channel,
            reserved,
            reserved,
            reserved,
            reserved,
            maximum_resistance,
            capabilities,
        )


class HRMPage(AntPage):
    """Base class for HRM data pages."""

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSpec1 = sc.unsigned_char
    fSpec2 = sc.unsigned_char
    fSpec3 = sc.unsigned_char
    fHeartBeatEventTime = sc.unsigned_short
    fHeartBeatCount = sc.unsigned_char
    fHeartRate = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fSpec1
        + fSpec2
        + fSpec3
        + fHeartBeatEventTime
        + fHeartBeatCount
        + fHeartRate
    )

    @classmethod
    def page(cls, data_page_number, *args):
        cls.data_page_number = data_page_number
        return super(HRMPage, cls).page(*args)


class PWRPage16(AntPage):
    """This page contains power sensor data."""

    data_page_number = 16

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fEventCount = sc.unsigned_char
    fPedalPower = sc.unsigned_char
    fInstantaneousCadence = sc.unsigned_char
    fAccumulatedPower = sc.unsigned_short
    fInstantaneousPower = sc.unsigned_short

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fEventCount
        + fPedalPower
        + fInstantaneousCadence
        + fAccumulatedPower
        + fInstantaneousPower
    )

    @classmethod
    def page(cls, *args):
        args = args[0:2] + (0xFF,) + args[2:]
        return super(PWRPage16, cls).page(*args)


class SCSPage(AntPage):
    """This page contains speed and cadence sensor data."""

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fCadenceEventTime = sc.unsigned_short
    fCadenceRevolutionCount = sc.unsigned_short
    fSpeedEventTime = sc.unsigned_short
    fSpeedRevolutionCount = sc.unsigned_short

    message_format = (
        sc.no_alignment
        + fChannel
        + fCadenceEventTime
        + fCadenceRevolutionCount
        + fSpeedEventTime
        + fSpeedRevolutionCount
    )

    @classmethod
    def page(cls, *args):
        """Override page due to legacy format."""
        return cls(struct.pack(cls.message_format, *args))


class TacxPage172(AntPage):
    """This page requests information from a legacy Tacx device."""

    data_page_number = 172

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fSubPageNumber = sc.unsigned_char
    fMode = sc.unsigned_char
    fPadding = sc.pad * 5

    message_format = (
        sc.no_alignment + fChannel + fDataPageNumber + fSubPageNumber + fMode + fPadding
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Page from dict of channel, and sub page number."""
        channel = kwargs["channel"]
        sub_page = kwargs["sub_page"]
        mode = kwargs["mode"].value if "mode" in kwargs else 0
        sub_page_number = sub_page.value
        return cls.page(channel, sub_page_number, mode)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return dict of channel, page number, and sub page number."""
        unpage = cls.unpage(page)
        sub_page_number = unpage[2]
        sub_page = TacxInfoSubPage(sub_page_number)
        rtn = {"channel": unpage[0], "page_number": unpage[1], "sub_page": sub_page}
        if sub_page == TacxInfoSubPage.mode:
            rtn["mode"] = unpage[3]
        return rtn


class TacxPage173(AntPage):
    """This page responds to :class:`TacxPage172`."""

    data_page_number = 173

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fSubPageNumber = sc.unsigned_char
    fData = sc.unsigned_char * 6

    message_format = (
        sc.no_alignment + fChannel + fDataPageNumber + fSubPageNumber + fData
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Not implemented."""
        raise NotImplementedError

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Convert to dict depending on specific sub page."""
        unpage = cls.unpage(page)
        sub_page_number = unpage[2]
        sub_page = TacxInfoSubPage(sub_page_number)

        rtn = {"channel": unpage[0], "page_number": unpage[1], "sub_page": sub_page}

        if sub_page == TacxInfoSubPage.serial:
            rtn["mode"] = TacxHUMode(unpage[3])
            rtn["year"] = unpage[4]
            rtn["device_number"] = int.from_bytes(unpage[5:9])
        elif sub_page == TacxInfoSubPage.version:
            rtn["major_version"] = unpage[3]
            rtn["minor_version"] = unpage[4]
            rtn["build_number"] = int.from_bytes(unpage[5:7])
        elif sub_page == TacxInfoSubPage.battery:
            raise NotImplementedError
        return rtn


class TacxPage220(AntPage):
    """Wrapper for sub page classes."""

    data_page_number = 220

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fSubPageNumber = sc.unsigned_char
    fData = sc.unsigned_char * 6

    message_format = (
        sc.no_alignment + fChannel + fDataPageNumber + fSubPageNumber + fData
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        sub_page_number = kwargs["sub_page"]
        if sub_page_number == 1:
            return TacxPage220_01.page_from_dict(**kwargs)
        if sub_page_number == 2:
            return TacxPage220_02.page_from_dict(**kwargs)
        print(sub_page_number)
        raise RuntimeError

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        unpage = cls.unpage(page)
        sub_page_number = unpage[2]

        if sub_page_number == 1:
            return TacxPage220_01.unpage_to_dict(page)
        if sub_page_number == 2:
            return TacxPage220_02.unpage_to_dict(page)
        print(sub_page_number)
        raise RuntimeError


class TacxPage220_01(AntPage):
    """Target subpage for page 220 (Legacy trainers)."""

    data_page_number = 220

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x01

    fMode = sc.unsigned_char
    fTarget = sc.unsigned_int
    fWeight = sc.unsigned_char
    fReset = sc.unsigned_char
    fPadding = sc.pad

    message_format = (
        fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fMode
        + fTarget
        + fWeight
        + fReset
        + fPadding
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        sub_page_number = 1
        mode = kwargs["mode"]
        target = kwargs["target"]
        weight = kwargs["weight"]
        reset = 0xEE if kwargs["reset"] else 0
        return cls.page(channel, sub_page_number, mode, target, weight, reset)


class TacxPage220_02(AntPage):
    """Simulation subpage for page 220 (Legacy trainers)."""

    data_page_number = 220

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x01

    fWindCoefficient = sc.unsigned_int
    fWindSpeed = sc.unsigned_int
    fRollingResistance = sc.unsigned_int

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fWindCoefficient
        + fWindSpeed
        + fRollingResistance
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        channel = kwargs["channel"]
        sub_page_number = 2
        wind_coefficient = kwargs["wind_coefficient"]
        wind_speed = kwargs["wind_speed"]
        rolling_resistance = kwargs["rolling_resistance"]
        return cls.page(
            channel, sub_page_number, wind_coefficient, wind_speed, rolling_resistance
        )


class TacxPage221(AntPage):
    """Wrapper for sub page classes."""

    data_page_number = 221

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fSubPageNumber = sc.unsigned_char
    fData = sc.unsigned_char * 6

    message_format = (
        sc.no_alignment + fChannel + fDataPageNumber + fSubPageNumber + fData
    )

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        unpage = cls.unpage(page)
        sub_page_number = unpage[2]

        if sub_page_number == 1:
            return TacxPage221_01.unpage_to_dict(page)
        if sub_page_number == 2:
            return TacxPage221_02.unpage_to_dict(page)
        if sub_page_number == 3:
            return TacxPage221_03.unpage_to_dict(page)
        if sub_page_number == 16:
            return TacxPage221_16.unpage_to_dict(page)
        print(sub_page_number)
        raise RuntimeError


class TacxPage221_01(AntPage):
    """Sub page 1 for page 221 (Legacy trainers)."""

    data_page_number = 221
    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x01
    fSpeed = sc.unsigned_short  # speed (km/h) * 10
    fPower = sc.unsigned_short  # power (W)
    fCadence = sc.unsigned_char  # cadence (rpm)
    fBalance = sc.unsigned_char  # L/R power balance (%)

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fSpeed
        + fPower
        + fCadence
        + fBalance
    )

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return speed, power, cadence, and balance."""
        unpage = cls.unpage(page)
        sub_page = unpage[2]
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "sub_page": sub_page,
            "speed": unpage[3],
            "power": unpage[4],
            "cadence": unpage[5],
            "balance": unpage[6],
        }


class TacxPage221_02(AntPage):
    """Sub page 2 for page 221 (Legacy trainers)."""

    data_page_number = 221
    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x02

    fDistance = sc.unsigned_int  # distance (m)
    fHeartrate = sc.unsigned_char  # heartrate (bpm) (Vortex/Bushido only?)
    fPadding = sc.pad

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fDistance
        + fHeartrate
        + fPadding
    )

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return distance and heart rate."""
        unpage = cls.unpage(page)
        sub_page = unpage[2]
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "sub_page": sub_page,
            "distance": unpage[3],
            "heart_rate": unpage[4],
        }


class TacxPage221_03(AntPage):
    """Sub page 3 for page 221 (Legacy trainers)."""

    data_page_number = 221
    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char  # == 0x03

    fAlarm = sc.unsigned_short  # alarm bitmask
    fTemperature = sc.unsigned_char  # brake temperature (°C ?)
    fPowerback = sc.unsigned_short  # Powerback (W)
    fPadding = sc.pad

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fAlarm
        + fTemperature
        + fPowerback
        + fPadding
    )

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return alarm, temperature, and powerback if defined."""
        unpage = cls.unpage(page)
        sub_page = unpage[2]
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "sub_page": sub_page,
            "alarm": bin(unpage[3]),
            "bushido_alarm": BushidoPage16.bushido_alarm_to_dict(unpage[3]),
            "temperature": unpage[4],
            "powerback": unpage[5],
        }


class TacxPage221_16(AntPage):
    """Sub page 16 for page 221 (Legacy trainers)."""

    data_page_number = 221

    fChannel = sc.unsigned_char  # First byte of the ANT+ message content
    fDataPageNumber = sc.unsigned_char  # First byte of the ANT+ datapage (payload)
    fSubPageNumber = sc.unsigned_char

    fKey = sc.unsigned_char
    fPadding = sc.pad * 4
    fCount = sc.unsigned_char

    message_format = (
        sc.no_alignment
        + fChannel
        + fDataPageNumber
        + fSubPageNumber
        + fKey
        + fPadding
        + fCount
    )

    class KeyFlag(Enum):
        """Key press length."""

        normal = 0
        long = 8
        very_long = 12

    class KeyCode(Enum):
        """Key code."""

        none = 0
        left = 1
        up = 2
        ok = 3
        down = 4
        right = 5

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return key code, flag, and count."""
        unpage = cls.unpage(page)
        sub_page = unpage[2]
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "sub_page": sub_page,
            "key": unpage[3],
            "key_flag": cls.KeyFlag(unpage[3] >> 4),
            "key_code": cls.KeyCode(unpage[3] & 0xF),
            "key_count": unpage[4],
        }


class TacxPage0(AntPage):
    """Keep alive page for Tacx legacy HU."""

    data_page_number = 0

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fPadding = sc.pad * 7

    message_format = sc.no_alignment + fChannel + fDataPageNumber + fPadding


class TacxInfoSubPage(Enum):
    """Tacx info sub page enum (for pages 172 and 173)."""

    serial = 1
    version = 2
    mode = 3
    battery = 4
    brake_version = 0x11
    brake_serial = 0x12


class TacxHUMode(Enum):
    """Mode for Tacx Bushido and Vortex."""

    standalone = 0
    reset_distance = 1
    training = 2
    paused = 3
    pc = 4


class BushidoPage1(AntPage):
    """Contains power data from Bushido brake unit."""

    data_page_number = 1

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fData = sc.unsigned_short
    fPad = sc.pad

    message_format = sc.big_endian + fChannel + fDataPageNumber + fData * 3 + fPad

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Create page from channel and data."""
        channel = kwargs["channel"]
        data1 = kwargs["data1"]
        data2 = kwargs["data2"]
        data3 = kwargs["data3"]
        return cls.page(channel, data1, data2, data3)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return power."""
        unpage = cls.unpage(page)
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "data1": unpage[2],
            "power": unpage[3],
            "data2": unpage[4],
        }


class BushidoPage2(AntPage):
    """Contains speed, cadence, and balance data from Bushido brake unit."""

    data_page_number = 2

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fSpeed = sc.unsigned_short
    fCadence = sc.unsigned_char
    fBalance = sc.unsigned_char
    fPad = sc.pad * 3

    message_format = (
        sc.big_endian + fChannel + fDataPageNumber + fSpeed + fCadence + fBalance + fPad
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Create page from speed, cadence, and balance."""
        channel = kwargs["channel"]
        speed = kwargs["speed"]
        cadence = kwargs["cadence"]
        balance = kwargs["balance"]
        return cls.page(channel, speed, cadence, balance)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return power."""
        unpage = cls.unpage(page)
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "speed": unpage[2],
            "cadence": unpage[3],
            "balance": unpage[4],
        }


class BushidoPage4(AntPage):
    """Contains motor voltage and current data from Bushido brake unit."""

    data_page_number = 4

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fData = sc.unsigned_char * 7

    message_format = sc.big_endian + fChannel + fDataPageNumber + fData

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return data - format is currently unknown."""
        unpage = cls.unpage(page)
        return {"channel": unpage[0], "page_number": unpage[1], "data": unpage[2:9]}


class BushidoPage8(AntPage):
    """Contains distance data from Bushido brake unit."""

    data_page_number = 8

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fDistance = sc.unsigned_int
    fPad = sc.pad * 3

    message_format = sc.big_endian + fChannel + fDataPageNumber + fDistance + fPad

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return distance data."""
        unpage = cls.unpage(page)
        return {"channel": unpage[0], "page_number": unpage[1], "distance": unpage[2]}


class BushidoPage16(AntPage):
    """Contains alarm data from Bushido brake unit."""

    data_page_number = 16

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fPad = sc.pad
    fAlarm = sc.unsigned_short  # alarm bitmask
    fTemperature = sc.unsigned_char  # brake temperature (°C ?)
    fPadding = sc.pad * 3

    message_format = (
        sc.big_endian
        + fChannel
        + fDataPageNumber
        + fPad
        + fAlarm
        + fTemperature
        + fPadding
    )

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Create page from channel, alarm, and temeperature."""
        channel = kwargs["channel"]
        alarm = kwargs["alarm"]
        temperature = kwargs["temperature"]
        return cls.page(channel, alarm, temperature)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return alarm, temperature, and powerback if defined."""
        unpage = cls.unpage(page)
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "alarm": bin(unpage[2]),
            "bushido_alarm": BushidoPage16.bushido_alarm_to_dict(unpage[2]),
            "temperature": unpage[3],
        }

    @staticmethod
    def bushido_alarm_to_dict(alarm):
        """Convert alarm field to dict for Bushido."""
        temp1 = BushidoPage16._alarm(alarm, 0)
        temp2 = BushidoPage16._alarm(alarm, 1)
        temp4 = BushidoPage16._alarm(alarm, 2)
        overvoltage = BushidoPage16._alarm(alarm, 3)
        overcurrent1 = BushidoPage16._alarm(alarm, 4)
        overcurrent2 = BushidoPage16._alarm(alarm, 5)
        overspeed = BushidoPage16._alarm(alarm, 7)
        undervoltage = BushidoPage16._alarm(alarm, 8)
        virtual_power = BushidoPage16._alarm(alarm, 13)
        virtual_speed = BushidoPage16._alarm(alarm, 14)
        communications = BushidoPage16._alarm(alarm, 15)

        temp_level = temp1 + 2 * temp2 + 4 * temp4
        current_level = overcurrent1 + 2 * overcurrent2

        return {
            "temp_level": temp_level,
            "overvoltage": overvoltage,
            "current_level": current_level,
            "overspeed": overspeed,
            "undervoltage": undervoltage,
            "virtual_power": virtual_power,
            "virtual_speed": virtual_speed,
            "comms_error": communications,
        }

    @staticmethod
    def _alarm(alarm, bit_number):
        flag = 1 << bit_number
        return (alarm & flag) == flag


class BushidoPage34(AntPage):
    """Contains calibration data from Bushido brake unit."""

    data_page_number = 34

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fUnknown = sc.unsigned_short
    fStatus = sc.unsigned_char
    fRR = sc.unsigned_short
    fPad = sc.pad * 2

    message_format = (
        sc.big_endian + fChannel + fDataPageNumber + fUnknown + fStatus + fRR + fPad
    )

    class Status(Enum):
        """Calibration status Enum."""

        OFF = 0x00
        START_CYCLING = 0x01
        SPEED_UP = 0x02
        STOP_CYCLING = 0x03
        WAIT_FOR_SPIN_DOWN = 0x04
        SPIN_DOWN = 0x05
        PROCESSING = 0x06
        SHOW_DATA = 0x0A
        END_CALIBRATION = 0x0B
        FINISHED = 0x0C
        ERROR = 0x0D
        CALIBRATION_SUCCESSFUL = 0x42
        REQUEST_CALIBRATION_VALUE = 0x4D

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return rolling resistance and calibration status code."""
        unpage = cls.unpage(page)
        return {
            "channel": unpage[0],
            "page_number": unpage[1],
            "unknown": unpage[2],
            "status": cls.Status(unpage[3]),
            "rolling_resistance": unpage[4],
        }


class BushidoSlavePage1(AntPage):
    """Contains force target for Bushido brake unit."""

    data_page_number = 1

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fTarget = sc.unsigned_short
    fPad = sc.pad * 5

    message_format = sc.big_endian + fChannel + fDataPageNumber + fTarget + fPad

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Create page from channel and target force."""
        channel = kwargs["channel"]
        target = kwargs["target"]
        return cls.page(channel, target)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return target force."""
        unpage = cls.unpage(page)
        return {"channel": unpage[0], "page_number": unpage[1], "target": unpage[2]}


class BushidoPage35(AntPage):
    """Contains calibration command data for Bushido brake unit."""

    data_page_number = 35

    fChannel = sc.unsigned_char
    fDataPageNumber = sc.unsigned_char
    fCommand = sc.unsigned_char
    fPad = sc.pad * 6

    message_format = sc.big_endian + fChannel + fDataPageNumber + fCommand + fPad

    class Command(Enum):
        """Calibration command Enum."""

        START = 0x4D
        REQUEST_CALIBRATION_RESULT = 0x58
        REQUEST_ROLLING_RESISTANCE = 0x63

    @classmethod
    def page_from_dict(cls, **kwargs):
        """Create page from channel and command."""
        channel = kwargs["channel"]
        command = kwargs["command"]
        return cls.page(channel, command)

    @classmethod
    def unpage_to_dict(cls, page) -> dict:
        """Return command."""
        unpage = cls.unpage(page)
        return {"channel": unpage[0], "page_number": unpage[1], "command": unpage[2]}
