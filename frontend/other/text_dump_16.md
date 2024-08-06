# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module provides the main script for the text processing application.

It handles the workflow for calculating scaling factors and scaling positional values in text files.
"""

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
    """
    Scales positional values in text files based on stored scaling factors.

    This function reads text files from the input directory, applies scaling factors to
    specific positional attributes based on the target resolution, and writes the modified
    content to the output directory.
    """
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
    """
    Calculates scaling factors for text files by comparing original files with their 2K and 4K counterparts.

    This function reads original text files, their 2K and 4K scaled versions, and calculates
    scaling factors for individual properties and overall scaling factors for each resolution.
    The results are stored in a SQLite database.
    """
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
