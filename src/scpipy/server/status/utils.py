def _soft_clamp_value(value: int, maximum: int) -> int:
    """
    Validate and restrict an integer value within range [0, maximum].

    It acts as a safety validator for SCPI register masks, ensuring that
    the provided value fits within the specified bit bounds.

    :param value: Value to validate.
    :type value: int
    :param maximum: Maximum allowed upper bound.
    :type maximum: int
    :return: Validated integer value.
    :rtype: int
    :raises ValueError: If value is not an integer or is out of bounds.
    """
    if not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f'Expected an integer from 0 to {maximum}')
    return value
