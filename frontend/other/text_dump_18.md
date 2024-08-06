You're right, pytest is a great choice for testing in Python. Let's convert our tests to use pytest.

Here's the updated `test_text_processing.py` file using pytest:

```python
# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module contains unit and integration tests for the text processing application using pytest.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.core.db import (
    File,
    OriginalValue,
    Property,
    ScalingFactor,
    engine,
    create_database,
    get_scaling_factors,
    generate_scaling_report,
)
from app.functions import text_processing


@pytest.fixture(autouse=True)
def setup_database():
    """Set up the database before each test."""
    create_database()
    yield
    with Session(engine) as session:
        session.execute("DELETE FROM scaling_factor")
        session.execute("DELETE FROM original_value")
        session.execute("DELETE FROM property")
        session.execute("DELETE FROM file")
        session.commit()


# ============================================================#
#                Tests for Database Functions                  #
# ============================================================#


def test_get_scaling_factors():
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
    assert scaling_factors == {"x": 1.2}


def test_generate_scaling_report():
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
    assert report_file.exists()

    with open(report_file, "r") as f:
        report_content = json.load(f)

    expected_content = {
        "test_file.gui": {"x": {"mean": 1.2, "median": 1.2, "std_dev": 0.01, "min": 1.1, "max": 1.3}}
    }
    assert report_content == expected_content


# ============================================================#
#        Tests for Text Processing Functions        #
# ============================================================#


def test_extract_positional_values():
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
    assert actual_values == expected_values


def test_calculate_property_scaling():
    """Test calculating scaling factors for properties."""
    original_values = {"x": [10, 20], "y": [5, 10]}
    scaled_values = {"x": [12, 24], "y": [6, 12]}
    expected_scaling = {
        "x": {"mean": 1.2, "median": 1.2, "std_dev": 0, "min": 1.2, "max": 1.2},
        "y": {"mean": 1.2, "median": 1.2, "std_dev": 0, "min": 1.2, "max": 1.2},
    }
    actual_scaling = text_processing.calculate_property_scaling(original_values, scaled_values)
    assert actual_scaling == expected_scaling


@patch("app.functions.text_processing.file_utils.read_file")
def test_store_scaling_factors_in_database(mock_read_file):
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
        assert file_record is not None

        property_records = session.exec(select(Property).where(Property.file_id == file_record.id)).all()
        assert len(property_records) == 2

        original_value_records = session.exec(select(OriginalValue)).all()
        assert len(original_value_records) == 4

        scaling_factor_records = session.exec(select(ScalingFactor)).all()
        assert len(scaling_factor_records) == 4


@patch("app.functions.text_processing.apply_scaling_factors")
@patch("app.functions.text_processing.file_utils.read_file")
def test_scale_file_contents(mock_read_file, mock_apply_scaling_factors):
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
    assert scaled_content == "scaled_content"
    mock_apply_scaling_factors.assert_called_once_with(
        mock_read_file.return_value, {"x": [10, 200], "y": [5, 100]}, "2K"
    )


@patch("app.functions.text_processing.file_utils.read_file")
@patch("app.functions.text_processing.extract_positional_values")
def test_apply_scaling_factors(mock_extract_positional_values, mock_read_file):
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
    assert "x = 12" in scaled_content
    assert "y = 6" in scaled_content


# ============================================================#
#                Tests for Scaling Workflow                  #
# ============================================================#


@patch("app.functions.text_processing.scale_file_contents")
def test_scale_positional_values(mock_scale_file_contents):
    """Test the main scaling workflow."""
    input_directory = Path("path/to/input_dir")
    output_directory = Path("path/to/output_dir")
    input_format = "gui"
    resolution = "2K"
    mock_scale_file_contents.return_value = "scaled_content"
    text_processing.scale_positional_values(input_directory, output_directory, input_format, resolution)
    mock_scale_file_contents.assert_called()


@patch("app.functions.text_processing.store_scaling_factors_in_database")
def test_calculate_and_store_scaling_factors(mock_store_scaling_factors_in_database):
    """Test calculating and storing scaling factors."""
    original_directory = Path("path/to/original_dir")
    scaled_2k_directory = Path("path/to/scaled_2k_dir")
    scaled_4k_directory = Path("path/to/scaled_4k_dir")
    input_format = "gui"
    text_processing.calculate_and_store_scaling_factors(original_directory, scaled_2k_directory, scaled_4k_directory, input_format)
    mock_store_scaling_factors_in_database.assert_called()
```

Key changes:

- **`pytest.fixture`:** We use `pytest.fixture` to set up the database before each test and clean it up afterward.
- **`assert` statements:** We use `assert` statements instead of `self.assertEqual` for assertions.
- **Test Function Naming:** Test function names are more descriptive and follow the convention of `test_function_name`.

Now, you can run your tests using the `pytest` command:

```bash
pytest
```

This will run all the tests in your `test_text_processing.py` file.

Let me know if you have any other questions!