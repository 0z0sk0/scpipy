import re

from scpipy.shared.ast import Argument, Command, Node
from scpipy.shared.exceptions import ParseError
from scpipy.shared.utils import (
    format_scpi_full_keyword,
    format_scpi_short_keyword,
)

_NODE_TOKEN_RE = re.compile(r'^([A-Z*]+)(\d+)?$')


class Parser:
    def parse(self, line: str) -> list[Command]:
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

        if '[:' not in line:
            if '[' in line or ']' in line:
                raise ParseError('Invalid bracket usage')
            return [cls._build_node(line, optional=False)]

        required_node, optional_node = cls._split_optional_node(line)

        nodes: list[Node] = []
        if required_node:
            nodes.append(cls._build_node(required_node, optional=False))
        nodes.append(cls._build_node(optional_node, optional=True))
        return nodes

    @staticmethod
    def _split_optional_node(line: str) -> tuple[str, str]:
        if not line.endswith(']'):
            raise ParseError('Invalid bracket usage')

        body = line[:-1]
        required_node, optional_node = body.split('[:', 1)

        required_node = required_node.strip()
        optional_node = optional_node.strip()

        if not optional_node:
            raise ParseError('Invalid node')

        return required_node, optional_node

    @classmethod
    def _build_node(cls, token: str, optional: bool) -> Node:
        keyword, arg = cls._split_node(token)
        arg = cls._build_arg(arg) if arg is not None else None

        return Node(
            short=format_scpi_short_keyword(keyword),
            full=format_scpi_full_keyword(keyword),
            arg=arg,
            optional=optional,
        )

    @staticmethod
    def _build_arg(value: str) -> Argument:
        return Argument(value=value)

    @classmethod
    def _build_args(cls, args: list[str]) -> list[Argument]:
        return [cls._build_arg(arg) for arg in args]

    @staticmethod
    def _split_node(node: str) -> tuple[str, str | None]:
        node = node.strip()
        if not node:
            raise ParseError('Invalid node')

        match = _NODE_TOKEN_RE.fullmatch(node.upper())
        if not match:
            raise ParseError('Invalid node')

        keyword = match.group(1)
        arg = match.group(2)
        return keyword, arg

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
