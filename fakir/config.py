from __future__ import annotations

import os
from typing import Any, Dict, Optional

from . import pogo, screws
from .extract import DEFAULT_REF_PATTERN
from .model import DEFAULT_BOARD_NOTE_BOTTOM, DEFAULT_BOARD_NOTE_TOP

# Every setting there is, with the value config.yaml ships with.
DEFAULTS: Dict[str, Any] = {
    "pogo_pin": pogo.DEFAULT_KEY,
    "screw": screws.DEFAULT_KEY,
    "test_point_side": "B.Cu",
    "ref_pattern": DEFAULT_REF_PATTERN,
    "pcb": {
        "thickness": 1.6,
        "drill_hole_extra": pogo.CLEARANCE_MM,
        "note_top": DEFAULT_BOARD_NOTE_TOP,
        "note_bottom": DEFAULT_BOARD_NOTE_BOTTOM,
    },
    "holder": {
        "print_hole_allowance": 0.10,
        "threaded_inserts": True,
        "clamp": True,
        "clamp_tower_height": 15.0,
        "presser_cap_height": 20.0,
        "base_thickness": 3.0,
        "board_clearance": 0.40,
        "body_border": 2.5,
        "feet": True,
        "foot_height": 8.0,
    },
    "render": {
        "holder_format": "step,stl",
        "model_dir": "3dshapes",
    },
}


class ConfigError(ValueError):
    pass


def _check(values: Dict[str, Any], known: Dict[str, Any], prefix: str) -> None:
    for key, value in values.items():
        name = prefix + str(key)
        if key not in known:
            raise ConfigError("unknown setting %s" % name)
        if isinstance(known[key], dict) and value is not None:
            if not isinstance(value, dict):
                raise ConfigError("%s is a section, not a value" % name)
            _check(value, known[key], name + ".")


class Config:
    def __init__(self, values: Optional[Dict[str, Any]] = None,
                 path: Optional[str] = None):
        self.values = values or {}
        self.path = path
        _check(self.values, DEFAULTS, "")

    def get(self, key: str) -> Any:
        value, default = self.values, DEFAULTS
        for part in key.split("."):
            default = default[part]
            value = value.get(part) if isinstance(value, dict) else None
        return default if value is None else value

    def __repr__(self) -> str:
        return "Config(%r)" % (self.path or self.values)


def loads(text: str, path: Optional[str] = None) -> Config:
    try:
        import yaml
    except ImportError:
        raise ConfigError(
            "PyYAML is missing; run `uv sync` in fakir_tools") from None

    try:
        values = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError("%s: %s" % (path or "config", exc)) from None
    if not isinstance(values, dict):
        raise ConfigError("%s: expected a mapping" % (path or "config"))
    try:
        return Config(values, path)
    except ConfigError as exc:
        raise ConfigError("%s: %s" % (path or "config", exc)) from None


def load(path: str) -> Config:
    if not os.path.exists(path):
        raise ConfigError("%s does not exist" % path)
    with open(path, encoding="utf-8") as handle:
        return loads(handle.read(), path)
