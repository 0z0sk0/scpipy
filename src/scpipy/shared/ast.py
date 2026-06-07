import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class Argument:
    value: str


@dataclasses.dataclass(frozen=True, slots=True)
class Node:
    short: str
    full: str
    arg: Argument | None = None
    optional: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class Command:
    nodes: list[Node]
    args: list[Argument] = dataclasses.field(default_factory=list)
    query: bool = False
    root_node: bool = False
    common: bool = False
