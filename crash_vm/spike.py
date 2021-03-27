KEYWORDS = [
    'return',
    'const',
    'var'
]

BIN_OPERATORS = [
    '+', '-', '*'
]

HEX_NUMBER_PATTERN = r'[\-\+]?(?:0x[0-9a-fA-F]+)'
DEC_NUMBER_PATTERN = r'[\-\+]?(?:\d+)'
NUMBER_PATTERN = rf'(?:{DEC_NUMBER_PATTERN}|{HEX_NUMBER_PATTERN})'
SPACER_CHARACTER_PATTERN = r'[ \t]'
BIN_OPERATOR_PATTERN = '|'.join([f'\\{o}' for o in BIN_OPERATORS])
# VALUE_PATTERN = NUMBER_PATTERN
# BIN_OPERATION_EXPRESSION_PATTERN = rf'{VALUE_PATTERN}{SPACER_CHARACTER_PATTERN}*{BIN_OPERATOR_PATTERN}'\
#                                    rf'{SPACER_CHARACTER_PATTERN}*{VALUE_PATTERN}'


def parse(lines):
    if isinstance(lines, str):
        lines = lines.split('\n')
    print(lines)


def compile(code: str) -> str:
    parsed = parse(code)
    return ''
