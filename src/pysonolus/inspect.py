from __future__ import annotations

import ast
import builtins
import importlib
from dataclasses import dataclass
from functools import lru_cache
from types import ModuleType
from typing import Any, Callable, Dict, Optional, final

try:
    from sourceinspect import getsource as getsource_inspect
except ImportError:
    from inspect import getsource as getsource_inspect


def getsource(func: Callable[..., Any]) -> str:
    return getsource_inspect(func)


def getmodule(obj: Any) -> Optional[str]:
    """Get the module name of a object. """
    if (result := getattr(obj, '__module__', None)) is not None:
        return result
    elif (result := getattr(obj, '__self__', None)) is not None:
        return getmodule(result)
    return None


def getname(obj: Any) -> Optional[str]:
    return getattr(obj, '__qualname__', None)


def getglobal(obj: type) -> Dict[str, Any]:
    result = importlib.import_module(obj.__module__).__dict__
    for base in obj.__bases__:
        result = {**getglobal(base), **result}
    return result


@dataclass
class Name():

    def eval(self) -> Any:
        raise NotImplementedError


@dataclass(init=True, frozen=True, eq=True)
@final
class RelativeName():
    """Name relative to a module. """
    module: ModuleType
    name: ast.expr

    @lru_cache(maxsize=128)
    def eval(self) -> Any:
        code = compile(
            ast.Expression(self.name),
            filename=self.module.__file__ or '<string>',
            mode='eval'
        )
        return eval(code, {**self.module.__dict__, **builtins.__dict__}, {})

    @lru_cache(maxsize=128)
    def as_qualified(self) -> QualifiedName:
        obj = self.eval()
        if (result := QualifiedName.from_function(obj)) is not None:
            return result
        else:
            if name := getname(self.module):
                parts = [name]
            else:
                parts = []
            name = self.name
            while name:
                if isinstance(name, ast.Name):
                    parts.append(name.id)
                    break
                elif isinstance(name, ast.Attribute):
                    parts.append(name.attr)
                    name = name.value
                else:
                    raise RuntimeError(f"Cannot resolve {name}")
            return QualifiedName('.'.join(parts))

    def param(self, name: str) -> str:
        return self.as_qualified(name).var(name)


@dataclass(init=True, frozen=True, eq=True)
@final
class QualifiedName():
    """Name with a module name. """
    name: str

    @staticmethod
    def from_function(func: Callable[..., Any]) -> Optional[QualifiedName]:
        if (
            (module_name := getmodule(func)) is not None
            and (name := getname(func)) is not None
        ):
            return QualifiedName(f'{module_name}.{name}')
        return None

    @lru_cache(maxsize=128)
    def eval(self) -> Any:
        parts = self.name.split('.')
        for i in range(1, len(parts)):
            try:
                module = importlib.import_module('.'.join(parts[:i]))
                name = '.'.join(parts[i:])
                return eval(name, {**builtins.__dict__, **module.__dict__}, {})
            except (ModuleNotFoundError, NameError, AttributeError):
                pass

    def var(self, name: str) -> str:
        return f"{self}${name}".replace('.', '$')

    def __str__(self) -> str:
        return self.name
