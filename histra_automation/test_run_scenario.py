import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from histra_automation.run_scenario import run_scenario


class TestRunScenarioCleanup(unittest.TestCase):
    def test_cleanup_deletes_temporary_model_files_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "model.hrx"
            xml_file = Path(temp_dir) / "model_copy_1.hrx"
            results_file = Path(temp_dir) / "model_copy_1.Results"

            input_path.write_text("base")
            xml_file.write_text("copy")
            results_file.write_text("results")

            self._run_with_mocked_steps(input_path)

            self.assertFalse(xml_file.exists())
            self.assertFalse(results_file.exists())

    def test_cleanup_can_be_disabled_to_keep_temporary_model_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "model.hrx"
            xml_file = Path(temp_dir) / "model_copy_1.hrx"
            results_file = Path(temp_dir) / "model_copy_1.Results"

            input_path.write_text("base")
            xml_file.write_text("copy")
            results_file.write_text("results")

            self._run_with_mocked_steps(input_path, cleanup=False)

            self.assertTrue(xml_file.exists())
            self.assertTrue(results_file.exists())

    def _run_with_mocked_steps(self, input_path, **kwargs):
        with (
            patch("histra_automation.run_scenario.pre_processing"),
            patch("histra_automation.run_scenario.processing"),
            patch("histra_automation.run_scenario.pos_processing"),
            patch("histra_automation.run_scenario.time.sleep"),
        ):
            run_scenario(str(input_path), {}, 0, **kwargs)


if __name__ == "__main__":
    unittest.main()
