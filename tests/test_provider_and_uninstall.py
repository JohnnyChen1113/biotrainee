import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import setup_shell_gpt


class ProviderConfigurationTests(unittest.TestCase):
    def test_deepseek_v4_pro_is_siliconflow_default(self):
        self.assertEqual(
            setup_shell_gpt.SILICONFLOW_DEFAULT_MODEL,
            "deepseek-ai/DeepSeek-V4-Pro",
        )
        self.assertEqual(
            setup_shell_gpt.ALLOWED_MODELS[0],
            setup_shell_gpt.SILICONFLOW_DEFAULT_MODEL,
        )
        self.assertEqual(
            setup_shell_gpt.select_default_model([]),
            setup_shell_gpt.SILICONFLOW_DEFAULT_MODEL,
        )

    def test_custom_provider_keeps_complete_base_url_and_model(self):
        with redirect_stdout(io.StringIO()):
            provider = setup_shell_gpt.choose_api_provider(
                provider_choice="custom",
                api_base_url="https://api.openai.com/v1/",
                model="gpt-5",
            )

        self.assertIsNotNone(provider)
        self.assertEqual(provider.api_base_url, "https://api.openai.com/v1")
        self.assertEqual(provider.default_model, "gpt-5")
        self.assertFalse(provider.is_siliconflow)

    @mock.patch.object(setup_shell_gpt, "create_config_file")
    @mock.patch.object(setup_shell_gpt, "install_shell_gpt", return_value=True)
    @mock.patch.object(setup_shell_gpt, "get_available_models_cached")
    def test_custom_install_skips_siliconflow_model_probe(
        self, get_models, _install_shell_gpt, create_config
    ):
        provider = setup_shell_gpt.ApiProvider(
            name="api.openai.com",
            api_base_url="https://api.openai.com/v1",
            default_model="gpt-5",
            is_siliconflow=False,
        )

        with redirect_stdout(io.StringIO()):
            installed = setup_shell_gpt.auto_install("sk-test-key", provider)

        self.assertTrue(installed)
        get_models.assert_not_called()
        create_config.assert_called_once_with(
            "sk-test-key", "gpt-5", "https://api.openai.com/v1"
        )


class UninstallTests(unittest.TestCase):
    def test_uninstall_cli_skips_path_setup_and_forwards_yes(self):
        with mock.patch.object(sys, "argv", ["setup_shell_gpt.py", "--uninstall", "--yes"]):
            with mock.patch.object(setup_shell_gpt, "_ensure_local_bin_in_path") as ensure_path:
                with mock.patch.object(
                    setup_shell_gpt, "uninstall_shell_gpt", return_value=True
                ) as uninstall:
                    with redirect_stdout(io.StringIO()):
                        result = setup_shell_gpt.main()

        self.assertTrue(result)
        ensure_path.assert_not_called()
        uninstall.assert_called_once_with(assume_yes=True)

    @mock.patch.object(setup_shell_gpt, "_remove_managed_path_exports", return_value=[])
    @mock.patch.object(
        setup_shell_gpt.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 0, "", ""),
    )
    def test_assume_yes_removes_directories_and_wrapper_file(self, _run, _remove_path):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            portable_dir = root / "portable"
            portable_dir.mkdir()
            (portable_dir / "python").write_text("runtime")
            wrapper = root / "sgpt"
            wrapper.write_text("#!/bin/bash\n")

            targets = [("Portable Python", portable_dir), ("sgpt 包装脚本", wrapper)]
            with mock.patch.object(setup_shell_gpt, "_get_cleanup_targets", return_value=targets):
                with redirect_stdout(io.StringIO()):
                    removed = setup_shell_gpt.uninstall_shell_gpt(assume_yes=True)

            self.assertTrue(removed)
            self.assertFalse(portable_dir.exists())
            self.assertFalse(wrapper.exists())


if __name__ == "__main__":
    unittest.main()
