from scpipy.shared import Parser

parser = Parser()

# [Command(
#    nodes=[
#        Node(short='CALC', full='CALCulate', arg=Argument(value='1'), optional=False),
#        Node(short='TRAC', full='TRACe', arg=Argument(value='3'), optional=False),
#        Node(short='PAR', full='PARameter', arg=None, optional=False),
#        Node(short='DEF', full='DEFine', arg=None, optional=False)
#    ],
#    args=[Argument(value='S11')],
#    query=False,
#    root_node=False,
#    common=False
# )]
print(parser.parse('CALCulate1:TRACe3:PARameter:DEFine S11'))

# [Command(
#     nodes=[
#         Node(short='CALC', full='CALCulate', arg=None, optional=False),
#         Node(short='DAT', full='DATa', arg=None, optional=False),
#         Node(short='FDAT', full='FDATa', arg=None, optional=False)
#     ],
#     args=[Argument(value='S11')],
#     query=True,
#     root_node=False,
#     common=False
# )]
print(parser.parse('CALCulate:DATA:FDATa? S11'))

# [Command(
#     nodes=[
#         Node(short='SYST', full='SYSTem', arg=None, optional=False),
#         Node(short='READ', full='READy', arg=None, optional=False),
#         Node(short='STAT', full='STATe', arg=None, optional=True)
#     ],
#     args=[],
#     query=True,
#     root_node=False,
#     common=False
# )]
print(parser.parse('SYSTem:READy[:STATe]?'))

# [
#  Command(
#     nodes=[
#         Node(short='SYST', full='SYSTem', arg=None, optional=False),
#         Node(short='READ', full='READy', arg=None, optional=False)
#     ],
#     args=[],
#     query=True,
#     root_node=False,
#     common=False
#  ),
#  Command(
#     nodes=[
#         Node(short='SYST', full='SYSTem', arg=None, optional=False),
#         Node(short='STAT', full='STATe', arg=None, optional=False)
#     ],
#     args=[],
#     query=True,
#     root_node=False,
#     common=False
#  )
# ]
print(parser.parse('SYSTem:READy?;STATe?'))
