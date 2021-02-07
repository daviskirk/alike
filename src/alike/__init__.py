import inspect
import operator
from functools import wraps
from typing import (
    Any,
    Callable,
    List,
    Mapping,
    NamedTuple,
    Optional,
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
    >>> op._evaluate()
    'Alice: Hello Bob!'

    Replacements can be made of the special variable ``alike.A`` is used:
    >>> op = Op(lambda x, y: f"{x}: Hello {y}!", A, "Bob", symbol="talks to")
    >>> str(op)
    "<A> talks to 'Bob'"
    >>> op._evaluate("Carol")
    'Carol: Hello Bob!'

    Most comparison operators are supported
    >>> squared = Op(lambda x: x ** 2, A, symbol="squared")
    >>> op = (squared > 3) & (squared < 5)
    >>> op
    ((squared <A>) > 3) and ((squared <A>) < 5)
    >>> op._evaluate(1), op._evaluate(2), op._evaluate(3)
    (False, True, False)
    >>> op = (squared <= 1) | (squared >= 9)
    >>> op
    ((squared <A>) <= 1) or ((squared <A>) >= 9)
    >>> op._evaluate(1), op._evaluate(2), op._evaluate(3)
    (True, False, True)
    >>> op = (squared == 1) | (squared == 4)
    >>> op
    ((squared <A>) == 1) or ((squared <A>) == 4)
    >>> op._evaluate(1), op._evaluate(2), op._evaluate(3)
    (True, True, False)
    >>> op = ~(squared == 1) & ~(squared == 4)
    >>> op
    (not ((squared <A>) == 1)) and (not ((squared <A>) == 4))
    >>> op._evaluate(1), op._evaluate(2), op._evaluate(3)
    (False, False, True)

    """

    path: List[str]

    def __init__(
        self,
        op: Callable[..., Any],
        *args: Any,
        symbol: str = "",
        formatter: Optional[Callable[[List[str]], str]] = None,
        path: Optional[List[str]] = None,
    ) -> None:
        self.op = op
        self.args = args
        self.symbol = symbol or getattr(op, "__name__", "") or str(op)
        self.formatter = formatter
        self.path = path if path is not None else []

    def _to_str(self, a=NOTHING) -> str:
        if a is NOTHING:
            a = A

        def arg_to_str(arg: Any) -> str:
            if isinstance(arg, Op):
                return "(" + arg._to_str(a) + ")"
            elif isinstance(arg, _A):
                return repr(a)
            return repr(arg)

        arg_strings = [arg_to_str(arg) for arg in self.args]
        if self.formatter:
            return self.formatter(arg_strings)

        if len(self.args) != 1:
            pre_arg_str, post_arg_str = ", ".join(arg_strings[:1]), ", ".join(
                arg_strings[1:]
            )
        else:
            pre_arg_str, post_arg_str = "", ", ".join(arg_strings)

        return f"{pre_arg_str} {self.symbol} {post_arg_str}".strip()

    def __repr__(self) -> str:
        return self._to_str()

    def __getattr__(self, name: str) -> Any:
        return type(self)(
            operator.attrgetter(name),
            self,
            path=self.path + [name],
            formatter=lambda s: f"{s[0]}.{name}",
        )

    def __getitem__(self, name: str) -> Any:
        return Op(
            operator.itemgetter(name),
            self,
            path=self.path + [name],
            formatter=lambda s: f"{s[0].strip('()')}[{repr(name)}]",
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        path = self.path
        if path:
            path = path[:-1] + [path[-1] + _format_args(*args, **kwargs)]
        return type(self)(
            operator.methodcaller("__call__", *args, **kwargs),
            self,
            path=path,
            formatter=lambda s: s[0].strip("()") + _format_args(*args, **kwargs),
        )

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

    def is_alike(self: OT, b: Any) -> OT:
        return type(self)(is_alike, self, b, path=self.path)

    def _evaluate(self, a: Any = NOTHING, path=None) -> Any:
        if path is None:
            path = []
        args = [
            arg._evaluate(a) if isinstance(arg, (Op, _A)) else arg for arg in self.args
        ]
        result = self.op(*args)
        if isinstance(result, IsLike):
            for error in result.errors:
                error.path[:0] = path + self.path  # prepend passed path
        return result


def _get_is_like_errors(a, b):
    errors = []
    for item in [a, b]:
        if isinstance(item, IsLike):
            errors.extend(item.errors)
    return errors


def _apply_and(a, b, /) -> Union[bool, "IsLike"]:
    result = bool(a and b)
    if result:
        return result
    errors = _get_is_like_errors(a, b)
    if errors:
        return IsLike(errors=errors)
    return result


def _apply_or(a, b, /) -> Union[bool, "IsLike"]:
    result = bool(a or b)
    if result:
        return result
    errors = _get_is_like_errors(a, b)
    if errors:
        return IsLike(errors=errors)
    return result


def _format_args(*args, **kwargs) -> str:
    s = ""
    if args:
        s += ", ".join(repr(arg) for arg in args)
        if kwargs:
            s += ", "
    if kwargs:
        s += ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
    return f"({s})"


class _A:
    """Placeholder object for delayed comparison of values.

    >>> op = (A < 10) | (A > 20)
    >>> op._evaluate(5)
    True
    >>> op._evaluate(30)
    True
    >>> op._evaluate(15)
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

    def __invert__(self) -> Op:
        return Op(operator.not_, self, symbol="not")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return Op(
            operator.methodcaller("__call__", *args, **kwargs),
            self,
            formatter=lambda s: s[0].strip("()") + _format_args(*args, **kwargs),
        )

    def __getattr__(self, name: str) -> Any:
        return Op(
            operator.attrgetter(name),
            self,
            path=[name],
            formatter=lambda s: f"{s[0].strip('()')}.{name}",
        )

    def __getitem__(self, name: str) -> Any:
        return Op(
            operator.itemgetter(name),
            self,
            path=[name],
            formatter=lambda s: f"{s[0].strip('()')}[{repr(name)}]",
        )

    def __bool__(self):
        raise TypeError(
            "Operator cannot be truthy or falsy before evaluating. "
            "Most likely you have chained operators that cannot be chained."
        )

    def apply(self, callback: Callable[[Any], Any]):
        return Op(
            callback,
            self,
            path=[callback.__name__],
            formatter=lambda s: f"{callback.__name__}({', '.join(s)})",
        )

    @property
    def length(self) -> Op:
        return Op(len, self, symbol="len")

    @property
    def is_falsy(self) -> Op:
        return Op(operator.not_, self, symbol="not")

    @property
    def is_missing(self) -> Op:
        return Op(
            operator.is_,
            self,
            MISSING,
            formatter=lambda s: "value should be missing",
        )

    @property
    def is_present(self) -> Op:
        return Op(
            operator.is_not,
            self,
            MISSING,
            formatter=lambda s: "value should be present",
        )

    def is_alike(self, b: Any) -> Op:
        return Op(is_alike, self, b, path=self.path)

    def isinstance(self, types: Union[type, Tuple[type, ...]]) -> Op:
        return Op(isinstance, self, types)

    def __repr__(self) -> str:
        return "<A>"

    def _evaluate(self, value: T, path=None) -> T:
        return value


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

    def __init__(self, errors: Sequence[ErrorTuple] = ()) -> None:
        self.errors = list(errors)

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
                "  "
                + " -> ".join(repr(k) for k in e[0])
                + f" failed validation: {repr(e[1])} causes error: {e[2]}"
                for e in errors
            ]
        )


