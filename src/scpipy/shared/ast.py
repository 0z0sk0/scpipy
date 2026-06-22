import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class Argument:
    """Represent a command argument or pattern placeholders."""

    value: str
    pattern: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class Node:
    """Represent a single SCPI command node."""

    short: str
    full: str
    arg: Argument | None = None
    optional: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class Command:
    """Represent a parsed SCPI command."""

    nodes: list[Node]
    args: list[Argument] = dataclasses.field(default_factory=list)
    query: bool = False
    root_node: bool = False
    common: bool = False
