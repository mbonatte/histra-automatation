import logging
import unittest
from xml.etree import ElementTree as ET

from modelxml.mutations import (
    _select_outside_delta_interfaces,
    add_line_load,
    add_line_load_definition,
    create_load_combination,
    create_load_condition,
)


def _interface(key, x, y, z=0.0):
    point = f"{x};{y};{z}"
    return {
        "Key": key,
        "VInt3D1": point,
        "VInt3D2": point,
        "VInt3D3": point,
        "VInt3D4": point,
    }


class TestScourInterfaceSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.location = (0.0, 10.0, 100.0, 20.0, -5.0)
        self.interfaces = [
            _interface("left", -40.0, 10.0),
            _interface("middle", 0.0, 10.0),
            _interface("right", 40.0, 10.0),
            _interface("upstream", 0.0, 2.0),
            _interface("downstream", 0.0, 18.0),
        ]

    def test_uniform_selects_both_length_ends(self):
        self.assertEqual(
            _select_outside_delta_interfaces(self.interfaces, self.location, 0.5),
            ["left", "right"],
        )

    def test_left_selects_left_bank_length_zone(self):
        self.assertEqual(
            _select_outside_delta_interfaces(
                self.interfaces,
                self.location,
                0.25,
                mode="left",
            ),
            ["left"],
        )

    def test_right_selects_right_bank_length_zone(self):
        self.assertEqual(
            _select_outside_delta_interfaces(
                self.interfaces,
                self.location,
                0.25,
                mode="right",
            ),
            ["right"],
        )

    def test_upstream_selects_width_zone_relative_to_pier_origin(self):
        self.assertEqual(
            _select_outside_delta_interfaces(
                self.interfaces,
                self.location,
                0.25,
                mode="upstream",
            ),
            ["upstream"],
        )

    def test_downstream_selects_width_zone_relative_to_pier_origin(self):
        self.assertEqual(
            _select_outside_delta_interfaces(
                self.interfaces,
                self.location,
                0.25,
                mode="downstream",
            ),
            ["downstream"],
        )

    def test_invalid_mode_names_supported_modes(self):
        with self.assertRaisesRegex(ValueError, "upstream.*downstream"):
            _select_outside_delta_interfaces(
                self.interfaces,
                self.location,
                0.25,
                mode="diagonal",
            )


class TestCreateLoadCondition(unittest.TestCase):
    def test_copies_last_load_condition_and_increments_identifiers(self):
        root = ET.fromstring("""
            <HiStrA>
                <LoadCondition Id="11" Name="Load_Condition_1" Description="Load_Condition_1" Action="3" />
                <LoadCondition Id="12" Name="Load_Condition_2" Description="Load_Condition_2" Action="3" />
            </HiStrA>
        """)

        create_load_condition(root)

        load_condition = root.findall("LoadCondition")[-1]
        self.assertEqual(load_condition.get("Id"), "13")
        self.assertEqual(load_condition.get("Name"), "Load_Condition_3")
        self.assertEqual(load_condition.get("Description"), "Load_Condition_3")
        self.assertEqual(load_condition.get("Action"), "3")

    def test_adds_inactive_column_to_each_combination_row(self):
        root = ET.fromstring("""
            <HiStrA>
                <LoadCondition Id="11" Name="Load_Condition_1" />
                <LoadCondition Id="12" Name="Load_Condition_2" />
                <LoadCombination Key="6" Name="SEISMIC">
                    <Item LoadCombinationKey="6" ColumnKey="11" RowKey="1" Val="1" />
                    <Item LoadCombinationKey="6" ColumnKey="12" RowKey="1" Val="1" />
                    <Item LoadCombinationKey="6" ColumnKey="11" RowKey="2" Val="1" />
                    <Item LoadCombinationKey="6" ColumnKey="12" RowKey="2" Val="1" />
                </LoadCombination>
            </HiStrA>
        """)

        create_load_condition(root)

        columns = [
            (item.get("RowKey"), item.get("ColumnKey"), item.get("Val"))
            for item in root.find("LoadCombination").findall("Item")
        ]
        self.assertEqual(
            columns,
            [("1", "11", "1"), ("1", "12", "1"), ("1", "13", "0"),
             ("2", "11", "1"), ("2", "12", "1"), ("2", "13", "0")],
        )


