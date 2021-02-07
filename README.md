![Build Status](https://img.shields.io/github/workflow/status/daviskirk/alike/CI?style=flat-square)
![Coverage Status](https://img.shields.io/codecov/c/github/daviskirk/alike/master?style=flat-square)
![PyPI version](https://img.shields.io/pypi/v/alike?style=flat-square)
![PyPI license](https://img.shields.io/pypi/l/alike?style=flat-square)
![PyPI pyversions](https://img.shields.io/pypi/pyversions/alike?style=flat-square)
![Code Style Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)


# ALIKE

**ALIKE** helps you test/validate your objects and datasctructures.

In many cases you will want to make sure that python object has certain properties but don't want to recreate the entire object to make sure they are exactly equal. Similary, if you don't just want to check one property of the object but lots of them, perhaps even tested properties, you can check every property, going through checks at each step to make sure that the comparison is valid and so on.

**ALIKE** allows you to do both with a consice API that allows you to express the comparisons you want to make, and leave out those that you don't!

# Usage

```pycon
>>> from alike import assert_alike, A
>>> assert_alike({
...     "direct": "foo",
...     "condition": 2,
...     "chaining": 5,
...     "missing": "here",
...     "sequences": [1, 2, 3],
...     "nested": {"cheese": "shop", "foo": ["b", "a", "r"]},
...     "attribute access": "abc",
...     "custom": ["a", "b"],
... }, {
...     "direct": "bar",
...     "condition": A > 3,
...     "chaining": (A > 5) & (A < 10),
...     "missing": A.is_missing,
...     "presence": A.is_present,
...     "sequences": [1, A > 3, 4],
...     "nested": {"cheese": "rabbit", "foo": (A.length > 2) & (A[0] == "x")},
...     "attribute access": A.endswith("d"),
...     "custom": lambda x=A: reversed(x) == ["b", "c"]
... })
Traceback (most recent call last):
    ...
alike.UnlikeError: Values not alike...
  'direct' failed validation: 'foo' causes error: 'foo' == 'bar'
  'condition' failed validation: 2 causes error: 2 > 3
  'chaining' failed validation: 5 causes error: (5 > 5) and (5 < 10)
  'missing' failed validation: 'here' causes error: value should be missing
  'presence' failed validation: <MISSING> causes error: value should be present
  'sequences' -> 1 failed validation: 2 causes error: 2 > 3
  'sequences' -> 2 failed validation: 3 causes error: 3 == 4
  'nested' -> 'cheese' failed validation: 'shop' causes error: 'shop' == 'rabbit'
  'nested' -> 'foo' failed validation: ['b', 'a', 'r'] causes error: ((len ['b', 'a', 'r']) > 2) and ((['b', 'a', 'r'][0]) == 'x')
  'attribute access' failed validation: 'abc' causes error: 'abc'.endswith('d')
  'custom' failed validation: ['a', 'b'] causes error: <lambda>(['a', 'b'])

```

For a complete set of examples, see the ``test_alike`` parametrizations in ``tests/test_alike.py``.

# Usage with pytest

**ALIKE** includes a pytest plugin so that "normal" assert statements are rewritten to have a nice output.

```python
from alike import Alike, is_alike, assert_alike

def test_alike():
    assert {"test": 1} == Alike({"test": 2})

def test_is_alike():
    assert is_alike({"test": 1}, {"test": 2})

def test_assert_alike():
    assert_alike({"test": 1}, {"test": 2})
```

Any of these tests will give an error message like:

```
E       AssertionError: assert Values not alike:
E         'test' failed validation: 1 causes error: 1 == 2
```

