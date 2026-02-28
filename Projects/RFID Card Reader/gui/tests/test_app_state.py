import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import OperationGuard

import pytest


def test_guard_starts_operation():
    g = OperationGuard()
    assert g.start("reading")
    assert g.is_busy
    assert g.operation == "reading"


def test_guard_blocks_second_operation():
    g = OperationGuard()
    g.start("reading")
    assert not g.start("writing")
    assert g.operation == "reading"


def test_guard_finish_allows_new_operation():
    g = OperationGuard()
    g.start("reading")
    g.finish()
    assert not g.is_busy
    assert g.start("writing")


def test_guard_timeout_resets():
    g = OperationGuard()
    g.start("reading")
    assert not g.check_timeout(29)
    assert g.check_timeout(30)
    assert not g.is_busy
