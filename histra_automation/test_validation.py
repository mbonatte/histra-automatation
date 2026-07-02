import unittest
import xml.etree.ElementTree as ET
from histra_automation.validation import validate_load_combinations, ValidationIssue

class TestValidation(unittest.TestCase):
    def test_exact_match(self):
        # XML containing matched combination and condition name
        xml_data = """
        <Root>
            <LoadCondition Id="11" Name="User1" />
            <LoadCombination Key="15" Name="User1">
                <Item ColumnKey="11" Val="1" />
            </LoadCombination>
            <Analysis Name="NewAnalysis" TypeLoadDistribution="LoadCombination" LoadCombinationKey="15" />
        </Root>
        """
        root = ET.fromstring(xml_data)
        issues = validate_load_combinations(root)
        self.assertEqual(issues, [])

    def test_missing_active_column_exact_match(self):
        xml_data = """
        <Root>
            <LoadCondition Id="11" Name="User1" />
            <LoadCombination Key="15" Name="User1">
                <Item ColumnKey="11" Val="0" />
            </LoadCombination>
            <Analysis Name="NewAnalysis" TypeLoadDistribution="LoadCombination" LoadCombinationKey="15" />
        </Root>
        """
        root = ET.fromstring(xml_data)
        issues = validate_load_combinations(root)
        self.assertTrue(any("has no active item for matching ColumnKey" in issue.message for issue in issues))

    def test_combination_suffix_match(self):
        xml_data = """
        <Root>
            <LoadCondition Id="11" Name="AppliedLoad" />
            <LoadCombination Key="15" Name="AppliedLoad_Combination">
                <Item ColumnKey="11" Val="1" />
            </LoadCombination>
            <Analysis Name="AppliedLoadAnalysis" TypeLoadDistribution="LoadCombination" LoadCombinationKey="15" />
        </Root>
        """
        root = ET.fromstring(xml_data)
        issues = validate_load_combinations(root)
        self.assertEqual(issues, [])

    def test_missing_active_column_suffix_match(self):
        xml_data = """
        <Root>
            <LoadCondition Id="11" Name="AppliedLoad" />
            <LoadCombination Key="15" Name="AppliedLoad_Combination">
                <Item ColumnKey="11" Val="0" />
            </LoadCombination>
            <Analysis Name="AppliedLoadAnalysis" TypeLoadDistribution="LoadCombination" LoadCombinationKey="15" />
        </Root>
        """
        root = ET.fromstring(xml_data)
        issues = validate_load_combinations(root)
        self.assertTrue(any("has no active item for matching ColumnKey" in issue.message for issue in issues))

    def test_case_insensitive_match(self):
        xml_data = """
        <Root>
            <LoadCondition Id="11" Name="appliedload" />
            <LoadCombination Key="15" Name="AppliedLoad_Combination">
                <Item ColumnKey="11" Val="1" />
            </LoadCombination>
            <Analysis Name="AppliedLoadAnalysis" TypeLoadDistribution="LoadCombination" LoadCombinationKey="15" />
        </Root>
        """
        root = ET.fromstring(xml_data)
        issues = validate_load_combinations(root)
        self.assertEqual(issues, [])

if __name__ == "__main__":
    unittest.main()
