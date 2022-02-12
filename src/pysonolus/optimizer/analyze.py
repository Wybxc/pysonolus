from dataclasses import dataclass
from typing import Optional, Set, TypeVar, Union
from pysonolus.node.flow import Functions as F
from pysonolus.node.flow import *

T = TypeVar('T', bound=Union[Flow, Statement, Expr])


@dataclass()
class VarProperty():
    pure: bool
    is_alias: bool
    literal: Optional[Set[float]] = None


class Analyzer():

    def analyze(self, node: T) -> T:
        node_type = node.__class__.__name__
        analyzer = getattr(self, f"analyze_{node_type}", None)
        if analyzer:
            analyzer(node)
        else:
            node.apply(self.analyze)
        return node

    def analyze_AssignStatement(
        self, node: AssignStatement
    ) -> AssignStatement:
        self.analyze(node.value)

        return node