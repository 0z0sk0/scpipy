import re

from scpipy.shared.ast import Argument, Command, Node
from scpipy.shared.exceptions import ParseError
from scpipy.shared.utils import (
    format_scpi_full_keyword,
    format_scpi_short_keyword,
)

_NODE_TOKEN_RE = re.compile(
    r'^(?P<keyword>[A-Z*]+)(?:(?P<index>\d+)|<(?P<pattern>[A-Za-z_][A-Za-z0-9_]*)>)?$',
    re.IGNORECASE,
)


class Parser:
    """
    Parse SCPI command lines into command objects.

    Converts an input SCPI program message into a list of parsed
    ``Command`` instances that can be routed and dispatched.

    The parser supports full by SCPI protocol.
    """

    def parse(self, line: str) -> list[Command]:
        """
        Parse a SCPI command line.

        :param line: Raw SCPI command line.
        :type line: str

        :return: List of parsed SCPI commands.
        :rtype: list[Command]

        :raises ParseError: If the command line is empty or contains invalid
            SCPI syntax.
        """
        result = []
        scope_nodes = []

        for command in self._split_block(line):
            parsed = self._parse_command(command, scope_nodes)

            if parsed.common:
                scope_nodes = []
            else:
                scope_nodes = parsed.nodes[:-1]

            result.append(parsed)

        return result

    def _parse_command(self, command: str, scope_nodes: list[Node]) -> Command:
        if not (command := command.strip()):
            raise ParseError('Empty command')

        common = command.startswith('*')
        rooted = common or command.startswith(':')

        if rooted and not common:
            command = command[1:]

        header, args = self._split_node_and_args(command)
        args = self._build_args(args)

        query = header.endswith('?')
        if query:
            header = header[:-1]

        if common:
            nodes = [self._build_node(header, optional=False)]
        else:
            local_nodes = self._parse_header_nodes(header)

            if rooted or not scope_nodes:
                nodes = local_nodes
            else:
                nodes = scope_nodes + local_nodes

        return Command(
            nodes=nodes,
            args=args,
            query=query,
            root_node=rooted,
            common=common,
        )

    @staticmethod
    def _split_block(line: str) -> list[str]:
        line = line.strip()
        if not line:
            raise ParseError('Empty line')

        return [
            command.strip() for command in line.split(';') if command.strip()
        ]

    @classmethod
    def _parse_header_nodes(cls, header: str) -> list[Node]:
        parts = cls._split_nodes(header)
        nodes = []
        for node in parts:
            nodes.extend(cls._parse_node_part(node))
        return nodes

    @staticmethod
    def _split_nodes(command: str) -> list[str]:
        command = command.strip()
        if not command:
            raise ParseError('Command must contain at least one node')

        nodes = []
        current = ''
        in_brackets = False

        for character in command:
            if character == '[':
                if in_brackets:
                    raise ParseError('Invalid bracket usage')
                in_brackets = True
            elif character == ']':
                if not in_brackets:
                    raise ParseError('Invalid bracket usage')
                in_brackets = False
            elif character == ':' and not in_brackets:
                node = current.strip()
                if node:
                    nodes.append(node)
                current = ''
                continue

            current += character

        if in_brackets:
            raise ParseError('Invalid bracket usage')

        last_node = current.strip()
        if last_node:
            nodes.append(last_node)

        if not nodes:
            raise ParseError('Command must contain at least one node')

        return nodes

    @classmethod
    def _parse_node_part(cls, line: str) -> list[Node]:
        line = line.strip()
        if not line:
            raise ParseError('Invalid node')

        nodes = []
        pos = 0
        length = len(line)

        if not line.startswith('[:'):
            next_optional = line.find('[:')
            if next_optional == -1:
                return [cls._build_node(line, optional=False)]

            required = line[:next_optional].strip()
            if not required:
                raise ParseError('Invalid node')

            nodes.append(cls._build_node(required, optional=False))
            pos = next_optional

        while pos < length:
            if not line.startswith('[:', pos):
                raise ParseError('Invalid bracket usage')

            end = line.find(']', pos)
            if end == -1:
                raise ParseError('Invalid bracket usage')

            token = line[pos + 2 : end].strip()
            if not token:
                raise ParseError('Invalid node')

            nodes.append(cls._build_node(token, optional=True))
            pos = end + 1

        return nodes

    @classmethod
    def _build_node(cls, token: str, optional: bool) -> Node:
        keyword, arg, is_pattern = cls._split_node(token)
        arg = cls._build_arg(arg, is_pattern) if arg is not None else None

        return Node(
            short=format_scpi_short_keyword(keyword),
            full=format_scpi_full_keyword(keyword),
            arg=arg,
            optional=optional,
        )

    @staticmethod
    def _build_arg(value: str, is_pattern: bool = False) -> Argument:
        return Argument(value=value, pattern=is_pattern)

    @classmethod
    def _build_args(cls, args: list[str]) -> list[Argument]:
        return [cls._build_arg(arg) for arg in args]

    @staticmethod
    def _split_node(node: str) -> tuple[str, str | None, bool]:
        node = node.strip()
        if not node:
            raise ParseError('Invalid node')

        match = _NODE_TOKEN_RE.fullmatch(node)
        if not match:
            raise ParseError('Invalid node')

        keyword = match.group('keyword').upper()

        if match.group('index') is not None:
            return keyword, match.group('index'), False

        if match.group('pattern') is not None:
            return keyword, match.group('pattern'), True

        return keyword, None, False

    @staticmethod
    def _split_node_and_args(line: str) -> tuple[str, list[str]]:
        line = line.strip()
        if not line:
            raise ParseError('Empty command')

        parts = line.split(maxsplit=1)
        node = parts[0]

        if len(parts) == 1:
            return node, []

        args = [arg.strip() for arg in parts[1].split(',') if arg.strip()]
        return node, args