class TestAddLineLoadDefinition(unittest.TestCase):
    def test_copies_last_vertical_line_load_for_new_load_condition(self):
        root = ET.fromstring("""
            <HiStrA>
                <LoadCondition Id="11" Name="Load_Condition_1" Description="Load_Condition_1" />
                <LoadCondition Id="12" Name="Load_Condition_2" Description="Load_Condition_2" />
                <Template Key="147" Name="VERTICAL_APPLIED_LOAD_1" PurposeType="LineLoad">
                    <LoadtemplateItemList>
                        <LoadTemplateItem IdLoadTemplate="147" IdLoadCondition="11" />
                    </LoadtemplateItemList>
                </Template>
                <Template Key="148" Name="VERTICAL_APPLIED_LOAD_2" PurposeType="LineLoad">
                    <LoadtemplateItemList>
                        <LoadTemplateItem IdLoadTemplate="148" IdLoadCondition="12" />
                    </LoadtemplateItemList>
                </Template>
                <Template Key="200" Name="Other" />
            </HiStrA>
        """)

        self.assertEqual(add_line_load_definition(root), "201")

        load_condition = root.findall("LoadCondition")[-1]
        line_load = root.findall("Template")[-1]
        item = line_load.find(".//LoadTemplateItem")
        self.assertEqual(load_condition.get("Id"), "13")
        self.assertEqual(line_load.get("Key"), "201")
        self.assertEqual(line_load.get("Name"), "VERTICAL_APPLIED_LOAD_3")
        self.assertEqual(item.get("IdLoadTemplate"), "201")
        self.assertEqual(item.get("IdLoadCondition"), "13")


class TestCreateLoadCombination(unittest.TestCase):
    def test_copies_last_user_combination_and_increments_keys(self):
        root = ET.fromstring("""
            <HiStrA>
                <LoadCombination Key="15" Name="User_combination_1">
                    <Item LoadCombinationKey="15" ColumnKey="1" />
                </LoadCombination>
                <LoadCombination Key="17" Name="User_combination_2">
                    <Item LoadCombinationKey="17" ColumnKey="1" />
                    <Item LoadCombinationKey="17" ColumnKey="2" />
                </LoadCombination>
            </HiStrA>
        """)

        create_load_combination(root, active_load_condition_id="2")

        combination = root.findall("LoadCombination")[-1]
        self.assertEqual(combination.get("Key"), "18")
        self.assertEqual(combination.get("Name"), "User_combination_3")
        self.assertEqual(
            [item.get("LoadCombinationKey") for item in combination.findall("Item")],
            ["18", "18"],
        )
        self.assertEqual(
            [item.get("Val") for item in combination.findall("Item")],
            [None, "1"],
        )


