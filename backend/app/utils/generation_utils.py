# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides functions for loading and processing LLM prompts and pipeline settings.

This module offers utilities for loading YAML files, extracting specific prompts or settings,
and converting them into formats suitable for LLM input or pipeline configuration.
"""

from pathlib import Path
from typing import Any

import diffusers
import structlog

from app.utils import file_utils

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)


# ================================================= #
#                 Text Generation                   #
# ================================================= #


def load_llm_prompt(
    file_path: str, prompt_name: str, replacements: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """
    Load, format, and customize an LLM prompt from a YAML file.

    Process:
    -------
    -------
        - Loads YAML content from the specified file path.
        - Extracts the prompt with the given name from the YAML data.
        - Converts the prompt data into a message list format for LLM input.
        - Applies placeholder replacements if provided.

    Args:
    ----
    ----
        - file_path (str): Path to the YAML file containing the prompt.
        - prompt_name (str): Name of the specific prompt to extract from the YAML file.
        - replacements (dict[str, str], optional): Dictionary of placeholders and their replacements.

    Returns:
    -------
    -------
        - list[dict[str, Any]]: A list of dictionaries in the format required for LLM input.

    Exceptions:
    ----------
    ----------
        - ValueError: Raised when the YAML file is not found, parsing errors occur, or the prompt is not found.
    """
    try:
        # Load YAML content.
        yaml_content = file_utils.load_yaml(file_path)

        # Extract the specified prompt.
        prompt_data = file_utils.extract_key(yaml_content, prompt_name)

        # Convert to message list format and apply replacements.
        messages = file_utils.convert_to_message_list(prompt_data, replacements)

    except ValueError as error:
        log.exception("Invalid pipeline name: '%s'.", prompt_name, exc_info=error)
        raise

    else:
        return messages


# ================================================== #
#                 Image Generation                   #
# ================================================== #


def load_pipeline_settings(file_path: Path, pipeline_name: str) -> dict[str, Any]:
    """
    Load pipeline settings from a YAML file.

    Process:
    -------
    -------
        - Loads the YAML content from the specified file path.
        - Extracts the settings for the given pipeline name from the YAML content.
        - Converts the string representation of the diffusion pipeline class to the actual class object.

    Args:
    ----
    ----
        - file_path (Path): The path to the YAML file containing pipeline settings.
        - pipeline_name (str): The name of the pipeline whose settings should be loaded.

    Returns:
    -------
    -------
        - dict[str, Any]: A dictionary containing the settings for the specified pipeline.

    Exceptions:
    ----------
    ----------
        - ValueError: Raised if the provided pipeline name is invalid or not found in the YAML file.
    """
    try:
        # Load YAML content.
        yaml_content = file_utils.load_yaml(file_path)

        # Extract the specified setting.
        pipeline_settings = file_utils.extract_key(yaml_content, pipeline_name)

        # Convert the diffusion_pipeline string to the actual class
        pipeline_class_name = pipeline_settings["diffusion_pipeline"]
        pipeline_settings["diffusion_pipeline"] = getattr(diffusers, pipeline_class_name)

    except ValueError as error:
        log.exception("Invalid pipeline name: '%s'.", pipeline_name, exc_info=error)
        raise

    else:
        return pipeline_settings
