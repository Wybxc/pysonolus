from __future__ import annotations
from dataclasses import dataclass

from typing import Any, ClassVar, Dict, NamedTuple, NoReturn, Optional, TypeVar, Union, final, get_type_hints
from pysonolus.inspect import getglobal
from pysonolus.node.IR import GetNode, Node, SetNode, ValueNode
from pysonolus.node.IR import Functions as F
from pysonolus.post_init import post_init, init

from pysonolus.typings import is_class_var, Array

T = TypeVar('T', bound=type)


@final
class StructMetaclass(type):

    def base_ptr(cls) -> Pointer:
        init()
        info = Struct.__blocks__.get(cls)
        if info is None:
            raise RuntimeError(f'{cls.__name__} is not a block')
        return info.base_ptr()

    def __getattr__(cls, name: str) -> Pointer:
        if name.startswith('_'):
            return object.__getattribute__(cls, name)
        if result := cls.base_ptr().to(name):
            return result
        raise AttributeError(f'{cls.__name__} has no attribute {name}')

    def __getitem__(cls, index: Union[int, Node]) -> Pointer:
        if result := cls.base_ptr().of(index):
            return result
        raise IndexError(f'{cls.__name__} has no index {index}')


class Struct(metaclass=StructMetaclass):
    __structs__: ClassVar[Dict[StructMetaclass, StructInfo]] = {}
    __blocks__: ClassVar[Dict[StructMetaclass, BlockInfo]] = {}

    def __init_subclass__(cls, block: Optional[int] = None):
        """Make a struct from a class. """
        Struct.init_block(cls, block)

    @staticmethod
    def init_block(struct_cls: StructMetaclass, block: Optional[int] = None):

        @post_init
        def _():
            struct = Struct.make_struct(struct_cls)
            if block is not None:
                Struct.__blocks__[struct_cls] = BlockInfo(block, struct)

    def __new__(cls, *args: Any, **kwargs: Any) -> NoReturn:
        raise TypeError('Structs cannot be instantiated.')

    @staticmethod
    def make_struct(struct: StructMetaclass) -> StructInfo:
        if struct in Struct.__structs__:
            return Struct.__structs__[struct]
        size = 0
        fields: Dict[str, StructField] = {}

        # parse annotations
        annotations = get_type_hints(struct, getglobal(struct))
        for name, anno in annotations.items():
            if is_class_var(anno):
                continue  # Do not include class variables

            if isinstance(anno, Array):
                type_ = anno.type
                times = anno.length
            else:
                type_ = anno
                times = 1

            if type_ is float or type_ is int:
                fields[name] = StructField.value(size)
                size += times
            elif isinstance(type_, StructMetaclass):
                sub = Struct.make_struct(type_)
                fields[name] = StructField(sub, size)
                size += sub.size * times
            else:
                raise TypeError(f'{name} is not supported!')

        result = StructInfo(size, fields)
        Struct.__structs__[struct] = result
        return result


class StructField(NamedTuple):
    info: StructInfo
    offset: int

    @staticmethod
    def value(offset: int) -> StructField:
        return StructField(StructInfo.value(), offset)


@dataclass(frozen=True)
@final
class StructInfo():
    size: int
    fields: Dict[str, StructField]

    @staticmethod
    def value() -> StructInfo:
        return StructInfo(1, {})


@dataclass(frozen=True)
@final
class BlockInfo():
    block: int
    struct: StructInfo

    def base_ptr(self):
        return Pointer(self.block, self.struct, 0)


@dataclass(frozen=True)
@final
class Pointer():
    block: int
    info: StructInfo
    index: int
    offset: Node = F.Value(0)

    def to(self, name: str) -> Optional[Pointer]:
        if field := self.info.fields.get(name):
            return Pointer(
                self.block, field.info, self.index + field.offset, self.offset
            )

    def of(self, offset: Union[int, Node]) -> Pointer:
        if isinstance(offset, ValueNode):
            if int(offset.value) == offset.value:
                raise ValueError(
                    'Pointer offset must be a node or a value that can be casted to int.'
                )
            offset = int(offset.value)
        if isinstance(offset, int):
            index = self.index + offset * self.info.size
            return Pointer(self.block, self.info, index, self.offset)
        else:
            offset = self.offset + offset * F.Value(self.info.size)
            return Pointer(self.block, self.info, self.index, offset)

    def __getattr__(self, name: str) -> Pointer:
        if result := self.to(name):
            return result
        raise AttributeError(
            f"{self.__class__.__name__} has no attribute {name}"
        )

    def __getitem__(self, offset: Union[int, Node]) -> Pointer:
        return self.of(offset)

    def get(self) -> GetNode:
        return GetNode(self.block, self.index, self.offset)

    def set(self, value: Node) -> SetNode:
        return SetNode(self.block, self.index, self.offset, value)