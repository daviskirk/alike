import operator
from typing import (
    Any,
    Callable,
    List,
    Mapping,
    NamedTuple,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")
OT = TypeVar("OT", bound="Op")


class _Constant:
    __slots__ = ("name",)

    def __init__(self, name) -> None:
        self.name: str = name

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return f"<{self.name}>"


MISSING = _Constant("MISSING")
PRESENT = _Constant("PRESENT")
NOTHING = _Constant("NOTHING")


class Op:
    """Delayed operation.

    Operation can be triggered by calling with an object.
    The triggering object is used as the FIRST argument of the operation.

    For example a binary operation can be modelled:

    >>> op = Op(lambda x, y: f"{x}: Hello {y}!", "Alice", "Bob", symbol="talks to")
    >>> str(op)
    "'Alice' talks to 'Bob'"
    >>> op()
    'Alice: Hello Bob!'

    Replacements can be made of the special variable ``alike.A`` is used:
    >>> op = Op(lambda x, y: f"{x}: Hello {y}!", A, "Bob", symbol="talks to")
    >>> str(op)
    "<A> talks to 'Bob'"
    >>> op("Carol")
    'Carol: Hello Bob!'

    Most comparison operators are supported
    >>> squared = Op(lambda x: x ** 2, A, symbol="squared")
    >>> op = (squared > 3) & (squared < 5)
    >>> op
    ((squared <A>) > 3) and ((squared <A>) < 5)
    >>> op(1), op(2), op(3)
    (False, True, False)
    >>> op = (squared <= 1) | (squared >= 9)
    >>> op
    ((squared <A>) <= 1) or ((squared <A>) >= 9)
    >>> op(1), op(2), op(3)
    (True, False, True)
    >>> op = (squared == 1) | (squared == 4)
    >>> op
    ((squared <A>) == 1) or ((squared <A>) == 4)
    >>> op(1), op(2), op(3)
    (True, True, False)
    >>> op = ~(squared == 1) & ~(squared == 4)
    >>> op
    (not ((squared <A>) == 1)) and (not ((squared <A>) == 4))
    >>> op(1), op(2), op(3)
    (False, False, True)

    """

    def __init__(self, op: Callable[..., Any], *args: Any, symbol: str = "") -> None:
        self.op = op
        self.args = args
        self.symbol = symbol or getattr(op, "__name__", "") or str(op)

    def __call__(self, a: Any = NOTHING) -> Any:
        args = [arg(a) if isinstance(arg, (Op, _A)) else arg for arg in self.args]
        return self.op(*args)

    def to_str(self, a=NOTHING) -> str:
        if a is NOTHING:
            a = A

        def arg_to_str(arg: Any) -> str:
            if isinstance(arg, Op):
                return "(" + arg.to_str(a) + ")"
            elif isinstance(arg, _A):
                return repr(a)
            return repr(arg)

        if len(self.args) != 1:
            pre_args, post_args = self.args[:1], self.args[1:]
        else:
            pre_args, post_args = (), self.args

        pre_arg_str = ", ".join(arg_to_str(arg) for arg in pre_args)
        post_arg_str = ", ".join(arg_to_str(arg) for arg in post_args)
        return f"{pre_arg_str} {self.symbol} {post_arg_str}".strip()

    def __repr__(self) -> str:
        return self.to_str()

    def __eq__(self: OT, b: Any) -> OT:  # type: ignore  # we're not returning a bool
        return type(self)(operator.eq, self, b, symbol="==")

    def __gt__(self: OT, b: Any) -> OT:
        return type(self)(operator.gt, self, b, symbol=">")

    def __lt__(self: OT, b: Any) -> OT:
        return type(self)(operator.lt, self, b, symbol="<")

    def __ge__(self: OT, b: Any) -> OT:
        return type(self)(operator.ge, self, b, symbol=">=")

    def __le__(self: OT, b: Any) -> OT:
        return type(self)(operator.le, self, b, symbol="<=")

    def __and__(self: OT, b: Any) -> OT:
        return type(self)(_apply_and, self, b, symbol="and")

    def __or__(self: OT, b: Any) -> OT:
        return type(self)(_apply_or, self, b, symbol="or")

    def __invert__(self: OT) -> OT:
        return type(self)(operator.not_, self, symbol="not")

    def __bool__(self):
        raise TypeError(
            "Operator cannot be truthy or falsy before evaluating. "
            "Most likely you have chained operators that cannot be chained."
        )

    # def __eq__(self, a: Any) -> "IsLike":  # type: ignore
    #     return Alike({"__root__": self}) == {"__root__": a}


def _apply_and(a, b, /) -> bool:
    return bool(a and b)


def _apply_or(a, b, /) -> bool:
    return bool(a or b)


class _A:
    """Placeholder object for delayed comparison of values.

    >>> op = (A < 10) | (A > 20)
    >>> op(5)
    True
    >>> op(30)
    True
    >>> op(15)
    False
    """

    def __eq__(self, b: Any) -> Op:  # type: ignore  # we're not returning a bool
        return Op(operator.eq, self, b, symbol="==")

    def __gt__(self, b: Any) -> Op:
        return Op(operator.gt, self, b, symbol=">")

    def __lt__(self, b: Any) -> Op:
        return Op(operator.lt, self, b, symbol="<")

    def __ge__(self, b: Any) -> Op:
        return Op(operator.ge, self, b, symbol=">=")

    def __le__(self, b: Any) -> Op:
        return Op(operator.le, self, b, symbol="<=")

    def __and__(self, b: Any) -> Op:
        return Op(_apply_and, self, b, symbol="and")

    def __or__(self, b: Any) -> Op:
        return Op(_apply_or, self, b, symbol="or")

    def __call__(self, value: T) -> T:
        return value

    def __invert__(self) -> Op:
        return Op(operator.not_, self, symbol="not")

    def __bool__(self):
        raise TypeError(
            "Operator cannot be truthy or falsy before evaluating. "
            "Most likely you have chained operators that cannot be chained."
        )

    def apply(self, callback: Callable[[Any], Any]):
        return Op(callback, self, symbol=f"{callback.__name__}")

    @property
    def length(self) -> Op:
        return Op(len, self, symbol="len")

    @property
    def is_falsy(self) -> Op:
        return Op(operator.not_, self, symbol="not")

    @property
    def is_missing(self) -> Op:
        return Op(operator.is_, self, MISSING, symbol="should be")

    @property
    def is_present(self) -> Op:
        return Op(operator.is_not, self, MISSING, symbol="value should not be")

    def isinstance(self, types: Union[type, Tuple[type, ...]]) -> Op:
        return Op(isinstance, self, types)

    def __repr__(self) -> str:
        return "<A>"


A = _A()


class ErrorTuple(NamedTuple):
    path: List[Any]
    value: Any
    description: str


class IsLike:
    """Result simulating a boolean value but also holding errors.

    >>> IsLike([])
    True
    >>> IsLike([(["path", "to", "error"], 5, "random error")])
    False

    """

    def __init__(self, errors: List[ErrorTuple]) -> None:
        self.errors = errors

    def __bool__(self):
        return not bool(self.errors)

    def raise_on_error(self):
        if not self.errors:
            return
        raise UnlikeError(errors=self.errors)

    def __repr__(self) -> str:
        return repr(bool(self))


class UnlikeError(AssertionError):
    """Raised when objects are not alike, according to an "Alike" comparison."""

    def __init__(self, msg: str = "", errors: List[ErrorTuple] = None) -> None:
        self.errors = [ErrorTuple(*e) for e in errors] if errors is not None else []
        super().__init__(msg + self._errors_to_str(self.errors))

    @staticmethod
    def _errors_to_str(errors: List[ErrorTuple]):
        if not errors:
            return ""
        return "Values not alike:\n" + "\n".join(
            [
                " -> ".join(repr(k) for k in e[0])
                + f" failed validation: {e[1]} does not match {e[2]}"
                for e in errors
            ]
        )


class Alike:
    def __init__(self, schema: Union[Mapping, Any]) -> None:
        self.schema = schema

    def is_alike(self, obj: Any) -> IsLike:
        errors = []
        schema = self.schema

        if isinstance(schema, List):
            if not isinstance(obj, Sequence) or isinstance(obj, str):
                return IsLike(
                    [ErrorTuple([], obj, "Compared object is not a sequence")]
                )
            # convert compared to dictionary for better comparison
            obj = {i: item for i, item in enumerate(obj)}
            schema = {i: item for i, item in enumerate(schema)}
        elif not isinstance(schema, Mapping):
            if schema == obj:
                return IsLike([])
            else:
                return IsLike([ErrorTuple([], obj, "Compared object is not equal")])

        for key, expected in schema.items():
            actual = _get(obj, key, MISSING)
            op = expected if isinstance(expected, Op) else (A == expected)
            if op(actual) is True:
                continue
            errors.append(ErrorTuple([key], actual, op.to_str(actual)))
        return IsLike(errors)

    def __eq__(self, obj: Any):
        return self.is_alike(obj)


def _get(obj: Any, key: Any, default=None, relax: bool = True) -> Any:
    try:
        return obj[key]
    except (KeyError, IndexError):
        if not relax:
            return default
        return getattr(obj, key, default)


def is_alike(actual: Union[Mapping, Sequence], expected: Any) -> IsLike:
    return Alike(expected).is_alike(actual)


def assert_alike(actual: Any, expected: Any) -> None:
    is_alike(actual, expected).raise_on_error()
