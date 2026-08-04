"""Tests for transactional MainLoop state transitions."""

import sys
import types

import pytest


if "RPi.GPIO" not in sys.modules:
    rpi_package = types.ModuleType("RPi")
    gpio_module = types.ModuleType("RPi.GPIO")
    rpi_package.GPIO = gpio_module
    sys.modules["RPi"] = rpi_package
    sys.modules["RPi.GPIO"] = gpio_module

if "rpi_ws281x" not in sys.modules:
    ws281x_module = types.ModuleType("rpi_ws281x")
    ws281x_module.Adafruit_NeoPixel = object
    ws281x_module.Color = lambda *args: args
    sys.modules["rpi_ws281x"] = ws281x_module

from MainLoop import MainLoop
from CamStates.state_names import StateName


class _Settings:
    def get_dict(self):
        return {}


class _State:
    def __init__(self, initialize_error=None):
        self.initialize_error = initialize_error
        self.cleanup_calls = 0
        self.initialize_calls = 0

    def cleanup(self):
        self.cleanup_calls += 1

    def initialize(self, settings):
        self.initialize_calls += 1
        if self.initialize_error:
            raise self.initialize_error


def test_failed_transition_restores_previous_state():
    """A target that cannot initialize must never become the active state."""
    loop = object.__new__(MainLoop)
    previous = _State()
    target = _State(RuntimeError("camera import failed"))
    loop._settings = _Settings()
    loop._hardware_config = {"CamChip": "PiCamHQ"}
    loop._initState = previous
    loop._currentstate = previous
    loop.states = {
        StateName.INIT: previous,
        StateName.POST: target,
    }

    with pytest.raises(RuntimeError, match="camera import failed"):
        loop.set_state(StateName.POST)

    assert loop._currentstate is previous
    assert previous.cleanup_calls == 1
    assert previous.initialize_calls == 1
    assert target.initialize_calls == 1


def test_successful_transition_commits_target_state():
    loop = object.__new__(MainLoop)
    previous = _State()
    target = _State()
    loop._settings = _Settings()
    loop._hardware_config = {}
    loop._initState = previous
    loop._currentstate = previous
    loop.states = {
        StateName.INIT: previous,
        StateName.POST: target,
    }

    loop.set_state(StateName.POST)

    assert loop._currentstate is target
    assert target.initialize_calls == 1
