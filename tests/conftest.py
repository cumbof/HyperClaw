"""
Shared pytest fixtures and utilities for HyperClaw skill tests.

Design notes
------------
* Each skill handler persists state to a .pkl file in the *current working
  directory*.  The ``tmp_state_dir`` fixture changes the cwd to a fresh
  temporary directory for every test, so tests are fully isolated.

* All 18 skills share the same handler *file name* (``handler.py``).  Using
  ``sys.path.insert`` for each skill would cause later ``from handler import X``
  calls to pick up the handler that was inserted *first*.  We therefore use
  ``importlib.util.spec_from_file_location`` to import each handler explicitly
  by its absolute file path — this avoids any sys.path pollution.

* The helper ``import_skill_handler(skill_name)`` is used by every test module.
"""

import importlib.util
import os
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def import_skill_handler(skill_name: str):
    """
    Import and return the handler module for the named skill using its
    absolute file path.  Multiple calls with the same skill_name return the
    same module object (cached by importlib).
    """
    handler_path = os.path.join(_REPO_ROOT, "skills", skill_name, "handler.py")
    module_name = f"skills.{skill_name}.handler"
    spec = importlib.util.spec_from_file_location(module_name, handler_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_state_dir(monkeypatch):
    """
    Change the working directory to a fresh temporary directory for the
    duration of a test.  Every skill handler resolves its STATE_FILE
    relative to the cwd, so this gives each test a clean slate with no
    risk of cross-test pollution.

    Yields the path of the temporary directory (str).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        yield tmpdir
