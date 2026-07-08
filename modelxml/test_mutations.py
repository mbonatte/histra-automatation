import logging
import unittest

from modelxml.mutations import _select_outside_delta_interfaces


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


if __name__ == "__main__":
    unittest.main()
