from concurrent.futures import ThreadPoolExecutor, as_completed
import json

import pytest
from _pytest.terminal import _get_line_with_reprcrash_message
from nso_restconf.restconf import RestConf

# don't put your credentials in the code use ENV variables instead
nso_api = RestConf(address="http://127.0.0.1", port=8080,
                   username="admin", password="admin")

CHECK_OK = "OK"
CHECK_NOK = "NOK"
CHECK_ERROR = "ERROR"


def router_version_check_data(target_version, devices_list) -> list:
    processes = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for device in devices_list:
            processes.append(executor.submit(nso_check_version, device, target_version))

    checks_list = []
    for task in as_completed(processes):
        result = task.result()["check_device:output"]
        checks_list.append(result)

    return checks_list


def nso_check_version(device, target_version):
    try:
        data = json.dumps({'input': {'device': f"{device}", "target_version": f"{target_version}"}})
        result = nso_api.action(data, "check_device/check_version")
        return result.json()
    except ConnectionError:
        return {"check_device:output": {"device": device, "check_status": CHECK_NOK,
                                        "check_message": f"Cannot connect to NSO to check {device}"}}


def pytest_addoption(parser):
    parser.addoption("--target-version", action="store", help="target version of the devices")
    parser.addoption("--devices-list-path", action="store", help="path to the devices list txt")


def pytest_generate_tests(metafunc):
    if "device_check" in metafunc.fixturenames:
        target_version = metafunc.config.getoption("--target-version", default=None)
        devices_list_path = metafunc.config.getoption("--devices-list-path", default=None)
        if devices_list_path:
            with open(devices_list_path) as devices_list_txt:
                devices_list = devices_list_txt.readlines()
                devices_list = [str(device).strip() for device in devices_list]
        if target_version and devices_list_path:
            check_list = router_version_check_data(target_version, devices_list)
            metafunc.parametrize("device_check", check_list)
        else:
            metafunc.parametrize("device_check", [])


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, 'extra', [])
    if report.when == 'call':
        device_check = item.funcargs.get('device_check', None)
        if device_check:
            extra.append(device_check["device"])
    report.extra = extra


import pytest
from _pytest.terminal import TerminalReporter


class MyReporter(TerminalReporter):
    def short_test_summary(self):
        self.write_sep("=", "short test summary info")
        failed = self.stats.get("failed", [])

        termwidth = self._tw.fullwidth
        config = self.config
        for rep in failed:
            line = _get_line_with_reprcrash_message(config, rep, termwidth)
            if hasattr(rep, "extra"):
                if rep.extra:
                    line = f" {line} for {rep.extra[0]}"
            self.write_line(line)


@pytest.mark.trylast
def pytest_configure(config):
    vanilla_reporter = config.pluginmanager.getplugin("terminalreporter")
    my_reporter = MyReporter(config)
    config.pluginmanager.unregister(vanilla_reporter)
    config.pluginmanager.register(my_reporter, "terminalreporter")