class TestAddLineLoad(unittest.TestCase):
    def test_copies_last_line_load_for_closest_quad(self):
        root = ET.fromstring("""
            <HiStrA>
                <LoadCondition Id="11" Name="Load_Condition_1" Description="Load_Condition_1" />
                <LoadCondition Id="12" Name="Load_Condition_2" Description="Load_Condition_2" />
                <Template Key="147" Name="VERTICAL_APPLIED_LOAD_1">
                    <LoadtemplateItemList>
                        <LoadTemplateItem IdLoadTemplate="147" IdLoadCondition="11" />
                    </LoadtemplateItemList>
                </Template>
                <Template Key="148" Name="VERTICAL_APPLIED_LOAD_2">
                    <LoadtemplateItemList>
                        <LoadTemplateItem IdLoadTemplate="148" IdLoadCondition="12" />
                    </LoadtemplateItemList>
                </Template>
                <Template Key="200" Name="Other" />
                <LoadCombination Key="15" Name="User_combination_1">
                    <Item LoadCombinationKey="15" ColumnKey="11" RowKey="1" Val="0" />
                </LoadCombination>
                <LoadCombination Key="17" Name="User_combination_2">
                    <Item LoadCombinationKey="17" ColumnKey="11" RowKey="1" Val="0" />
                    <Item LoadCombinationKey="17" ColumnKey="12" RowKey="1" Val="0" />
                </LoadCombination>
                <Analysis Key="20" Name="LiveLoad_0" Description="Base live load"
                    LoadCombinationKey="15" LoadFunctionKey="20">
                    <States><State Key="20" /></States>
                </Analysis>
                <Analysis Key="21" Name="LiveLoad_1" Description="Base live load"
                    LoadCombinationKey="15" LoadFunctionKey="21">
                    <States><State Key="21" /></States>
                    <AdapticPhases><AdapticPhase ParentKey="21" /></AdapticPhases>
                </Analysis>
                <LoadFunction key="21" typeDiscr="false" DiscrVal="0.2" />
                <LoadFunctionItem key="65" loadFunctionKey="21" pseudoTime="0" multiplier="0" />
                <LoadFunctionItem key="66" loadFunctionKey="21" pseudoTime="1" multiplier="1" />
                <Quad Key="105" G="590;0;126.5" />
                <Quad Key="106" G="595;0;126.5" />
                <LoadElement TypeOf="HiStrA.Objects.LineLoadElement" Key="3" ParentKey="0"
                    ElementKey="106" ElementType="Quad" IdLoadTemplate="3"
                    Point1="595;-144;126.5" Point2="595;144;126.5" />
            </HiStrA>
        """)

        add_line_load(root, 590, "LiveLoad_0")

        line_load = root.findall("LoadElement")[-1]
        self.assertEqual(line_load.get("Key"), "4")
        self.assertEqual(line_load.get("ElementKey"), "105")
        self.assertEqual(line_load.get("IdLoadTemplate"), "201")
        self.assertEqual(line_load.get("Point1"), "590;-144;126.5")
        self.assertEqual(line_load.get("Point2"), "590;144;126.5")
        self.assertEqual(root.findall("LoadCondition")[-1].get("Id"), "13")
        self.assertEqual(root.findall("Template")[-1].get("Name"), "VERTICAL_APPLIED_LOAD_3")
        self.assertEqual(root.findall("LoadCombination")[-1].get("Name"), "User_combination_3")
        analyses = [
            analysis for analysis in root.findall("Analysis")
            if analysis.get("Name", "").endswith("_Pos_590")
        ]
        self.assertEqual(
            [analysis.get("Name") for analysis in analyses],
            ["LiveLoad_0_Pos_590"],
        )
        self.assertEqual([analysis.get("Key") for analysis in analyses], ["22"])
        self.assertEqual([analysis.get("LoadFunctionKey") for analysis in analyses], ["22"])
        self.assertEqual([analysis.get("LoadCombinationKey") for analysis in analyses], ["18"])
        self.assertIsNone(analyses[0].find(".//AdapticPhase"))
        load_function = root.findall("LoadFunction")[-1]
        self.assertEqual(load_function.get("key"), "22")
        self.assertEqual(
            [(item.get("key"), item.get("loadFunctionKey"), item.get("pseudoTime"), item.get("multiplier"))
            for item in root.findall("LoadFunctionItem")[-2:]],
            [("67", "22", "0", "0"), ("68", "22", "1", "1")],
        )
        children = list(root)
        self.assertEqual(children[children.index(line_load) - 1].get("Key"), "3")
        self.assertEqual(children[children.index(analyses[0]) - 1].get("Key"), "21")
        self.assertEqual(children[children.index(root.findall("Template")[-1]) - 1].get("Key"), "200")
        self.assertEqual(children[children.index(root.findall("LoadCombination")[-1]) - 1].get("Key"), "17")
        self.assertEqual(children[children.index(root.findall("LoadCondition")[-1]) - 1].get("Id"), "12")

        add_line_load(root, 590, "LiveLoad_1")

        self.assertEqual(len(root.findall("LoadCondition")), 3)
        self.assertEqual(len(root.findall("LoadCombination")), 3)
        self.assertEqual(len(root.findall("LoadElement")), 2)
        positioned = {
            analysis.get("Name"): analysis.get("LoadCombinationKey")
            for analysis in root.findall("Analysis")
            if analysis.get("Name", "").endswith("_Pos_590")
        }
        self.assertEqual(
            positioned,
            {"LiveLoad_0_Pos_590": "18", "LiveLoad_1_Pos_590": "18"},
        )


if __name__ == "__main__":
    unittest.main()
