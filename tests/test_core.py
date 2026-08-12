"""Core tests for 月相羅針 計算PoC v0.6｜入力UI・現在値改善."""

from __future__ import annotations

import os
import sys
import unittest

# Allow tests to import modules from the project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from astronomy import calculate_birth_astronomy, calculate_birth_date_astronomy
from phase_classifier import classify_phase, classify_possible_phases


class TestAstronomy(unittest.TestCase):
    def test_reference_birth_data_known_time(self) -> None:
        """Test 1: known birth time keeps the existing exact calculation."""
        result = calculate_birth_astronomy(
            birth_date="1964-09-03",
            birth_time="11:23",
            timezone_name="Asia/Tokyo",
        )

        self.assertEqual(
            result["utc_datetime"].strftime("%Y-%m-%d %H:%M:%S UTC"),
            "1964-09-03 02:23:00 UTC",
        )

        # The original PoC reference values are approximate. A tolerance of
        # 0.0001 degree (= 0.36 arcsec) avoids brittle float comparisons.
        tolerance = 0.0001
        self.assertAlmostEqual(
            float(result["sun_longitude"]), 160.60945188, delta=tolerance
        )
        self.assertAlmostEqual(
            float(result["moon_longitude"]), 119.86709682, delta=tolerance
        )
        self.assertAlmostEqual(
            float(result["angle_difference"]), 319.25764494, delta=tolerance
        )

        phase = classify_phase(float(result["angle_difference"]))
        self.assertEqual(phase["id"], "P08")
        self.assertEqual(phase["name"], "欠けていく三日月")


class TestProvisionalPhaseBoundaries(unittest.TestCase):
    def test_boundaries(self) -> None:
        """Test 2: 45-degree boundaries and 360->0 normalization."""
        cases = [
            (0.0, "P01"),
            (44.9999, "P01"),
            (45.0, "P02"),
            (315.0, "P08"),
            (359.9999, "P08"),
            (360.0, "P01"),
        ]
        for angle, expected_id in cases:
            with self.subTest(angle=angle):
                self.assertEqual(classify_phase(angle)["id"], expected_id)

    def test_possible_phases_handles_wraparound(self) -> None:
        result = classify_possible_phases([359.5, 0.5])
        self.assertEqual(result["classification_status"], "ambiguous")
        self.assertEqual(
            [phase["id"] for phase in result["possible_phases"]],
            ["P08", "P01"],
        )


class TestUnknownBirthTime(unittest.TestCase):
    def test_stable_day_returns_one_candidate(self) -> None:
        """Test 3: 1964-09-04 stays within P08 for the whole JST date."""
        day = calculate_birth_date_astronomy(
            birth_date="1964-09-04",
            timezone_name="Asia/Tokyo",
            interval_minutes=30,
        )
        result = classify_possible_phases(day["angle_differences"])

        self.assertEqual(result["classification_status"], "stable")
        self.assertEqual(len(result["possible_phases"]), 1)
        self.assertEqual(result["possible_phases"][0]["id"], "P08")

    def test_ambiguous_day_returns_multiple_candidates(self) -> None:
        """Test 4: 1964-09-03 crosses the 315-degree P07/P08 boundary."""
        day = calculate_birth_date_astronomy(
            birth_date="1964-09-03",
            timezone_name="Asia/Tokyo",
            interval_minutes=30,
        )
        result = classify_possible_phases(day["angle_differences"])

        self.assertEqual(result["classification_status"], "ambiguous")
        self.assertGreaterEqual(len(result["possible_phases"]), 2)
        self.assertEqual(
            [phase["id"] for phase in result["possible_phases"]],
            ["P07", "P08"],
        )


class TestWebInputUI(unittest.TestCase):
    def test_template_keeps_previous_values_out_of_html_defaults(self) -> None:
        """v0.6: previous values are live values, not reset/default values."""
        template_path = os.path.join(PROJECT_ROOT, "templates", "index.html")
        with open(template_path, encoding="utf-8") as handle:
            html = handle.read()

        self.assertIn('data-current-value="{{ form.birth_date }}"', html)
        self.assertIn('data-current-value="{{ form.birth_time }}"', html)
        self.assertIn('data-current-value="{{ form.birth_place }}"', html)
        self.assertNotIn(' value="{{ form.birth_date }}"', html)
        self.assertNotIn(' value="{{ form.birth_time }}"', html)
        self.assertNotIn(' value="{{ form.birth_place }}"', html)
        self.assertIn('月相羅針 計算PoC v0.6', html)

    def test_form_reset_script_clears_all_three_fields(self) -> None:
        """v0.6: the reset handler still explicitly empties all fields."""
        template_path = os.path.join(PROJECT_ROOT, "templates", "index.html")
        with open(template_path, encoding="utf-8") as handle:
            html = handle.read()

        self.assertIn('class="birth-form"', html)
        self.assertIn('form.addEventListener("reset"', html)
        self.assertIn('field.value = ""', html)
        self.assertEqual(html.count('data-current-value='), 3)

    def test_all_input_types_share_fixed_height_and_top_alignment(self) -> None:
        """v0.6: date/time/text controls use one fixed height without row drift."""
        css_path = os.path.join(PROJECT_ROOT, "static", "style.css")
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()

        self.assertIn('align-content: start;', css)
        self.assertIn('align-self: start;', css)
        self.assertIn('--form-control-height: 48px;', css)
        self.assertIn('input[type="date"]', css)
        self.assertIn('input[type="time"]', css)
        self.assertIn('input[type="text"]', css)
        self.assertIn('max-block-size: var(--form-control-height);', css)

    def test_empty_date_and_time_are_primed_with_device_local_now(self) -> None:
        """v0.6: opening an empty native picker starts from local current date/time."""
        template_path = os.path.join(PROJECT_ROOT, "templates", "index.html")
        with open(template_path, encoding="utf-8") as handle:
            html = handle.read()

        self.assertIn('const now = new Date();', html)
        self.assertIn('now.getFullYear()', html)
        self.assertIn('now.getMonth() + 1', html)
        self.assertIn('now.getDate()', html)
        self.assertIn('now.getHours()', html)
        self.assertIn('now.getMinutes()', html)
        self.assertIn('field.addEventListener("pointerdown"', html)
        self.assertIn('field.addEventListener("focus"', html)
        self.assertIn('if (field.value) return;', html)

    def test_stylesheet_url_is_cache_busted_for_v06(self) -> None:
        """v0.6: force browsers to fetch the new input-height CSS."""
        template_path = os.path.join(PROJECT_ROOT, "templates", "index.html")
        with open(template_path, encoding="utf-8") as handle:
            html = handle.read()

        self.assertIn("filename='style.css', v='0.6'", html)


if __name__ == "__main__":
    unittest.main()
