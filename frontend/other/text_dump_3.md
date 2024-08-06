Alright, let's implement error handling and logging in our `text_processing.py` file.

Here's the updated code:

```python
# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module provides functionality for handling text files and processing their positional values.

All functions are split up into a worker & caller function pair, utilizing multiprocessing to speed up operations.
"""

import json
import multiprocessing
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from statistics import mean, median, stdev

import structlog
from sqlmodel import Session, select

from app.core.db import File, OriginalValue, Property, ScalingFactor, engine
from app.utils import file_utils

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)


# ============================================================#
#        Worker function for scaling positional values        #
# ============================================================#


def scale_positional_values_worker(args: tuple) -> str:
    """
    Worker function for scaling positional values in text files.

    This function processes a single text file, scaling specific positional attributes
    according to a provided scaling factor. It then writes the modified content to the
    output directory.

    Args:
    ----
    - args (tuple): A tuple containing the following arguments:
        - input_file (Path): The input text file.
        - input_directory (Path): The directory containing the input text files.
        - output_directory (Path): The directory to output processed files.
        - scale_factor (float): The scaling factor to apply to positional values.

    Returns:
    -------
    - None

    Raises:
    ------
    - PermissionError: If there's a permission issue when accessing files.
    - OSError: If there's an operating system related error.
    - Exception: For any other unexpected errors during processing.
    """
    input_file, input_directory, output_directory, scale_factor = args

    def scale_value(match: re.Match) -> str:
        """
        Scales a matched value according to the scaling factor.

        Args:
        ----
        - match (re.Match): A regex match object containing the property and value.

        Returns:
        -------
        - str: A string with the scaled value in the format "property = scaled_value",
            or the original string if the value is "-1".
        """
        prop = match.group(1)
        value = match.group(2).strip()

        # Return the original string if value contains '%', '@', '10s', or is "-1".
        if any(x in value for x in ["%", "@", "10s"]) or value == "-1":
            return f"{prop} = {value}"

        # Handle complex size format, e.g.: size = {x = 5 y = 5}.
        if value.startswith("{"):
            return f"{prop} = " + re.sub(
                r"([\w_]+)\s*=\s*(-?\d+(?:\.\d+)?)",
                lambda m: f"{m.group(1)} = {m.group(2) if m.group(2) == '-1' or any(x in m.group(2) for x in ['%', '@', '10s']) else round(float(m.group(2)) * scale_factor)}",
                value,
            )

        # Handle simple size format, e.g.: size = 17.
        try:
            scaled_value = round(float(value) * scale_factor)
        # Return original if not a number.
        except ValueError:
            return f"{prop} = {value}"
        else:
            return f"{prop} = {scaled_value}"

    def process_content(content: str) -> str:
        """
        Scales specific values in the content according to the scaling factor.

        Args:
        ----
        - content (str): The content of a text file.

        Returns:
        -------
        - str: The content with scaled positional values.
        """
        # Regular expression to match & scale positional properties and their values.
        pattern = r"(\b(?:x|y|width|height|maxWidth|maxHeight|size|borderSize|spacing|position|pos_x)\b)\s*=\s*({[^}]+}|-?\d+(?:\.\d+)?%?|[^}\n]+)"

        return re.sub(pattern, scale_value, content, flags=re.IGNORECASE)

    try:
        # Read the content of the copied file.
        content = file_utils.read_file(input_file)

        if content is not None:
            # Calculate the relative output path to maintain directory structure.
            relative_path = input_file.relative_to(input_directory)
            output_path = output_directory / relative_path.parent

            # Process the content and scale positional attributes.
            updated_content = process_content(content)
            if content != updated_content:
                output_path.mkdir(parents=True, exist_ok=True)
                output_file = output_path / input_file.name
                file_utils.write_file(output_file, updated_content)
                log.debug("Updated %s with scaled values.", output_file.name)

            else:
                log.debug("No changes have been made to %s.", input_file.name)

        else:
            # Skip to the next file if no content is found.
            log.error("No content found in file: %s", input_file)

    except PermissionError as error:
        log.exception("Permission denied when accessing file: %s", input_file, exc_info=error)
        sys.exit()
    except OSError as error:
        log.exception("OS error while processing file: %s", input_file, exc_info=error)
    except Exception as error:
        log.exception("Unexpected error while processing file: %s", input_file, exc_info=error)


# ============================================================#
#        Caller function for scaling positional values        #
# ============================================================#


def scale_positional_values(
    input_directory: Path, output_directory: Path, input_format: str, scale_factor: float
) -> None:
    """
    Scales relevant positional values in text files according to a specified scaling factor.

    This function reads text files from the input directory, applies a scaling factor to
    specific positional attributes, and writes the modified content to the output directory.

    Args:
    ----
    - input_directory (Path): The directory containing the GUI files to process.
    - output_directory (Path): The directory to output processed files.
    - input_format (str): The file extension of input GUI files (e.g., 'xml', 'ui').
    - scale_factor (float): The scaling factor to apply to positional values.

    Returns:
    -------
    - None

    Raises:
    ------
    - FileNotFoundError: If no images are found in the input directory.
    - ValueError: If an invalid scaling factor is provided.
    - Exception: If an unexpected error occurs.
    """
    log.info("Scaling positional values in text files with a scale factor of %s...", scale_factor)

    try:
        # Use a ProcessPoolExecutor to run the worker function in parallel.
        input_files = list(input_directory.rglob(f"*.{input_format.lower()}"))
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            args = [(input_file, input_directory, output_directory, scale_factor) for input_file in input_files]
            results = list(executor.map(scale_positional_values_worker, args, chunksize=10))

            # Consume the iterator to trigger any exceptions.
            for _ in results:
                pass

    except FileNotFoundError as error:
        log.exception("No %s files found in %s.", input_format.upper(), input_directory, exc_info=error)
        sys.exit()
    except ValueError as error:
        log.exception("'%s' is not a valid scaling factor.", scale_factor, exc_info=error)
        sys.exit()
    except Exception as error:
        log.exception("An unexpected error occurred.", exc_info=error)


# ==============================================================#
#        Worker function for comparing positional values        #
# ==============================================================#


def calculate_scaling_factors_worker(args: tuple[Path, Path, Path]) -> None:
    """
    Worker function for calculating scaling factors for a single text file and storing them in the database.

    This function compares positional values in an original text file with its 2K and 4K
    scaled versions. It calculates scaling factors for individual properties and stores
    them in the database.

    Args:
    ----
    - args (tuple[Path, Path, Path]): A tuple containing:
        - original_file (Path): Path to the original text file.
        - scaled_2k_file (Path): Path to the 2K scaled version of the file.
        - scaled_4k_file (Path): Path to the 4K scaled version of the file.

    Returns:
    -------
    - None

    Raises:
    ------
    - Exception: If an error occurs during file processing or calculation.
    """
    original_file, scaled_2k_file, scaled_4k_file = args

    try:
        # Check if all relevant files exist, skip if any are missing.
        if not all(file.exists() for file in [original_file, scaled_2k_file, scaled_4k_file]):
            log.warning("Skipping %s due to missing files.", original_file.name)
            return

        # Extract positional values from each file.
        original_values = extract_positional_values(original_file)
        scaled_2k_values = extract_positional_values(scaled_2k_file)
        scaled_4k_values = extract_positional_values(scaled_4k_file)

        # Check if any content is None, skip if so.
        if any(values is None for values in [original_values, scaled_2k_values, scaled_4k_values]):
            log.warning("Skipping file %s due to missing content in one or more versions.", original_file)
            return

        # Calculate scaling factors for 2K and 4K resolutions.
        scale_2k = calculate_property_scaling(original_values, scaled_2k_values)
        scale_4k = calculate_property_scaling(original_values, scaled_4k_values)

        # Store results in the database
        store_scaling_factors_in_database(original_file, original_values, scale_2k, scale_4k)

        log.info("Stored scaling factors for %s in the database.", original_file.name)

    except Exception as error:
        log.exception("An unexpected error occurred.", exc_info=error)


def extract_positional_values(file_path: Path) -> dict[str, list[float]]:
    """
    Extracts positional values from the content of a text file.

    Args:
    ----
    - content (str): The content of the text file.

    Returns:
    -------
    - dict[str, list[float]]: A dictionary where keys are property names and values
    are lists of corresponding positional values.
    """
    values = {}
    pattern = r"(\b(?:x|y|width|height|maxWidth|maxHeight|size|borderSize|spacing|position|pos_x)\b)\s*=\s*({[^}]+}|-?\d+(?:\.\d+)?%?|[^}\n]+)"

    content = file_utils.read_file(file_path)
    if content is None:
        return None

    for match in re.finditer(pattern, content, re.IGNORECASE):
        # Extract property name and value.
        prop, value = match.groups()
        # If value is a digit, add it to the dictionary.
        if value.isdigit():
            if prop not in values:
                values[prop] = []
            values[prop].append(float(value))
    return values


def calculate_property_scaling(
    original: dict[str, list[float]], scaled: dict[str, list[float]]
) -> dict[str, dict[str, float]]:
    """
    Calculates scaling factors for individual properties.

    Args:
    ----
    - original (dict[str, list[float]]): Positional values from the original file.
    - scaled (dict[str, list[float]]): Positional values from the scaled file.

    Returns:
    -------
    - dict[str, dict[str, float]]: A dictionary where keys are property names and
    values are dictionaries containing scaling factor statistics (mean, median,
    standard deviation, minimum, maximum).
    """
    scaling = {}
    for prop in original:
        # Check if the property exists in both original and scaled values.
        if prop in scaled and len(original[prop]) == len(scaled[prop]):
            # Calculate scaling factors for each property.
            factors = [s / o for o, s in zip(original[prop], scaled[prop], strict=True) if o != 0]

            # If factors are found, calculate statistics.
            if factors:
                scaling[prop] = {
                    "mean": mean(factors),
                    "median": median(factors),
                    "std_dev": stdev(factors) if len(factors) > 1 else 0,
                    "min": min(factors),
                    "max": max(factors),
                }

            # Otherwise, set all statistics to None.
            else:
                scaling[prop] = {"mean": None, "median": None, "std_dev": None, "min": None, "max": None}
    return scaling


def store_scaling_factors_in_database(
    original_file: Path,
    original_values: dict[str, list[float]],
    scale_2k: dict[str, dict[str, float]],
    scale_4k: dict[str, dict[str, float]],
) -> None:
    """
    Stores original values and scaling factors in the database.

    Args:
    ----
    - original_file (Path): Path to the original text file.
    - original_values (dict[str, list[float]]): Original positional values for the file.
    - scale_2k (dict[str, dict[str, float]]): Scaling factors for 2K resolution.
    - scale_4k (dict[str, dict[str, float]]): Scaling factors for 4K resolution.

    Returns:
    -------
    - None
    """
    with Session(engine) as session:
        # Create or get the File record
        file_record = session.exec(select(File).where(File.path == str(original_file))).first()
        if not file_record:
            file_record = File(filename=original_file.name, path=str(original_file))
            session.add(file_record)
            session.commit()
            session.refresh(file_record)

        # Store original values and scaling factors for each property
        for prop, values in original_values.items():
            property_record = Property(name=prop, file_id=file_record.id)
            session.add(property_record)
            session.commit()
            session.refresh(property_record)

            # Store original values
            for value in values:
                original_value = OriginalValue(property_id=property_record.id, value=value)
                session.add(original_value)

            # Store 2K scaling factors
            if prop in scale_2k:
                scaling_2k = ScalingFactor(
                    property_id=property_record.id,
                    resolution="2K",
                    **scale_2k[prop]
                )
                session.add(scaling_2k)

            # Store 4K scaling factors
            if prop in scale_4k:
                scaling_4k = ScalingFactor(
                    property_id=property_record.id,
                    resolution="4K",
                    **scale_4k[prop]
                )
                session.add(scaling_4k)

        session.commit()


# ==============================================================#
#        Caller function for comparing positional values        #
# ==============================================================#


def calculate_scaling_factors(
    original_directory: Path,
    scaled_2k_directory: Path,
    scaled_4k_directory: Path,
    input_format: str,
) -> None:
    """
    Calculates scaling factors for text files by comparing original files with their 2K and 4K counterparts.

    This function reads original text files, their 2K and 4K scaled versions, and calculates
    scaling factors for individual properties and overall scaling factors for each resolution.
    The results are stored in a SQLite database.

    Args:
    ----
    - original_directory (Path): The directory containing the original GUI files.
    - scaled_2k_directory (Path): The directory containing the 2K scaled GUI files.
    - scaled_4k_directory (Path): The directory containing the 4K scaled GUI files.
    - input_format (str): The file extension of input GUI files (e.g., 'gui', 'xml').
    - output_directory (Path): The directory where output files will be written.

    Returns:
    -------
    - None

    Raises:
    ------
    - FileNotFoundError: If no matching files are found in the directories.
    - Exception: If an unexpected error occurs during processing.
    """
    log.info("Calculating scaling factors for %s files...", input_format.lower())

    try:
        # Use a ProcessPoolExecutor to run the worker function in parallel.
        original_files = list(original_directory.rglob(f"*.{input_format.lower()}"))
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            args = [
                (
                    original_file,
                    scaled_2k_directory / original_file.relative_to(original_directory),
                    scaled_4k_directory / original_file.relative_to(original_directory),
                )
                # Only include files that have both 2K and 4K scaled versions.
                for original_file in original_files
                if (scaled_2k_directory / original_file.relative_to(original_directory)).exists()
                and (scaled_4k_directory / original_file.relative_to(original_directory)).exists()
            ]
            list(executor.map(calculate_scaling_factors_worker, args, chunksize=10))

        log.info("Scaling factors calculated and stored in the database.")

    except FileNotFoundError as error:
        log.exception("No matching %s files found in the directories.", input_format.upper(), exc_info=error)
    except Exception as error:
        log.exception("An unexpected error occurred while calculating scaling factors.", exc_info=error)


# ==============================================================#
#            New function for scaling file contents             #
# ==============================================================#


def scale_file_contents(file_path: Path, resolution: str) -> str:
    """
    Scales positional values in a text file based on stored scaling factors.

    This function reads the file, identifies positional properties, and applies
    scaling factors from the database based on the resolution.

    Args:
    ----
    - file_path (Path): The path to the text file.
    - resolution (str): The target resolution (e.g., "2K", "4K").

    Returns:
    -------
    - str: The scaled content of the file.

    Raises:
    ------
    - Exception: If an error occurs during file processing or database interaction.
    """
    try:
        # Read the content of the file.
        content = file_utils.read_file(file_path)

        if content is not None:
            # Extract positional values from the file.
            original_values = extract_positional_values(file_path)

            # Apply scaling factors to the values
            scaled_content = apply_scaling_factors(content, original_values, resolution)

            return scaled_content

        else:
            # Skip to the next file if no content is found.
            log.error("No content found in file: %s", file_path)

    except Exception as error:
        log.exception("An unexpected error occurred while scaling file: %s", file_path, exc_info=error)


def apply_scaling_factors(content: str, original_values: dict[str, list[float]], resolution: str) -> str:
    """
    Applies scaling factors to the content of a text file.

    This function iterates through the original values and applies scaling factors
    from the database based on the resolution.

    Args:
    ----
    - content (str): The content of the text file.
    - original_values (dict[str, list[float]]): Original positional values for the file.
    - resolution (str): The target resolution (e.g., "2K", "4K").

    Returns:
    -------
    - str: The content with scaled positional values.

    Raises:
    ------
    - Exception: If an error occurs during database interaction.
    """
    try:
        with Session(engine) as session:
            # Identify properties and apply scaling factors
            for prop, values in original_values.items():
                # Retrieve scaling factors for the property and resolution
                scaling_factor = (
                    session.exec(
                        select(ScalingFactor).where(
                            ScalingFactor.property_id == Property.id,
                            Property.name == prop,
                            ScalingFactor.resolution == resolution,
                        )
                    )
                    .join(Property)
                    .first()
                )

                # Apply scaling factor if found
                if scaling_factor:
                    # Calculate scaled values
                    scaled_values = [round(v * scaling_factor.mean) for v in values]

                    # Update the content with scaled values
                    content = re.sub(
                        rf"\b{prop}\b\s*=\s*({[^}]+}|-?\d+(?:\.\d+)?%?|[^}\n]+)",
                        lambda m: f"{prop} = {m.group(1) if m.group(1) == '-1' or any(x in m.group(1) for x in ['%', '@', '10s']) else scaled_values.pop(0)}",
                        content,
                        flags=re.IGNORECASE,
                    )

        return content

    except Exception as error:
        log.exception("An unexpected error occurred while applying scaling factors.", exc_info=error)


# ============================================================#
#        Updated caller function for scaling positional values        #
# ============================================================#


def scale_positional_values(
    input_directory: Path, output_directory: Path, input_format: str, resolution: str
) -> None:
    """
    Scales relevant positional values in text files according to a specified scaling factor.

    This function reads text files from the input directory, applies a scaling factor to
    specific positional attributes, and writes the modified content to the output directory.

    Args:
    ----
    - input_directory (Path): The directory containing the GUI files to process.
    - output_directory (Path): The directory to output processed files.
    - input_format (str): The file extension of input GUI files (e.g., 'xml', 'ui').
    - resolution (str): The target resolution (e.g., "2K", "4K").

    Returns:
    -------
    - None

    Raises:
    ------
    - FileNotFoundError: If no images are found in the input directory.
    - ValueError: If an invalid scaling factor is provided.
    - Exception: If an unexpected error occurs.
    """
    log.info("Scaling positional values in text files for %s resolution...", resolution)

    try:
        # Use a ProcessPoolExecutor to run the worker function in parallel.
        input_files = list(input_directory.rglob(f"*.{input_format.lower()}"))
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            for input_file in input_files:
                # Scale file contents
                scaled_content = scale_file_contents(input_file, resolution)

                if scaled_content is not None:
                    # Calculate the relative output path to maintain directory structure.
                    relative_path = input_file.relative_to(input_directory)
                    output_path = output_directory / relative_path.parent

                    # Write the scaled content to the output file
                    output_path.mkdir(parents=True, exist_ok=True)
                    output_file = output_path / input_file.name
                    file_utils.write_file(output_file, scaled_content)
                    log.debug("Updated %s with scaled values.", output_file.name)

                else:
                    log.debug("No changes have been made to %s.", input_file.name)

    except FileNotFoundError as error:
        log.exception("No %s files found in %s.", input_format.upper(), input_directory, exc_info=error)
        sys.exit()
    except ValueError as error:
        log.exception("'%s' is not a valid scaling factor.", scale_factor, exc_info=error)
        sys.exit()
    except Exception as error:
        log.exception("An unexpected error occurred.", exc_info=error)
```

**Key Changes:**

- **Error Handling - We've added `try...except` blocks around potentially error-prone sections in functions like `scale_positional_values_worker`, `scale_file_contents`, and `apply_scaling_factors`.
  - We're using `log.exception` to log detailed error messages along with the stack trace, making it easier to debug issues.
  - In cases where the error is critical and the process should terminate, we use `sys.exit()`.
- **Logging:**

  - We've added `log.info`, `log.debug`, `log.warning`, and `log.error` statements to provide informative logging messages throughout the code.
  - This will help us track the progress of the scaling process and identify any potential issues.

**Further Considerations:**

- **Custom Error Classes:** You could create custom error classes for specific types of errors (e.g., `DatabaseError`, `FileReadError`) to make error handling more organized.
- **Logging Levels:** You can use different logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) to control the verbosity of logging messages.
- **Logging Configuration:** You can configure the logging system to specify the output format, destination (file, console), and other settings.

Now, with error handling and logging in place, we have a more robust and informative scaling solution.

Let's move on to the next step in the action plan: creating database utility functions.