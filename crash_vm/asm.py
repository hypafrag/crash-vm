import re
from itertools import count
from .cpu import Instructions, InstructionArgTypes, instruction_methods
from ._types import NativeNumber, Address
from typing import Generator, List, Union
import itertools

LowercaseInstructions = {instruction.name.lower(): instruction for instruction in Instructions}

chain = itertools.chain.from_iterable

HEX_NUMBER_PATTERN = r'[\-\+]?(?:0x[0-9a-fA-F]+)'
DEC_NUMBER_PATTERN = r'[\-\+]?(?:\d+)'
NUMBER_PATTERN = rf'(?:{DEC_NUMBER_PATTERN}|{HEX_NUMBER_PATTERN})'
ADDRESS_LITERAL_PATTERN = NUMBER_PATTERN
IDENTIFIER_FIRST_CHARACTER_PATTERN = r'[a-zA-Z_]'
IDENTIFIER_CHARACTER_PATTERN = r'[a-zA-Z_0-9]'
SPACER_CHARACTER_PATTERN = r'[ \t]'
LABEL_PATTERN = rf'{IDENTIFIER_FIRST_CHARACTER_PATTERN}{IDENTIFIER_CHARACTER_PATTERN}*:'
LABEL_VALUE_PATTERN = rf':{IDENTIFIER_FIRST_CHARACTER_PATTERN}{IDENTIFIER_CHARACTER_PATTERN}*'
ADDRESS_PATTERN = rf'(?:{ADDRESS_LITERAL_PATTERN}|{LABEL_VALUE_PATTERN})'
INDENTATION_PATTERN = rf'^{SPACER_CHARACTER_PATTERN}*'
LINE_END_PATTERN = rf'{SPACER_CHARACTER_PATTERN}*(?:#.*)?$'
INSTRUCTION_NAME_PATTERN = '|'.join(map(lambda i: f'(?i:{i.name})', Instructions))


class CompilationError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'


def int_to_native_number(value):
    native_number = NativeNumber(value)
    if value != native_number.value:
        raise CompilationError(f'Value {value} is out of range')
    return native_number


def int_to_address(value):
    address = Address(value)
    if value != address.value and value != NativeNumber(value).value:
        raise CompilationError(f'Value {value} is out of range')
    return address


class Label(str):
    @staticmethod
    def __new__(cls, string_value):
        if re.match(rf'^{LABEL_PATTERN}$', string_value) is None:
            raise CompilationError(f'Invalid label')
        # noinspection PyArgumentList
        return str.__new__(cls, string_value[:-1])


class LabelValue(str):
    @staticmethod
    def __new__(cls, string_value):
        if re.match(rf'^{LABEL_VALUE_PATTERN}$', string_value) is None:
            raise CompilationError(f'Invalid label value')
        # noinspection PyArgumentList
        return str.__new__(cls, string_value[1:])


def parse_address_literal(address_str: str) -> Address:
    if re.match(HEX_NUMBER_PATTERN, address_str):
        return int_to_address(int(address_str, 16))
    if re.match(NUMBER_PATTERN, address_str):
        return int_to_address(int(address_str))
    raise CompilationError(f'Invalid address value {address_str}')


def parse_address(address_str: str, labels: dict = None) -> Union[Address, LabelValue]:
    try:
        return parse_address_literal(address_str)
    except CompilationError:
        pass
    if re.match(LABEL_VALUE_PATTERN, address_str):
        if labels is None:
            return LabelValue(address_str)
        try:
            return labels[address_str]
        except KeyError:
            raise CompilationError(f'Invalid label {address_str}')
    raise CompilationError(f'Invalid address value {address_str}')


class Line:
    def __init__(self, address: Address, *args):
        self.address = address

    def produced_bytes_padded_num(self) -> int:
        return 0

    def produced_bytes(self) -> List[Union[Instructions, NativeNumber, Address]]:
        return []

    def produce_bytes_padded(self) -> List[Union[Instructions, NativeNumber, Address]]:
        produced = self.produced_bytes()
        produced_len = len(produced)
        produced_bytes_padded_num = self.produced_bytes_padded_num()
        if produced_len > produced_bytes_padded_num:
            raise RuntimeError(f'{self.__class__}.produced_bytes returned too many bytes')
        return produced + [NativeNumber(0)] * (produced_bytes_padded_num - produced_len)


class EmptyLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}{LINE_END_PATTERN}'


class OffsetLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}(?i:offset){SPACER_CHARACTER_PATTERN}+({ADDRESS_LITERAL_PATTERN}){LINE_END_PATTERN}'

    def __init__(self, address, offset_str):
        super().__init__(address)
        self.offset = parse_address_literal(offset_str)
        if self.offset.value < address.value:
            raise CompilationError(f'Inavalid offset {self.offset.value} at {address.value}')

    def produced_bytes_padded_num(self) -> int:
        return self.offset.value - self.address.value


class LabelLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}({LABEL_PATTERN}){LINE_END_PATTERN}'

    def __init__(self, address: Address, identifier: str):
        super().__init__(address)
        self.label = Label(identifier)


class ValueLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}({ADDRESS_PATTERN}){LINE_END_PATTERN}'

    def __init__(self, address: Address, value: str):
        super().__init__(address)
        self.value = parse_address(value)

    def produced_bytes_padded_num(self):
        return 1

    def produced_bytes(self) -> List[Union[Instructions, NativeNumber, Address]]:
        return [self.value]


class InstructionLine(Line):
    Pattern = rf'{INDENTATION_PATTERN}({INSTRUCTION_NAME_PATTERN})((?:{SPACER_CHARACTER_PATTERN}+{ADDRESS_PATTERN})*){LINE_END_PATTERN}'

    def __init__(self, address: Address, instruction_name: str, args_str: str):
        super().__init__(address, instruction_name, args_str)
        args = args_str.strip().split(' ') if args_str else []
        try:
            instruction = LowercaseInstructions[instruction_name.lower()]
        except KeyError:
            raise CompilationError(f'Invalid instruction {instruction_name}')
        _, arg_type = instruction_methods[instruction]
        if arg_type == InstructionArgTypes.NoArg and args:
            raise CompilationError(f'Instruction {instruction_name} takes no arguments, {len(args)} given')
        if arg_type != InstructionArgTypes.NoArg and not args:
            raise CompilationError(f'Instruction {instruction_name} takes 1 arguments, none given')
        self.instruction = instruction
        self.args = tuple(map(parse_address, args))

    def produced_bytes_padded_num(self):
        return 1 + len(self.args)

    def produced_bytes(self) -> List[Union[Instructions, NativeNumber, Address, Label]]:
        return [self.instruction, *self.args]


def parse(lines) -> Generator[Line, None, None]:
    if isinstance(lines, str):
        lines = lines.split('\n')
    classes = [EmptyLine, OffsetLine, ValueLine, InstructionLine, LabelLine]
    line_address = 0
    for line_number, line in zip(count(1), lines):
        try:
            try:
                cls, match = next(filter(lambda p: p[1], map(lambda c: (c, re.match(c.Pattern, line)), classes)))
            except StopIteration:
                raise CompilationError('Invalid syntax')
            line = cls(Address(line_address), *match.groups())
            line_address += line.produced_bytes_padded_num()
            yield line
        except CompilationError as error:
            error.message = f'Line {line_number}: {line}\n    {error.message}'
            raise error


def compile(lines):
    parsed = list(parse(lines))

    # first pass to determine addresses of labels
    labels = {line.label: line.address for line in [line for line in parsed if isinstance(line, LabelLine)]}

    def resolve(line_number, byte):
        try:
            return labels[byte] if isinstance(byte, LabelValue) else byte
        except KeyError:
            raise CompilationError(f'Line {line_number}: Invalid label {byte}')

    # second pass to produce bytecode
    return list(chain([[resolve(line_number, byte) for byte in line.produce_bytes_padded()]
                       for line_number, line in zip(count(0), parsed)]))
