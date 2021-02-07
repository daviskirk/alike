from alike import Alike, UnlikeError


def pytest_assertrepr_compare(op, left, right):
    if op == "==" and (
        errors := [
            error
            for obj in [left, right]
            if isinstance(obj, Alike)
            for error in obj.last_result.errors
        ]
    ):
        return UnlikeError._errors_to_str(errors).splitlines()
