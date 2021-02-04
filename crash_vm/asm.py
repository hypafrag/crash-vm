import re
from itertools import count
from .cpu import Instructions, instruction_methods
from ._types import NativeNumber, Address

HEX_NUMBER_PATTERN = r'[\-\+]?(?:0x[0-9a-fA-F]+)'
DEC_NUMBER_PATTERN = r'[\-\+]?(?:\d+)'
NUMBER_PATTERN = rf'(?:{DEC_NUMBER_PATTERN}|{HEX_NUMBER_PATTERN})'
IDENTIFIER_FIRST_CHARACTER_PATTERN = r'[a-zA-Z_]'
IDENTIFIER_CHARACTER_PATTERN = r'[a-zA-Z_0-9]'
SPACER_CHARACTER_PATTERN = r'[ \t]'
LABEL_PATTERN = rf'{IDENTIFIER_FIRST_CHARACTER_PATTERN}{IDENTIFIER_CHARACTER_PATTERN}*:'
ADDRESS_PATTERN = rf'(?:{NUMBER_PATTERN}|{LABEL_PATTERN})'
INDENTATION_PATTERN = rf'^{SPACER_CHARACTER_PATTERN}*'
LINE_END_PATTERN = rf'{SPACER_CHARACTER_PATTERN}*(?:#.*)?$'
INSTRUCTION_NAME_PATTERN = '|'.join(map(lambda i: f'(?:{i.name})', Instructions))


class CompilationError(Exception):
    def __init__(self, message):
        super(CompilationError, self).__init__()
        self.message = message

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'


def int_to_native_number(value):
    native_number = NativeNumber(value)
    if value != native_number.value:
        raise CompilationError(f'Value {value} is out of range')
    return native_number


def parse_number(number_str: str) -> NativeNumber:
    if re.match(HEX_NUMBER_PATTERN, number_str):
        return int_to_native_number(int(number_str, 16))
    if re.match(NUMBER_PATTERN, number_str):
        return int_to_native_number(int(number_str))
    raise CompilationError(f'Invalid number value {number_str}')


def int_to_address(value):
    address = Address(value)
    if value != address.value:
        raise CompilationError(f'Value {value} is out of range')
    return address


def parse_address(address_str: str, labels: dict = None) -> Address:
    if re.match(HEX_NUMBER_PATTERN, address_str):
        return int_to_address(int(address_str, 16))
    if re.match(NUMBER_PATTERN, address_str):
        return int_to_address(int(address_str))
    if re.match(LABEL_PATTERN, address_str):
        if labels is None:
            raise CompilationError(f'Labels not allowed here')
        try:
            return labels[address_str]
        except KeyError:
            raise CompilationError(f'Invalid label {address_str}')
    raise CompilationError(f'Invalid address value {address_str}')


class Line:
    def __init__(self, *args):
        pass


class EmptyLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}{LINE_END_PATTERN}'


class OffsetLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}Offset{SPACER_CHARACTER_PATTERN}+({NUMBER_PATTERN}){LINE_END_PATTERN}'

    def __init__(self, offset_str):
        super(OffsetLine, self).__init__()
        self.offset = parse_address(offset_str)


class LabelLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}({LABEL_PATTERN}){LINE_END_PATTERN}'

    def __init__(self, identifier: str):
        super(LabelLine, self).__init__()
        self.identifier = identifier


class ValueLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}({NUMBER_PATTERN}){LINE_END_PATTERN}'

    def __init__(self, value: str):
        super(ValueLine, self).__init__()
        self.value = parse_number(value)


class InstructionLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}({INSTRUCTION_NAME_PATTERN})((?: +{ADDRESS_PATTERN})*){LINE_END_PATTERN}'

    def __init__(self, instruction_name: str, args_str: str):
        super(InstructionLine, self).__init__(instruction_name, args_str)
        args = args_str.strip().split(' ') if args_str else []
        try:
            instruction = Instructions[instruction_name]
        except KeyError:
            raise CompilationError(f'Invalid instruction {instruction_name}')
        _, arg_num = instruction_methods[instruction]
        if arg_num != len(args):
            raise CompilationError(f'Instruction {instruction_name} takes {arg_num} arguments, {len(args)} given')
        self.instruction = instruction
        self.args = tuple(args)

    def resolve_args(self, labels: dict):
        return map(lambda a: parse_address(a, labels), self.args)


def parse(lines):
    if isinstance(lines, str):
        lines = lines.split('\n')
    classes = [EmptyLine, OffsetLine, ValueLine, InstructionLine, LabelLine]

    for line_number, line in zip(count(1), lines):
        try:
            try:
                cls, match = next(filter(lambda p: p[1], map(lambda c: (c, re.match(c.Pattern, line)), classes)))
            except StopIteration:
                raise CompilationError('Invalid syntax')
            yield cls(*match.groups())
        except CompilationError as error:
            error.message = f'Line {line_number}: {error.message}'
            raise error


def compile(lines):
    offset = 0
    labels = {}
    parsed = list(parse(lines))
    # first pass to determine addresses of labels
    for line in parsed:
        if isinstance(line, OffsetLine):
            if line.offset.value < offset:
                raise CompilationError(f'Inavalid offset {line.offset.value} at {offset}')
            offset = line.offset.value
            continue
        if isinstance(line, InstructionLine):
            offset += 1 + len(line.args)
            continue
        if isinstance(line, ValueLine):
            offset += 1
            continue
        if isinstance(line, LabelLine):
            if line.identifier in labels:
                raise CompilationError(f'Label {line.identifier} duplicated')
            labels[line.identifier] = Address(offset)
            continue

    compiled = []
    offset = 0
    for line in parsed:
        if isinstance(line, OffsetLine):
            compiled += [NativeNumber(0)] * (line.offset.value - offset)
            offset = line.offset.value
            continue
        if isinstance(line, ValueLine):
            compiled.append(line.value)
            offset += 1
            continue
        if isinstance(line, InstructionLine):
            compiled += [line.instruction, *line.resolve_args(labels)]
            offset += 1 + len(line.args)
            continue

    return compiled
