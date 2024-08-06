Okay, let's continue refactoring our code. We'll focus on improving the structure and organization of the code, particularly around the scaling logic.

**Step 4:  Refactoring `scale_positional_values`**

We'll refactor the `scale_positional_values` function to leverage the helper functions we've created and improve its structure.

```python
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

- We've removed the redundant `scale_positional_values_worker` function, as the logic is now handled directly within `scale_positional_values`.

**Step 5:  Refactoring `calculate_scaling_factors`**

We'll refactor the `calculate_scaling_factors` function to use a more descriptive name and improve its structure.

```python
def calculate_and_store_scaling_factors(
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
```

- We've renamed the function to `calculate_and_store_scaling_factors` to better reflect its purpose.

**Step 6:  Refactoring `main.py`**

We'll refactor the `main.py` script to use the new function names and improve its structure.

```python
# Copyright 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

import contextlib
import os
from pathlib import Path

import structlog
from dotenv import load_dotenv

from app.config import DirectoryConfig
from app.functions import text_processing
from app.utils import logging_utils

log = structlog.stdlib.get_logger(__name__)

# Directory configuration, see config.py for more information.
config = DirectoryConfig()

def text_positional_value_scaling() -> None:
    logging_utils.init_logger(config.LOG_LEVEL, config.LOG_DIR)
    log.info("Initiating text processing (scaling) workflow...")

    # Scale positional values in GUI and GFX text files (for 4K monitors).
    text_processing.scale_positional_values(config.INPUT_DIR, config.OUTPUT_DIR_4K, "GUI", "4K")
    text_processing.scale_positional_values(config.INPUT_DIR, config.OUTPUT_DIR_4K, "GFX", "4K")

    # Scale positional values in GUI and GFX text files (for 2K monitors).
    text_processing.scale_positional_values(config.INPUT_DIR, config.OUTPUT_DIR_2K, "GUI", "2K")
    text_processing.scale_positional_values(config.INPUT_DIR, config.OUTPUT_DIR_2K, "GFX", "2K")

# Used to derive an appropriate scaling factor by comparing how other mods (e.g., "Proper 2K UI") did it.
def text_positional_value_comparison() -> None:
    logging_utils.init_logger(config.LOG_LEVEL, config.LOG_DIR)
    log.info("Initiating text processing (scaling) workflow...")

    # Compares positional values between text files (for 4K monitors).
    text_processing.calculate_and_store_scaling_factors(
        config.TEXT_COMPARISON_ORIGINAL_DIR,
        config.TEXT_COMPARISON_DIR_2K,
        config.TEXT_COMPARISON_DIR_4K,
        "GUI",
    )

if __name__ == "__main__":
    text_positional_value_comparison()
    text_positional_value_scaling()
```

- We've updated the function calls in `main.py` to use the new function names.

**Next Steps:**

- We'll continue refactoring in subsequent responses, focusing on improving the structure and organization of the code.

Let me know if you have any questions!