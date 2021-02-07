from contextlib import contextmanager

import pytest
from pytest import param

from alike import MISSING, A, Alike, ErrorTuple, assert_alike, is_alike


@contextmanager
def no_error():
    yield


def raises(errors):
    if errors is None:
        return no_error()
    return pytest.raises(errors)


class _Dummy:
    def __call__(self, x):
        return True

    def __repr__(self) -> str:
        return "dummy callable"


_dummy = _Dummy()


class Summer:
    def sum(self, a, b):
        return a + b

    def __repr__(self) -> str:
        return "<Summer>"


_summer = Summer()


@pytest.mark.parametrize(
    "actual,compared,errors",
    [
        param({}, {}, None, id="Empty"),
        param({"test": 1}, {"test": 1}, None, id="Simple equality"),
        param({"test": "test"}, {"test": "test"}, None, id="Simple equality"),
        param({"test": None}, {"test": None}, None, id="eq with None"),
        param({"test": 10}, {"test": A == 10}, None, id="== with number"),
        param({"test": ""}, {"test": ~A}, None, id="not"),
        param(
            {"test": "s"},
            {"test": ~A},
            [(["test"], "s", "not 's'")],
            id="'not'-error",
        ),
        param({"test": ""}, {"test": A.is_falsy}, None, id="is falsy"),
        param(
            {"test": "s"},
            {"test": A.is_falsy},
            [(["test"], "s", "not 's'")],
            id="is-falsy-error",
        ),
        param({"test": "test"}, {"test": A == "test"}, None, id="== with string"),
        param(
            {"test": 1}, {"test": 1, "missing": A.is_missing}, None, id="key missing"
        ),
        param({"test": 1}, {"test": A.is_present}, None, id="key present"),
        param(
            {"test": 1},
            {"test": 1, "missing": A.is_present},
            [(["missing"], MISSING, "value should be present")],
            id="expected-key-missing-error",
        ),
        param({"test": 10}, {"test": A > 5}, None, id=">"),
        param({"test": 10}, {"test": A >= 5}, None, id=">="),
        param({"test": 5}, {"test": A <= 5}, None, id="<="),
        param({"test": 3}, {"test": A < 5}, None, id="<"),
        param(
            {"test": 10}, {"test": A > 15}, [(["test"], 10, "10 > 15")], id="> error"
        ),
        # or equals
        param(
            {"test": 10},
            {"test": A.is_missing | (A == 10)},
            None,
            id="missing-with-or-1",
        ),
        param({}, {"test": A.is_missing | (A == 10)}, None, id="missing with or 1"),
        param({"test": 10}, {"test": (A > 20) | (A < 12)}, None, id="OR expression 1"),
        param({"test": 25}, {"test": (A > 20) | (A < 12)}, None, id="OR expression 2"),
        param(
            {"test": 15},
            {"test": (A > 20) | (A < 12)},
            [(["test"], 15, "(15 > 20) or (15 < 12)")],
            id="OR-expression-with-error",
        ),
        param({"test": 25}, {"test": (A > 20) & (A < 30)}, None, id="AND expression"),
        param(
            {"test": 20},
            {"test": (20 < A) & (A < 30)},
            [(["test"], 20, "(20 > 20) and (20 < 30)")],
            id="AND-expression-error",
        ),
        param(
            {"test": 1},
            {"test": 2},
            [(["test"], 1, "1 == 2")],
            id="simple-equality-error",
        ),
        param({"test": [5, 6, 7]}, {"test": A.length > 2}, None),
        param(
            {"test": [5, 6, 7]},
            {"test": A.length > 4},
            [(["test"], [5, 6, 7], "(len [5, 6, 7]) > 4")],
        ),
        param(
            {"test": [5, 6, 7]},
            {"test": A.apply(lambda a: len(a)) > 2},
            None,
            id="lambda",
        ),
        param(
            {"test": [5, 6, 7]},
            {"test": A.apply(lambda a: len(a)) > 4},
            [(["test"], [5, 6, 7], "(<lambda>([5, 6, 7])) > 4")],
            id="lambda-error",
        ),
        param(5, 5, None, id="direct comparison"),
        param(5, 6, [([], 5, "Compared object is not equal")], id="direct comparison"),
        param([5, 6, 7], [5, A < 7, A > 6], None, id="list comparison"),
        param(
            [5, 6, 7],
            [5, A < 6, A > 7],
            [([1], 6, "6 < 6"), ([2], 7, "7 > 7")],
            id="list-comparison-error",
        ),
        param(
            6,
            [5, A < 6, A > 7],
            [([], 6, "Compared object is not a sequence")],
            id="list-comparison-type-error",
        ),
        param(
            {"test": 1, "nested": {"test2": 2}},
            {"test": 1, "nested": {"test2": 2}},
            [],
            id="nested-dict-schema",
        ),
        param(
            {"test": 1, "nested": {"test2": 2}},
            {"test": 1, "nested": {"test2": A == 2}},
            [],
            id="nested-dict-schema-using-A",
        ),
        param(
            {"test": 1, "nested": {"test2": 2}},
            {"test": 1, "nested": {"test2": A == 3}},
            [(["nested", "test2"], 2, "2 == 3")],
            id="nested-dict-schema-error",
        ),
        param(
            {
                "top": "ok",
                "test": 1,
                "before": "ok",
                "nested": {"test2": 2},
                "after": "ok",
                "after_broken": "boom!",
            },
            {
                "top": "ok",
                "test": A == 2,
                "before": "ok",
                "nested": {"test2": A == 1},
                "after": "ok",
                "after_broken": "yeah!",
            },
            [
                (["test"], 1, "1 == 2"),
                (["nested", "test2"], 2, "2 == 1"),
                (["after_broken"], "boom!", "'boom!' == 'yeah!'"),
            ],
            id="nested-dict-schema-error-on-multiple-levels",
        ),
        param(
            [1, [1, 2, 3], 3],
            [1, [1, A == 2, 3], A == 3],
            None,
            id="nested-list-schema",
        ),
        param(
            [1, [1, 2, 3], 3],
            [1, [1, A == 3, 3], A == 3],
            [([1, 1], 2, "2 == 3")],
            id="nested-list-schema-error",
        ),
        param(
            [1, [1, 2, 3], 3],
            [1, A.isinstance(list) & (A.length == 3), A == 3],
            None,
            id="list-schema-checking-inner-list",
        ),
        param(
            {"test": 5, "test2": "foobar"},
            {"test": lambda A: A == 5, "test2": lambda x=A: x == "foobar"},
            None,
            id="applyable-function",
        ),
        param(
            {"test": 5},
            {"test": _dummy},
            [(["test"], 5, "5 == dummy callable")],
            id="test-unapplyable-error",
        ),
        param(
            {"test": {"l1": {"a": 1, "b": 2}}},
            {"test": lambda x=A: is_alike(x["l1"], {"a": 2, "b": 3})},
            [
                (["test", "<lambda>", "a"], 1, "1 == 2"),
                (["test", "<lambda>", "b"], 2, "2 == 3"),
            ],
            id="nested-alike",
        ),
        param(
            {"test": {"l1": {"l2": {"a": 1, "b": 2}}}},
            {"test": A.is_present & (A["l1"].get("l2").is_alike({"a": 2, "b": 3}))},
            [
                (["test", "l1", "get('l2')", "a"], 1, "1 == 2"),
                (["test", "l1", "get('l2')", "b"], 2, "2 == 3"),
            ],
            id="nested-chained-alike",
        ),
        param(
            {"test": _summer},
            {"test": {"sum": A(3, 5) == 8}},
            [],
            id="callable",
        ),
        param(
            {"test": _summer},
            {"test": {"sum": A(3, 5) == 7}},
            [
                (
                    ["test", "sum"],
                    _summer.sum,
                    "(<bound method Summer.sum of <Summer>>(3, 5)) == 7",
                )
            ],
            id="callable-error",
        ),
        param(
            {"test": _summer},
            {"test": A.sum(3, 5) == 8},
            [],
            id="attrgetter-callable",
        ),
        param(
            {"test": _summer},
            {"test": A.sum(3, 5) == 7},
            [(["test"], _summer, "(<Summer>.sum(3, 5)) == 7")],
            id="attrgetter-callable-error",
        ),
        param(
            {"test": {"a": {"b": 5}}},
            {"test": A["a"]["b"] == 5},
            [],
            id="itemgetter-callable",
        ),
        param(
            {"test": {"a": {"b": 5}}},
            {"test": A["a"]["b"] == 6},
            [(["test"], {"a": {"b": 5}}, r"({'a': {'b': 5}}['a']['b']) == 6")],
            id="itemgetter-callable-error",
        ),
    ],
)
def test_alike(actual, compared, errors):
    result = is_alike(actual, compared)
    if errors:
        assert not result
        expected_errors = [ErrorTuple(*e) for e in errors]
        assert result.errors == expected_errors
    else:
        assert result, getattr(result, "errors", "Something went wrong")


def test_assert_alike():
    assert_alike({"one": 1, "two": 2}, {"one": 1, "two": 2})
    with pytest.raises(
        AssertionError,
        match=(
            "Values not alike:\n"
            "  'one' failed validation: 1 causes error: 1 == 2\n"
            "  'two' failed validation: 2 causes error: 2 == 'two'"
        ),
    ):
        assert_alike({"one": 1, "two": 2}, {"one": 2, "two": "two"})


expected_error_match = """
assert Values not alike:
    'bar' -> 'rabbit' -> 1 failed validation: 'knight' causes error: 'knight' == 'wrong'
    'bar' -> 'other' failed validation: 'oops' causes error: value should be missing$
""".strip()


def test_example():
    """Test example from README."""
    with pytest.raises(
        AssertionError,
        match=expected_error_match,
    ):
        actual = {
            "test1": 1,
            "test2": "foo",
            "bar": {"cheese": "parrot", "rabbit": ["black", "knight"], "other": "oops"},
        }
        assert actual == Alike(
            {
                "something": A.is_missing,
                "test2": "foo",
                "test1": A < 2,
                "bar": {
                    "cheese": A.is_present,
                    "rabbit": ["black", "wrong"],
                    "other": A.is_missing,
                },
            }
        )
