import pytest

from scpipy.server.status.register import StatusRegister


def test_positive_transitions_latch_independently_of_enable():
    register = StatusRegister()
    register.set_condition(5)
    register.set_condition(4)
    assert register.condition == 4
    assert register.event == 5
    assert not register.summary
    register.enable = 1
    assert register.summary
    assert register.read_event() == 5
    assert register.read_event() == 0
    assert register.condition == 4
    assert not register.summary

    register.set_condition(4)
    assert register.event == 0


def test_negative_both_and_disabled_transition_filters():
    register = StatusRegister()
    register.positive_transition = 0
    register.negative_transition = 1
    register.set_condition(3)
    assert register.event == 0
    register.set_condition(0)
    assert register.read_event() == 1
    register.positive_transition = 2
    register.negative_transition = 2
    register.set_condition(2)
    assert register.read_event() == 2
    register.set_condition(0)
    assert register.read_event() == 2
    register.negative_transition = 0
    register.positive_transition = 0
    register.set_condition(3)
    register.set_condition(0)
    assert register.event == 0


def test_clear_preserves_conditions_and_masks():
    register = StatusRegister()
    register.enable = 9
    register.negative_transition = 4
    register.positive_transition = 8
    register.set_condition(8)
    register.clear()
    assert (register.condition, register.event, register.enable) == (8, 0, 9)
    assert register.positive_transition == 8
    assert register.negative_transition == 4


def test_preset_preserves_events_and_conditions():
    register = StatusRegister()
    register.set_condition(2)
    register.enable = 2
    register.positive_transition = 0
    register.negative_transition = 2
    register.preset()
    assert register.condition == register.event == 2
    assert register.enable == 0
    assert register.positive_transition == 32767
    assert register.negative_transition == 0


@pytest.mark.parametrize(
    'field',
    ['enable', 'positive_transition', 'negative_transition'],
)
@pytest.mark.parametrize(
    'value,expected',
    [(0, 0), (32767, 32767), (32768, 0), (65535, 32767)],
)
def test_masks_accept_unsigned_16_bits_but_bit_15_is_always_zero(
    field,
    value,
    expected,
):
    register = StatusRegister()
    setattr(register, field, value)
    assert getattr(register, field) == expected


@pytest.mark.parametrize(
    'field',
    ['enable', 'positive_transition', 'negative_transition'],
)
@pytest.mark.parametrize('value', [-1, 65536, 1.2, '1'])
def test_python_mask_setters_reject_invalid_values(field, value):
    with pytest.raises(ValueError):
        setattr(StatusRegister(), field, value)


@pytest.mark.parametrize('value', [-1, 32768, 1.2])
def test_conditions_reject_invalid_values(value):
    with pytest.raises(ValueError):
        StatusRegister().set_condition(value)


def test_update_condition_preserves_other_flags_and_fires_callback():
    seen = []
    register = StatusRegister(on_change=lambda: seen.append(True))
    register.update_condition(1, True)
    register.update_condition(4, True)
    register.update_condition(1, False)
    assert register.condition == 4
    assert register.event == 5
    assert len(seen) == 3
