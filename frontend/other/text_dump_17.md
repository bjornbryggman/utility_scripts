You are absolutely correct! I missed the test module. To make things more organized and reduce redundancy, we'll combine all the test functions into a single file: `test_text_processing.py`.

```python
# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module contains unit and integration tests for the text processing application.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from app.functions import text_processing
from app.core.db import File, OriginalValue, Property, ScalingFactor, engine, create_database, get_scaling_factors, generate_scaling_report
from sqlmodel import Session, select

class TestTextProcessing(unittest.TestCase):
    """
    Test suite for the text processing functions.
    """

    def setUp(self):
        """Set up for test methods."""
        create_database()

    def tearDown(self):
        """Clean up after each test method."""
        with Session(engine) as session:
            session.execute("DELETE FROM scaling_factor")
            session.execute("DELETE FROM original_value")
            session.execute("DELETE FROM property")
            session.execute("DELETE FROM file")
            session.commit()

    # ============================================================#
    #                Tests for Database Functions                  #
    # ============================================================#

    def test_create_database(self):
        """Database creation is tested implicitly in setUp."""
        pass

    def test_get_scaling_factors(self):
        """Test retrieving scaling factors from the database."""
        with Session(engine) as session:
            file_record = File(filename="test_file.gui", path="path/to/test_file.gui")
            session.add(file_record)
            session.commit()
            session.refresh(file_record)

            property_record = Property(name="x", file_id=file_record.id)
            session.add(property_record)
            session.commit()
            session.refresh(property_record)

            scaling_factor_record = ScalingFactor(
                property_id=property_record.id,
                resolution="2K",
                mean=1.2,
                median=1.2,
                std_dev=0.01,
                min=1.1,
                max=1.3,
            )
            session.add(scaling_factor_record)
            session.commit()

        scaling_factors = get_scaling_factors("path/to/test_file.gui", "2K")
        self.assertEqual(scaling_factors, {"x": 1.2})

    def test_generate_scaling_report(self):
        """Test generating a scaling report."""
        with Session(engine) as session:
            file_record = File(filename="test_file.gui", path="path/to/test_file.gui")
            session.add(file_record)
            session.commit()
            session.refresh(file_record)

            property_record = Property(name="x", file_id=file_record.id)
            session.add(property_record)
            session.commit()
            session.refresh(property_record)

            scaling_factor_record = ScalingFactor(
                property_id=property_record.id,
                resolution="2K",
                mean=1.2,
                median=1.2,
                std_dev=0.01,
                min=1.1,
                max=1.3,
            )
            session.add(scaling_factor_record)
            session.commit()

        generate_scaling_report("2K")
        # Assert that the report file exists and has the correct content
        report_file = Path("2K_scaling_report.json")
        self.assertTrue(report_file.exists())

        with open(report_file, "r") as f:
            report_content = json.load(f)

        expected_content = {
            "test_file.gui": {"x": {"mean": 1.2, "median": 1.2, "std_dev": 0.01, "min": 1.1, "max": 1.3}}
        }
        self.assertEqual(report_content, expected_content)

    # ============================================================#
    #        Tests for Text Processing Functions        #
    # ============================================================#

    def test_extract_positional_values(self):
        """Test extracting positional values from text content."""
        test_content = """
        guiTypes = {
            windowType = {
                position = { x = 10 y = 5 }
                size = { x = 200 y = 100 }
            }
        }
        """
        expected_values = {"x": [10, 200], "y": [5, 100]}
        actual_values = text_processing.extract_positional_values(test_content)
        self.assertEqual(actual_values, expected_values)

    def test_calculate_property_scaling(self):
        """Test calculating scaling factors for properties."""
        original_values = {"x": [10, 20], "y": [5, 10]}
        scaled_values = {"x": [12, 24], "y": [6, 12]}
        expected_scaling = {
            "x": {"mean": 1.2, "median": 1.2, "std_dev": 0, "min": 1.2, "max": 1.2},
            "y": {"mean": 1.2, "median": 1.2, "std_dev": 0, "min": 1.2, "max": 1.2},
        }
        actual_scaling = text_processing.calculate_property_scaling(original_values, scaled_values)
        self.assertEqual(actual_scaling, expected_scaling)

    @patch("app.functions.text_processing.file_utils.read_file")
    def test_store_scaling_factors_in_database(self, mock_read_file):
        """Test storing scaling factors in the database."""
        mock_read_file.return_value = """
        guiTypes = {
            windowType = {
                position = { x = 10 y = 5 }
                size = { x = 200 y = 100 }
            }
        }
        """
        original_file = Path("path/to/test_file.gui")
        original_values = {"x": [10, 200], "y": [5, 100]}
        scale_2k = {
            "x": {"mean": 1.2, "median": 1.2, "std_dev": 0, "min": 1.2, "max": 1.2},
            "y": {"mean": 1.2, "median": 1.2, "std_dev": 0, "min": 1.2, "max": 1.2},
        }
        scale_4k = {
            "x": {"mean": 1.4, "median": 1.4, "std_dev": 0, "min": 1.4, "max": 1.4},
            "y": {"mean": 1.4, "median": 1.4, "std_dev": 0, "min": 1.4, "max": 1.4},
        }
        text_processing.store_scaling_factors_in_database(original_file, original_values, scale_2k, scale_4k)

        with Session(engine) as session:
            file_record = session.exec(select(File).where(File.path == str(original_file))).first()
            self.assertIsNotNone(file_record)

            property_records = session.exec(select(Property).where(Property.file_id == file_record.id)).all()
            self.assertEqual(len(property_records), 2)

            original_value_records = session.exec(select(OriginalValue)).all()
            self.assertEqual(len(original_value_records), 4)

            scaling_factor_records = session.exec(select(ScalingFactor)).all()
            self.assertEqual(len(scaling_factor_records), 4)

    @patch("app.functions.text_processing.apply_scaling_factors")
    @patch("app.functions.text_processing.file_utils.read_file")
    def test_scale_file_contents(self, mock_read_file, mock_apply_scaling_factors):
        """Test scaling file contents."""
        mock_read_file.return_value = """
        guiTypes = {
            windowType = {
                position = { x = 10 y = 5 }
                size = { x = 200 y = 100 }
            }
        }
        """
        mock_apply_scaling_factors.return_value = "scaled_content"
        file_path = Path("path/to/test_file.gui")
        resolution = "2K"
        scaled_content = text_processing.scale_file_contents(file_path, resolution)
        self.assertEqual(scaled_content, "scaled_content")
        mock_apply_scaling_factors.assert_called_once_with(
            mock_read_file.return_value, {"x": [10, 200], "y": [5, 100]}, "2K"
        )

    @patch("app.functions.text_processing.file_utils.read_file")
    @patch("app.functions.text_processing.extract_positional_values")
    def test_apply_scaling_factors(self, mock_extract_positional_values, mock_read_file):
        """Test applying scaling factors to content."""
        mock_extract_positional_values.return_value = {"x": [10, 200], "y": [5, 100]}
        mock_read_file.return_value = "test_content"
        resolution = "2K"
        with Session(engine) as session:
            file_record = File(filename="test_file.gui", path="path/to/test_file.gui")
            session.add(file_record)
            session.commit()
            session.refresh(file_record)

            property_x_record = Property(name="x", file_id=file_record.id)
            session.add(property_x_record)
            session.commit()
            session.refresh(property_x_record)

            property_y_record = Property(name="y", file_id=file_record.id)
            session.add(property_y_record)
            session.commit()
            session.refresh(property_y_record)

            scaling_factor_x_record = ScalingFactor(
                property_id=property_x_record.id,
                resolution="2K",
                mean=1.2,
                median=1.2,
                std_dev=0.01,
                min=1.1,
                max=1.3,
            )
            session.add(scaling_factor_x_record)
            session.commit()

            scaling_factor_y_record = ScalingFactor(
                property_id=property_y_record.id,
                resolution="2K",
                mean=1.2,
                median=1.2,
                std_dev=0.01,
                min=1.1,
                max=1.3,
            )
            session.add(scaling_factor_y_record)
            session.commit()

        scaled_content = text_processing.apply_scaling_factors("test_content", {"x": [10, 200], "y": [5, 100]}, "2K")
        self.assertIn("x = 12", scaled_content)
        self.assertIn("y = 6", scaled_content)

    # ============================================================#
    #                Tests for Scaling Workflow                  #
    # ============================================================#

    @patch("app.functions.text_processing.scale_file_contents")
    def test_scale_positional_values(self, mock_scale_file_contents):
        """Test the main scaling workflow."""
        input_directory = Path("path/to/input_dir")
        output_directory = Path("path/to/output_dir")
        input_format = "gui"
        resolution = "2K"
        mock_scale_file_contents.return_value = "scaled_content"
        text_processing.scale_positional_values(input_directory, output_directory, input_format, resolution)
        mock_scale_file_contents.assert_called()

    @patch("app.functions.text_processing.store_scaling_factors_in_database")
    def test_calculate_and_store_scaling_factors(self, mock_store_scaling_factors_in_database):
        """Test calculating and storing scaling factors."""
        original_directory = Path("path/to/original_dir")
        scaled_2k_directory = Path("path/to/scaled_2k_dir")
        scaled_4k_directory = Path("path/to/scaled_4k_dir")
        input_format = "gui"
        text_processing.calculate_and_store_scaling_factors(original_directory, scaled_2k_directory, scaled_4k_directory, input_format)
        mock_store_scaling_factors_in_database.assert_called()


if __name__ == '__main__':
    unittest.main()
```

We've combined all the test functions from the previous separate test modules into this single file. We've also added docstrings to the test class and test methods to explain their purpose and functionality.

This completes the documentation and organization of our test suite.

Let me know if you have any other questions!