from scpipy.server.route_handler import RouteHandler


def test_invoke_with_variadic_values(variadic_pattern):
    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=variadic_pattern)

    result = route_handler.invoke(
        object(),
        '3',
        '4',
        '5',
        '6',
        channel='1',
        some='2',
    )

    assert result == ('1', '2', ('3', '4', '5', '6'))


def test_invoke_without_variadic_values(simple_pattern):
    def handler(context, channel: int, some: int):
        return channel, some

    route_handler = RouteHandler(handler=handler, pattern=simple_pattern)

    result = route_handler.invoke(
        object(),
        channel='1',
        some='2',
    )

    assert result == ('1', '2')
