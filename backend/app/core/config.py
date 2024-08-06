# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides configuration classes for managing directory paths used in the project.

This module defines several configuration classes that centralize the management
of directory paths used throughout the project. Each class encapsulates paths
related to specific functionalities, such as LLM prompts.
"""

from pathlib import Path

import structlog

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)


# ================================================================== #
#                   Directory Configuration Classes                  #
# ================================================================== #


class BaseConfig:
    """
    Configuration class for basic directory paths.

    Attributes:
    ----------
        - ROOT_PATH (Path):
        - INPUT_DIR (Path): Path to the directory that contains the input files.
        - ERROR_DIR (Path): Path to the directory that stores error files.

        - LOG_DIR (Path): Path to the directory for storing log files.
        - LOG_LEVEL (str): Logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
    """

    def __init__(self) -> None:
        "Initializes the BaseConfig with values from environment variables."
        # Base directories.
        self.ROOT_PATH = Path(__file__).resolve().parent.parent
        self.INPUT_DIR = self.ROOT_PATH / "resources" / "input_directory"
        self.ERROR_DIR = self.ROOT_PATH / "resources" / "error_directory"

        # Logging configuration.
        self.LOG_DIR = self.ROOT_PATH / "log_directory"
        self.LOG_LEVEL = "DEBUG"


class GeographyConfig:
    """
    Configuration class for directory paths used in the 'terrain_script.py'.

    Attributes:
    ----------
        - POSITIONS_TXT (Path):
        - AREA_TXT (Path):
        - REGION_TXT (Path):
        - SUPERREGION_TXT (Path):
        - CONTINENT_TXT (Path):

        - CLIMATE_TXT (Path):
        - TERRAIN_TXT (Path):
    """

    def __init__(self) -> None:
        "Initializes the GeographyConfig."
        # Create an instance of the BaseConfig class.
        self.base_config = BaseConfig()

        # Text files containing geographical entities.
        self.POSITIONS_TXT = self.base_config.INPUT_DIR / "map" / "positions.txt"
        self.AREA_TXT = self.base_config.INPUT_DIR / "map" / "area.txt"
        self.REGION_TXT = self.base_config.INPUT_DIR / "map" / "region.txt"
        self.SUPERREGION_TXT = self.base_config.INPUT_DIR / "map" / "superregion.txt"
        self.CONTINENT_TXT = self.base_config.INPUT_DIR / "map" / "continent.txt"

        # Text files containing weather & terrain information.
        self.CLIMATE_TXT = self.base_config.INPUT_DIR / "map" / "climate.txt"
        self.TERRAIN_TXT = self.base_config.INPUT_DIR / "map" / "terrain.txt"


class PromptConfig:
    """
    Configuration class for file paths used in LLM prompts.

    Attributes:
    ----------
        - something.
    """

    def __init__(self) -> None:
        "Initializes the PromptConfig."
        # Create an instance of the BaseConfig class.
        self.base_config = BaseConfig()

        # Prompt folder.
        self.PROMPT_DIR = self.base_config.ROOT_PATH / "robot"
        self.PROMPT_YAML = self.PROMPT_DIR / "prompts.yaml"
        self.DOCUMENTATION_YAML = self.PROMPT_DIR / "documentation.yaml"
