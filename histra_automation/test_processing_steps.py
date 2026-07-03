import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from histra_automation.processing_steps import (
    _analysis_is_completed,
    _missing_required_analyses,
)


class TestAnalysisDependencies(unittest.TestCase):
    def test_missing_required_analyses_are_returned_in_dependency_order(self):
        root = ET.fromstring("""
        <Root>
            <Analysis Name="Vert" Key="1" InitialAnalysisKey="-100">
                <States><State State="NotExecutedNotToBeExecuted" /></States>
            </Analysis>
            <Analysis Name="1_scour" Key="23" InitialAnalysisKey="1">
                <States><State State="NotExecutedNotToBeExecuted" /></States>
            </Analysis>
            <Analysis Name="LiveLoad_1" Key="22" InitialAnalysisKey="23">
                <States><State State="NotExecutedNotToBeExecuted" /></States>
            </Analysis>
        </Root>
        """)

        self.assertEqual(
            _missing_required_analyses(root, "LiveLoad_1"),
            ["Vert", "1_scour"],
        )

    def test_completed_required_analysis_is_not_returned(self):
        root = ET.fromstring("""
        <Root>
            <Analysis Name="Vert" Key="1" InitialAnalysisKey="-100">
                <States><State State="ExecutedCompleted" /></States>
            </Analysis>
            <Analysis Name="1_scour" Key="23" InitialAnalysisKey="1">
                <States><State State="NotExecutedNotToBeExecuted" /></States>
            </Analysis>
        </Root>
        """)

        self.assertEqual(_missing_required_analyses(root, "1_scour"), [])

    def test_all_states_must_be_completed(self):
        analysis = ET.fromstring("""
        <Analysis Name="Vert" Key="1">
            <States>
                <State State="ExecutedCompleted" />
                <State State="NotExecutedNotToBeExecuted" />
            </States>
        </Analysis>
        """)

        self.assertFalse(_analysis_is_completed(analysis))

    def test_implicit_dependency_logs_warning(self):
        with patch("histra_automation.processing_steps.read_xml") as read_xml:
            from histra_automation.processing_steps import _analysis_run_queue

            read_xml.return_value = ET.fromstring("""
            <Root>
                <Analysis Name="Vert" Key="1" InitialAnalysisKey="-100">
                    <States><State State="NotExecutedNotToBeExecuted" /></States>
                </Analysis>
                <Analysis Name="LiveLoad_1" Key="22" InitialAnalysisKey="1">
                    <States><State State="NotExecutedNotToBeExecuted" /></States>
                </Analysis>
            </Root>
            """)

            with self.assertLogs("histra_automation.processing_steps", level="WARNING") as logs:
                queue = list(_analysis_run_queue("model.hrx", {"LiveLoad_1": {}}))

        self.assertEqual([name for name, _ in queue], ["Vert", "LiveLoad_1"])
        self.assertIn(
            "Analysis 'Vert' was set to run because it is required by analysis 'LiveLoad_1'",
            logs.output[0],
        )


if __name__ == "__main__":
    unittest.main()
