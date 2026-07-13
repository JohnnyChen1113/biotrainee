import unittest
from unittest import mock

import setup_shell_gpt


class PortableInstallTests(unittest.TestCase):
    @mock.patch.object(setup_shell_gpt, "_get_installed_package_version", return_value="1.5.1")
    @mock.patch.object(setup_shell_gpt, "_create_sgpt_wrapper")
    @mock.patch.object(setup_shell_gpt, "_verify_portable_shell_gpt", return_value=True)
    @mock.patch.object(setup_shell_gpt, "_run_with_spinner", return_value=True)
    @mock.patch.object(
        setup_shell_gpt,
        "get_pip_mirrors_sorted",
        return_value=[("测试镜像", "https://mirror.example/simple")],
    )
    def test_portable_install_explicitly_installs_click(
        self,
        _mirrors,
        run_with_spinner,
        verify_runtime,
        create_wrapper,
        _get_version,
    ):
        installed = setup_shell_gpt.install_shell_gpt_into_portable("/portable/python/bin/python3")

        self.assertTrue(installed)
        command = run_with_spinner.call_args.args[0]
        self.assertIn("click>=8.1,<9", command)
        self.assertIn("shell-gpt", command)
        verify_runtime.assert_called_once_with("/portable/python/bin/python3")
        create_wrapper.assert_called_once_with("/portable/python/bin/python3")

    @mock.patch.object(setup_shell_gpt, "_create_sgpt_wrapper")
    @mock.patch.object(setup_shell_gpt, "_verify_portable_shell_gpt", return_value=False)
    @mock.patch.object(setup_shell_gpt, "_run_with_spinner", return_value=True)
    @mock.patch.object(
        setup_shell_gpt,
        "get_pip_mirrors_sorted",
        return_value=[("测试镜像", "https://mirror.example/simple")],
    )
    def test_portable_install_rejects_unusable_runtime(
        self, _mirrors, _run_with_spinner, verify_runtime, create_wrapper
    ):
        installed = setup_shell_gpt.install_shell_gpt_into_portable("/portable/python/bin/python3")

        self.assertFalse(installed)
        verify_runtime.assert_called_once_with("/portable/python/bin/python3")
        create_wrapper.assert_not_called()


if __name__ == "__main__":
    unittest.main()
