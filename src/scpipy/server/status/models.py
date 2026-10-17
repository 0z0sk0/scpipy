import enum


class StandardEvent(enum.IntFlag):
    """
    Standard Event Status Register bits (*ESR).

    It defines standard system events and error flags tracked by
    instrument core status system.
    """

    OPERATION_COMPLETE = 1 << 0  # OPC: All pending operations are finished.
    REQUEST_CONTROL = (
        1 << 1
    )  # RQC: Instrument is requesting control in a controller configuration.
    QUERY_ERROR = (
        1 << 2
    )  # QYE: Data was lost, or output queue was read when empty.
    DEVICE_DEPENDENT_ERROR = (
        1 << 3
    )  # DDE: Internal, non-standard hardware or device error occurred.
    EXECUTION_ERROR = (
        1 << 4
    )  # EXE: Parameter was out of range or execution was blocked.
    COMMAND_ERROR = (
        1 << 5
    )  # CME: Syntax error or unknown SCPI command encountered.
    USER_REQUEST = (
        1 << 6
    )  # URQ: Front panel button or local user control was activated.
    POWER_ON = 1 << 7  # PON: Instrument power cycle has occurred.


class StatusByte(enum.IntFlag):
    """
    Status Byte Register summary bits (*STB).

    It acts as top-level summary register aggregating statuses from
    all other sub-register groups and queues.
    """

    ERROR_QUEUE = 1 << 2  # EAV: Error or event is available in system queue.
    QUESTIONABLE = 1 << 3  # QUES: Summary bit for Questionable Status Group.
    MESSAGE_AVAILABLE = (
        1 << 4
    )  # MAV: Data is available in instrument output buffer.
    EVENT_STATUS = (
        1 << 5
    )  # ESB: Summary bit for Standard Event Status Register.
    MASTER_SUMMARY = (
        1 << 6
    )  # MSS / RQS: Master Summary Status or Request for Service indicator.
    OPERATION = 1 << 7  # OPER: Summary bit for Operation Status Group.


class OperationStatus(enum.IntFlag):
    """
    Operation Status Group bits (STATus:OPERation).

    It tracks conditions related to normal operating state and
    ongoing execution routines of instrument.
    """

    CALIBRATING = (
        1 << 0
    )  # Instrument is currently performing internal calibration.
    SETTLING = 1 << 1  # Instrument signals or circuits are stabilizing.
    RANGING = 1 << 2  # Instrument is changing its measurement hardware range.
    SWEEPING = 1 << 3  # A sweep is in progress.
    MEASURING = (
        1 << 4
    )  # Instrument is actively acquiring data or performing a measurement.
    WAITING_FOR_TRIGGER = (
        1 << 5
    )  # Device is ready and waiting for an external or internal trigger.
    WAITING_FOR_ARM = (
        1 << 6
    )  # Device is waiting to be armed before it can accept a trigger.
    CORRECTING = (
        1 << 7
    )  # Instrument is applying internal correction or normalization logic.
    INSTRUMENT_SUMMARY = (
        1 << 13
    )  # Summary bit for logical multi-channel instrument sub-modules.
    PROGRAM_RUNNING = (
        1 << 14
    )  # A user or internal test program is currently executing.


class QuestionableStatus(enum.IntFlag):
    """
    Questionable Status Group bits (STATus:QUEStionable).

    It monitors conditions indicating that data or measurements might
    be untrustworthy, degraded, or out of normal bounds.
    """

    VOLTAGE = (
        1 << 0
    )  # Voltage levels are unstable, overloaded, or questionable.
    CURRENT = 1 << 1  # Current limits or circuitry states are questionable.
    TIME = (
        1 << 2
    )  # Time-related parameters or timeout limits are questionable.
    POWER = 1 << 3  # Power supply or signal power bounds are compromised.
    TEMPERATURE = (
        1 << 4
    )  # Internal components are operating outside safe temperature limits.
    FREQUENCY = (
        1 << 5
    )  # Signal frequency is unlocked or out of expected bounds.
    PHASE = (
        1 << 6
    )  # Phase lock or relative phase calculations are questionable.
    MODULATION = (
        1 << 7
    )  # Modulation parameters or signal quality are degraded.
    CALIBRATION = 1 << 8  # Calibration constants or validity are questionable.
    INSTRUMENT_SUMMARY = (
        1 << 13
    )  # Summary bit for questionable metrics in sub-modules.
    COMMAND_WARNING = (
        1 << 14
    )  # An operation succeeded but with potential quality issues.
