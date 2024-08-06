You got it! Let's incorporate Faker to generate fake test data for our tests.

Here's the updated `test_text_processing.py` file using Faker:

```python
# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module contains unit and integration tests for the text processing application using pytest and Faker.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from faker import Faker
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

fake = Faker()

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
        file_record = File(filename=fake.file_name(extension="gui"), path=fake.file_path(extension="gui"))
        session.add(file_record)
        session.commit()
        session.refresh(file_record)

        property_record = Property(name=fake.word(), file_id=file_record.id)
        session.add(property_record)
        session.commit()
        session.refresh(property_record)

        scaling_factor_record = ScalingFactor(
            property_id=property_record.id,
            resolution="2K",
            mean=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            median=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            std_dev=fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            min=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            max=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        )
        session.add(scaling_factor_record)
        session.commit()

    scaling_factors = get_scaling_factors(file_record.path, "2K")
    assert scaling_factors == {property_record.name: scaling_factor_record.mean}


def test_generate_scaling_report():
    """Test generating a scaling report."""
    with Session(engine) as session:
        file_record = File(filename=fake.file_name(extension="gui"), path=fake.file_path(extension="gui"))
        session.add(file_record)
        session.commit()
        session.refresh(file_record)

        property_record = Property(name=fake.word(), file_id=file_record.id)
        session.add(property_record)
        session.commit()
        session.refresh(property_record)

        scaling_factor_record = ScalingFactor(
            property_id=property_record.id,
            resolution="2K",
            mean=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            median=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            std_dev=fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            min=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            max=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
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
        file_record.filename: {property_record.name: {"mean": scaling_factor_record.mean, "median": scaling_factor_record.median, "std_dev": scaling_factor_record.std_dev, "min": scaling_factor_record.min, "max": scaling_factor_record.max}}
    }
    assert report_content == expected_content


# ============================================================#
#        Tests for Text Processing Functions        #
# ============================================================#


def test_extract_positional_values():
    """Test extracting positional values from text content."""
    test_content = f"""
    guiTypes = {{
        windowType = {{
            position = {{ {fake.word()} = {fake.random_int(min=1, max=100)} {fake.word()} = {fake.random_int(min=1, max=100)} }}
            size = {{ {fake.word()} = {fake.random_int(min=1, max=100)} {fake.word()} = {fake.random_int(min=1, max=100)} }}
        }}
    }}
    """
    expected_values = {
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
    }
    actual_values = text_processing.extract_positional_values(test_content)
    assert actual_values == expected_values


def test_calculate_property_scaling():
    """Test calculating scaling factors for properties."""
    original_values = {
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
    }
    scaled_values = {
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
    }
    expected_scaling = {
        fake.word(): {
            "mean": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "median": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "std_dev": fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            "min": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "max": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        },
        fake.word(): {
            "mean": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "median": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "std_dev": fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            "min": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "max": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        },
    }
    actual_scaling = text_processing.calculate_property_scaling(original_values, scaled_values)
    assert actual_scaling == expected_scaling


@patch("app.functions.text_processing.file_utils.read_file")
def test_store_scaling_factors_in_database(mock_read_file):
    """Test storing scaling factors in the database."""
    mock_read_file.return_value = f"""
    guiTypes = {{
        windowType = {{
            position = {{ {fake.word()} = {fake.random_int(min=1, max=100)} {fake.word()} = {fake.random_int(min=1, max=100)} }}
            size = {{ {fake.word()} = {fake.random_int(min=1, max=100)} {fake.word()} = {fake.random_int(min=1, max=100)} }}
        }}
    }}
    """
    original_file = Path(fake.file_path(extension="gui"))
    original_values = {
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
    }
    scale_2k = {
        fake.word(): {
            "mean": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "median": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "std_dev": fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            "min": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "max": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        },
        fake.word(): {
            "mean": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "median": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "std_dev": fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            "min": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "max": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        },
    }
    scale_4k = {
        fake.word(): {
            "mean": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "median": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "std_dev": fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            "min": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "max": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        },
        fake.word(): {
            "mean": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "median": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "std_dev": fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            "min": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            "max": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        },
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
    mock_read_file.return_value = f"""
    guiTypes = {{
        windowType = {{
            position = {{ {fake.word()} = {fake.random_int(min=1, max=100)} {fake.word()} = {fake.random_int(min=1, max=100)} }}
            size = {{ {fake.word()} = {fake.random_int(min=1, max=100)} {fake.word()} = {fake.random_int(min=1, max=100)} }}
        }}
    }}
    """
    mock_apply_scaling_factors.return_value = "scaled_content"
    file_path = Path(fake.file_path(extension="gui"))
    resolution = "2K"
    scaled_content = text_processing.scale_file_contents(file_path, resolution)
    assert scaled_content == "scaled_content"
    mock_apply_scaling_factors.assert_called_once_with(
        mock_read_file.return_value,
        {
            fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
            fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        },
        "2K",
    )


@patch("app.functions.text_processing.file_utils.read_file")
@patch("app.functions.text_processing.extract_positional_values")
def test_apply_scaling_factors(mock_extract_positional_values, mock_read_file):
    """Test applying scaling factors to content."""
    mock_extract_positional_values.return_value = {
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        fake.word(): [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
    }
    mock_read_file.return_value = "test_content"
    resolution = "2K"
    with Session(engine) as session:
        file_record = File(filename=fake.file_name(extension="gui"), path=fake.file_path(extension="gui"))
        session.add(file_record)
        session.commit()
        session.refresh(file_record)

        property_x_record = Property(name=fake.word(), file_id=file_record.id)
        session.add(property_x_record)
        session.commit()
        session.refresh(property_x_record)

        property_y_record = Property(name=fake.word(), file_id=file_record.id)
        session.add(property_y_record)
        session.commit()
        session.refresh(property_y_record)

        scaling_factor_x_record = ScalingFactor(
            property_id=property_x_record.id,
            resolution="2K",
            mean=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            median=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            std_dev=fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            min=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            max=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        )
        session.add(scaling_factor_x_record)
        session.commit()

        scaling_factor_y_record = ScalingFactor(
            property_id=property_y_record.id,
            resolution="2K",
            mean=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            median=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            std_dev=fake.pyfloat(min_value=0.0, max_value=0.1, right_digits=2),
            min=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
            max=fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=2),
        )
        session.add(scaling_factor_y_record)
        session.commit()

    scaled_content = text_processing.apply_scaling_factors(
        "test_content",
        {
            property_x_record.name: [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
            property_y_record.name: [fake.random_int(min=1, max=100), fake.random_int(min=1, max=100)],
        },
        "2K",
    )
    assert f"{property_x_record.name} = " in scaled_content
    assert f"{property_y_record.name} = " in scaled_content


# ============================================================#
#                Tests for Scaling Workflow                  #
# ============================================================#


@patch("app.functions.text_processing.scale_file_contents")
def test_scale_positional_values(mock_scale_file_contents):
    """Test the main scaling workflow."""
    input_directory = Path(fake.file_path())
    output_directory = Path(fake.file_path())
    input_format = fake.file_extension()
    resolution = "2K"
    mock_scale_file_contents.return_value = "scaled_content"
    text_processing.scale_positional_values(input_directory, output_directory, input_format, resolution)
    mock_scale_file_contents.assert_called()


@patch("app.functions.text_processing.store_scaling_factors_in_database")
def test_calculate_and_store_scaling_factors(mock_store_scaling_factors_in_database):
    """Test calculating and storing scaling factors."""
    original_directory = Path(fake.file_path())
    scaled_2k_directory = Path(fake.file_path())
    scaled_4k_directory = Path(fake.file_path())
    input_format = fake.file_extension()
    text_processing.calculate_and_store_scaling_factors(original_directory, scaled_2k_directory, scaled_4k_directory, input_format)
    mock_store_scaling_factors_in_database.assert_called()
```

**Key Changes:**

- **Import Faker:** We import `Faker` at the beginning of the file.
- **Create a Faker Instance:** We create a `Faker` instance named `fake`.
- **Use Faker in Tests:** We use `fake` to generate fake data for file names, paths, properties, values, and scaling factors.

Now, our tests will use realistic-looking fake data, making them more robust and less dependent on specific values.

Remember to install Faker if you haven't already:

```bash
pip install Faker
```

Let me know if you have any other questions!