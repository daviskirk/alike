from contextlib import contextmanager

import pytest
from pytest import param

from alike import MISSING, A, ErrorTuple, assert_alike, is_alike


@contextmanager
def no_error():
    yield


def raises(errors):
    if errors is None:
        return no_error()
    return pytest.raises(errors)


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
            id="'not' error",
        ),
        param({"test": ""}, {"test": A.is_falsy}, None, id="is falsy"),
        param(
            {"test": "s"},
            {"test": A.is_falsy},
            [(["test"], "s", "not 's'")],
            id="is falsy error",
        ),
        param({"test": "test"}, {"test": A == "test"}, None, id="== with string"),
        param(
            {"test": 1}, {"test": 1, "missing": A.is_missing}, None, id="key missing"
        ),
        param({"test": 1}, {"test": A.is_present}, None, id="key present"),
        param(
            {"test": 1},
            {"test": 1, "missing": A.is_present},
            [(["missing"], MISSING, "<MISSING> value should not be <MISSING>")],
            id="expected key missing error",
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
            id="missing with or 1",
        ),
        param({}, {"test": A.is_missing | (A == 10)}, None, id="missing with or 1"),
        param({"test": 10}, {"test": (A > 20) | (A < 12)}, None, id="OR expression 1"),
        param({"test": 25}, {"test": (A > 20) | (A < 12)}, None, id="OR expression 2"),
        param(
            {"test": 15},
            {"test": (A > 20) | (A < 12)},
            [(["test"], 15, "(15 > 20) or (15 < 12)")],
            id="OR expression with error",
        ),
        param({"test": 25}, {"test": (A > 20) & (A < 30)}, None, id="AND expression"),
        param(
            {"test": 20},
            {"test": (20 < A) & (A < 30)},
            [(["test"], 20, "(20 > 20) and (20 < 30)")],
            id="AND expression error",
        ),
        param(
            {"test": 1},
            {"test": 2},
            [(["test"], 1, "1 == 2")],
            id="simple equality error",
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
            [(["test"], [5, 6, 7], "(<lambda> [5, 6, 7]) > 4")],
            id="lambda error",
        ),
        param(5, 5, None, id="direct comparison"),
        param(5, 6, [([], 5, "Compared object is not equal")], id="direct comparison"),
        param([5, 6, 7], [5, A < 7, A > 6], None, id="list comparison"),
        param(
            [5, 6, 7],
            [5, A < 6, A > 7],
            [([1], 6, "6 < 6"), ([2], 7, "7 > 7")],
            id="list comparison error",
        ),
        param(
            6,
            [5, A < 6, A > 7],
            [([], 6, "Compared object is not a sequence")],
            id="list comparison type error",
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
            "'one' failed validation: 1 does not match 1 == 2\n"
            "'two' failed validation: 2 does not match 2 == 'two'"
        ),
    ):
        assert_alike({"one": 1, "two": 2}, {"one": 2, "two": "two"})
