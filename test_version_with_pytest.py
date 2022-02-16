import pytest

CHECK_OK = "OK"
CHECK_NOK = "NOK"
CHECK_ERROR = "ERROR"


def test_router_version(device_check):
    assert device_check["check_status"] == CHECK_OK


def test_dummy_test():
    assert True


def test_dummy_test_will_fail():
    assert False