class ComparisonComplete(Exception):
    """Raised when comparison is complete."""


class Alike:
    def __init__(self, schema: Union[Mapping[Union[str, int], Any], Any]) -> None:
        self.schema = schema
        self.last_result: IsLike = IsLike()

    def __eq__(self, obj: Any):
        return self.is_alike(obj)

    def is_alike(self, obj: Any) -> IsLike:
        errors = self._is_alike(self.schema, obj)
        self.last_result = IsLike(errors)
        return IsLike(errors)

    def raise_on_error(self) -> None:
        self.last_result.raise_on_error()

    @classmethod
    def _is_alike(
        cls, schema: Union[Mapping, Any], obj: Any, path: Sequence[Union[str, int]] = ()
    ) -> List[ErrorTuple]:
        errors = []
        path = list(path)

        if isinstance(schema, Mapping):
            # we don't need to modify preprocess mappings
            pass
        elif isinstance(schema, List):
            # we can handle lists but we need to ensure that the compared
            # object is a sequence to be able to compare them
            if not isinstance(obj, Sequence) or isinstance(obj, str):
                errors.append(
                    ErrorTuple(path, obj, "Compared object is not a sequence")
                )
                return errors
            # convert compared to dictionary for better comparison
            obj = {i: item for i, item in enumerate(obj)}
            schema = {i: item for i, item in enumerate(schema)}
        else:
            if schema != obj:
                errors.append(ErrorTuple(path, obj, "Compared object is not equal"))
            return errors

        for key, expected in schema.items():
            actual = _get(obj, key, MISSING)

            if isinstance(expected, (dict, list)):
                # we recursively parse errors if there are nested dictionaries/lists
                errors.extend(cls._is_alike(expected, actual, path=path + [key]))
                continue
            elif isinstance(expected, Op):
                op = expected
            elif callable(expected) and (f := _get_applyable(expected)):
                op = A.apply(f)
            else:
                op = A == expected

            evaluated = op._evaluate(actual, path=path + [key])

            if evaluated is True:
                pass
            elif isinstance(evaluated, IsLike) and not evaluated:
                for error in evaluated.errors:
                    errors.append(error)
            else:
                # All other values are assumed to be errors
                errors.append(ErrorTuple(path + [key], actual, op._to_str(actual)))

        return errors


def _get_applyable(f: Callable[..., Any]) -> Optional[Callable[[Any], bool]]:
    """Consolidate a function that uses ``A`` as a default into an applyable function.

    If no ``A`` objects exist as default values, ``None`` is returned instead
    of a consolidated function.
    """
    keys = {
        k
        for k, v in inspect.signature(f).parameters.items()
        if isinstance(v.default, _A) or k == "A"
    }
    if not keys:
        return None

    @wraps(f)
    def custom_validation_fcn(x):
        return f(**{k: x for k in keys})

    return custom_validation_fcn


def _get(obj: Any, key: Any, default=None, relax: bool = True) -> Any:
    try:
        return obj[key]
    except (KeyError, IndexError, TypeError):
        if not relax:
            return default
        return getattr(obj, key, default)


def is_alike(actual: Union[Mapping, Sequence], expected: Any) -> IsLike:
    return Alike(expected).is_alike(actual)


def assert_alike(actual: Any, expected: Any) -> None:
    is_alike(actual, expected).raise_on_error()
