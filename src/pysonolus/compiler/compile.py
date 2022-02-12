from __future__ import annotations

import importlib
import inspect
import itertools
from dataclasses import dataclass
from typing import Callable, Dict, Literal, Optional, Set, Union, overload

import pysonolus.post_init as post_init
from pysonolus.compiler.context import Context, FunctionContext
from pysonolus.compiler.core import Compiler
from pysonolus.compiler.function import CompiledFunction
from pysonolus.compiler.pre_compiled import compiled
from pysonolus.inspect import QualifiedName
from pysonolus.node.dispatch import dispatch
from pysonolus.node.IR import CallNode, Node

TSonolusFunction = Callable[[], Optional[float]]


@overload
def compile(
    func: TSonolusFunction,
    environment: Optional[Dict[QualifiedName, CompiledFunction]] = None,
    link: Literal[True] = True
) -> Node:
    ...


@overload
def compile(
    func: TSonolusFunction,
    environment: Optional[Dict[QualifiedName, CompiledFunction]] = None,
    link: Literal[False] = False
) -> CompileOutput:
    ...


def compile(
    func: TSonolusFunction,
    environment: Optional[Dict[QualifiedName, CompiledFunction]] = None,
    link: bool = True
) -> Union[CompileOutput, Node]:
    """Compile a Python function into Sonolus node.

    This method will recursively compile all of function calls in the function.

    Args:
        func: The function to compile.
        environment: The environment that contains compiled functions, defaults
            to `None`, which means to use the default environment.
        link: Whether to link the compile output to be a single node.

    Returns:
        CompileOutput if link is False, otherwise Node.
    """
    post_init.init()
    func_def = Compiler.parse(func)
    func_name = QualifiedName.from_function(func)
    if not func_name:
        raise ValueError(f"Cannot get function name from {func}")
    module = importlib.import_module(func.__module__)

    environment = environment or compiled()
    output = CompileOutput(func_name, {})
    context = Context()
    with context.use(FunctionContext) as c:
        params = Compiler.analyze_parameters(func_def.args, context)

        c.name = func_name
        c.module = module
        c.params = {
            arg.arg
            for arg in itertools.chain(
                func_def.args.posonlyargs, func_def.args.args,
                func_def.args.kwonlyargs
            )
        }

        compiled_function = CompiledFunction(
            func_name,
            params,
            Compiler.compile(func_def, context),
        )
        output.functions[func_name] = compiled_function
        environment[func_name] = compiled_function

        # recursively compile all of function calls
        for call in c.calls:
            c_func = call.eval()
            c_name = call.as_qualified()
            if c_name in environment:
                output.functions[c_name] = environment[c_name]
            else:
                if inspect.isbuiltin(c_func):
                    raise RuntimeError(
                        f"Cannot compile builtin function {c_name}"
                    )
                ref_output = compile(c_func, environment, link=False)
                output.functions.update(ref_output.functions)

    if link:
        return output.link()
    else:
        return output


@dataclass
@dataclass
class CompileOutput():
    """Output of the compiler.

    Name rule of the compiled function is at `CompiledFuncion.name`.
    """
    entry: QualifiedName
    """The entry point function's name."""
    functions: Dict[QualifiedName, CompiledFunction]
    """All of functions compiled."""

    def __str__(self) -> str:
        return f'main := {self.entry}\n' + '\n'.join(
            f'{name} := {function}'
            for name, function in self.functions.items()
        )

    @property
    def entry_func(self):
        return self.functions[self.entry]

    def link(self) -> Node:
        """Link all of CallNode to make a single Node.

        Starting from the entry point function, recursively inline all of
        CallNode with the corresponding CompiledFunction.

        Recursive call is not allowed (it will cause infinite inlining) and will
        be detected and raise an error when linking.
        """
        recursive: Set[QualifiedName] = set()
        return self._link(self.entry_func.node, recursive)

    @dispatch
    def _link(self, node: Node, recursive: Set[QualifiedName]) -> Node:
        ...

    @_link.register(CallNode)
    def _link_CallNode(
        self, entry: CallNode, recursive: Set[QualifiedName]
    ) -> Node:
        args = [self._link(arg, recursive) for arg in entry.args]
        kwargs = {
            kw: self._link(arg, recursive)
            for kw, arg in entry.kwargs.items()
        }
        name = entry.name
        if name in recursive:
            raise RuntimeError(f'Recursive call detected: {name}')
        recursive.add(name)
        result = self._link(self.functions[name].call(args, kwargs), recursive)
        recursive.remove(name)
        return result
