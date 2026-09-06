import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SETUP_PATH = Path(__file__).resolve().parents[1] / "setup.py"


def load_setup_module():
    numpy_module = types.ModuleType("numpy")
    numpy_module.get_include = lambda: "/tmp/numpy"

    cython_module = types.ModuleType("Cython")
    cython_build_module = types.ModuleType("Cython.Build")
    cython_build_module.cythonize = lambda *args, **kwargs: []
    cython_module.Build = cython_build_module

    setuptools_module = types.ModuleType("setuptools")
    setuptools_module.find_packages = lambda **kwargs: []
    setuptools_module.setup = lambda **kwargs: None

    setuptools_command_module = types.ModuleType("setuptools.command")
    setuptools_build_ext_module = types.ModuleType("setuptools.command.build_ext")

    class DummyBuildExt:
        def build_extensions(self):
            return None

    setuptools_build_ext_module.build_ext = DummyBuildExt
    setuptools_command_module.build_ext = setuptools_build_ext_module

    modules = {
        "numpy": numpy_module,
        "Cython": cython_module,
        "Cython.Build": cython_build_module,
        "setuptools": setuptools_module,
        "setuptools.command": setuptools_command_module,
        "setuptools.command.build_ext": setuptools_build_ext_module,
    }

    spec = importlib.util.spec_from_file_location("hummingbot_setup", SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


class SetupPyTests(unittest.TestCase):
    def test_build_ext_does_not_force_parallel_on_posix(self):
        module = load_setup_module()
        setup_calls = []
        observed_argv = []

        with patch.object(module, "find_packages", return_value=[]), \
                patch.object(module, "cythonize", return_value=[]), \
                patch.object(module, "setup", side_effect=lambda **kwargs: (observed_argv.extend(sys.argv), setup_calls.append(kwargs))), \
                patch.object(module.os, "cpu_count", return_value=8), \
                patch.object(module.subprocess, "check_output", return_value=b"Linux"), \
                patch("sys.argv", ["setup.py", "build_ext"]):
            module.main()

        self.assertTrue(setup_calls)
        self.assertEqual(["setup.py", "build_ext"], observed_argv)


if __name__ == "__main__":
    unittest.main()
