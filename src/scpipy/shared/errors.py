import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class ErrorCode:
    code: int
    message: str
