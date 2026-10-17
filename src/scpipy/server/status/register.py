from collections.abc import Callable

from scpipy.server.status.utils import _soft_clamp_value


class StatusRegister:
    """
    Generic SCPI Status Register Group.

    It represents a standard 16-bit SCPI register group (like OPERation or
    QUEStionable), incorporating Condition, Event, and Enable registers,
    along with Positive and Negative transition filters.
    """

    MASK = 0x7FFF

    def __init__(self, *, on_change: Callable[[], None] | None = None):
        self._condition = 0
        self._event = 0
        self._enable = 0
        self._positive_transition = self.MASK
        self._negative_transition = 0
        self._on_change = on_change

    def _changed(self):
        if self._on_change is not None:
            self._on_change()

    @property
    def condition(self) -> int:
        """
        STATus:<group>:CONDition?, without clearing register.

        It returns current state of instrument signals.

        :return: Current condition register bits
        :rtype: int
        """
        return self._condition

    def set_condition(self, value: int):
        """
        Set condition register value and update event register.

        It calculates rising and falling edges based on transition filters
        and updates the Event register accordingly.

        :param value: New condition register state.
        :type value: int
        """
        value = _soft_clamp_value(value, self.MASK)
        rising = value & ~self._condition
        falling = self._condition & ~value
        self._condition = value
        self._event |= (rising & self._positive_transition) | (
            falling & self._negative_transition
        )
        self._changed()

    def update_condition(self, mask: int, active: bool):
        """
        Update specific bits within condition register.

        :param mask: Bitmask defining which bits to alter.
        :type mask: int
        :param active: True to set bits, False to clear bits.
        :type active: bool
        """
        mask = _soft_clamp_value(mask, self.MASK)
        self.set_condition(
            self._condition | mask if active else self._condition & ~mask,
        )

    @property
    def event(self) -> int:
        return self._event

    def read_event(self) -> int:
        """
        STATus:<group>[:EVENt]?, with clearing register after reading.

        It returns the contents of Event register and automatically
        clears it to 0.

        :return: Event register bits value before clearance
        :rtype: int
        """
        result = self._event
        self.clear()
        return result

    def clear(self):
        """Clear event register to 0."""
        self._event = 0
        self._changed()

    @property
    def enable(self) -> int:
        """
        STATus:<group>:ENABle?, without clearing register.

        :return: Currently set mask for events
        :rtype: int
        """
        return self._enable

    @enable.setter
    def enable(self, value: int):
        """
        STATus:<group>:ENABle.

        It controls which specific events from Event register are
        allowed to propagate to summary bit.

        :param value: A 16-bit number.
        :type value: int
        """
        self._enable = _soft_clamp_value(value, 0xFFFF) & self.MASK
        self._changed()

    @property
    def positive_transition(self) -> int:
        """
        STATus:<group>:PTRansition?, without clearing register.

        :return: Currently set positive transition filter mask
        :rtype: int
        """
        return self._positive_transition

    @positive_transition.setter
    def positive_transition(self, value: int):
        """
        STATus:<group>:PTRansition.

        It sets positive transition filter.

        Setting a bit allows a 0-to-1 transition
        in Condition register to set corresponding
        bit in Event register.

        :param value: A 16-bit number.
        :type value: int
        """
        self._positive_transition = (
            _soft_clamp_value(value, 0xFFFF) & self.MASK
        )

    @property
    def negative_transition(self) -> int:
        """
        STATus:<group>:NTRansition?, without clearing register.

        :return: Currently set negative transition filter mask
        :rtype: int
        """
        return self._negative_transition

    @negative_transition.setter
    def negative_transition(self, value: int):
        """
        STATus:<group>:NTRansition.

        It sets the negative transition filter.

        Setting a bit allows a 1-to-0 transition
        in Condition register to set corresponding
        bit in Event register.

        :param value: A 16-bit number.
        :type value: int
        """
        self._negative_transition = (
            _soft_clamp_value(value, 0xFFFF) & self.MASK
        )

    @property
    def summary(self) -> bool:
        """
        Evaluate summary bit state for this register group.

        :return: True if any enabled event bit is active, False otherwise
        :rtype: bool
        """
        return bool(self._event & self._enable)

    def preset(self):
        """
        Preset sub-register group to factory defaults.

        It clears enable register and resets transition filters
        (positive filters enabled, negative filters disabled).
        """
        self._enable = 0
        self._positive_transition = self.MASK
        self._negative_transition = 0
        self._changed()
