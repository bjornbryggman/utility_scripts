# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides a collection of utility functions for file I/O, directory management, and YAML processing.

This module offers a variety of utility functions that can be used across the project. It includes
functions for reading and writing files, creating and deleting directories, encoding and decoding
images as base64 strings, and working with YAML data.

These functions aim to provide a centralized and reusable set of tools for common file and data
manipulation tasks.
"""

import base64
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

import structlog
import yaml

log = structlog.stdlib.get_logger(__name__)

# =========================================================== #
#                 Generic Utility Functions                   #
# =========================================================== #


def read_file(file_path: Path) -> str:
    """
    Read the content of a file with multiple encoding attempts.

    Process:
    -------
    -------
        - Attempts to read the file using a list of encodings (UTF-8, Latin-1, ASCII) in order.
        - If all text encodings fail, tries to read the file in binary mode and decode it with UTF-8.

    Args:
    ----
    ----
        - file_path (Path): The path to the file to read.

    Returns:
    -------
    -------
        - str: The content of the file as a string, or None if all read attempts fail.

    Exceptions:
    ----------
    ----------
        - PermissionError: Raised if the process lacks permission to read the file.
        - OSError: Raised if an I/O related error occurs during file reading.
        - Exception: Raised for any other unexpected errors during the read operation.
    """
    encodings = ["utf-8", "latin-1", "ascii"]

    # Use 'utf-8' encoding as default, with 'latin-1' and 'ascii' as fallbacks.
    for encoding in encodings:
        try:
            with Path(file_path).open("r", encoding=encoding) as file:
                return file.read()

        except UnicodeDecodeError:
            continue
        except PermissionError as error:
            log.exception("Permission denied for file '%s'.", file_path.name, exc_info=error)
        except OSError as error:
            log.exception("I/O error occurred for file '%s'.", file_path.name, exc_info=error)
        except Exception as error:
            log.exception("An unexpected error occurred for file '%s'.", file_path.name, exc_info=error)

    # If all text encodings fail, try to read as binary.
    try:
        with Path(file_path).open("rb") as file:
            return file.read().decode("utf-8", errors="replace")
    except Exception as error:
        log.exception("Failed to read file even in binary mode: '%s'.", file_path.name, exc_info=error)


def write_file(file_path: Path, content: str) -> None:
    """
    Write content to a file with multiple encoding attempts.

    Process:
    -------
    -------
        - Attempts to write content to the file using a list of encodings ('utf-8', 'latin-1', 'ascii').
        - If all text encodings fail, attempts to write the content in binary mode with 'utf-8' encoding.

    Args:
    ----
    ----
        - file_path (Path): The path to the file to write.
        - content (str): The content to write to the file.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - PermissionError: If the process lacks permission to write to the file.
        - OSError: If an I/O related error occurs during file writing.
        - Exception: For any other unexpected errors during the write operation.
    """
    encodings = ["utf-8", "latin-1", "ascii"]

    # Use 'utf-8' encoding as default, with 'latin-1' and 'ascii' as fallbacks.
    for encoding in encodings:
        try:
            with Path(file_path).open("w", encoding=encoding) as file:
                file.write(content)

        except UnicodeEncodeError:
            continue
        except PermissionError as error:
            log.exception("Permission denied for file '%s'.", file_path.name, exc_info=error)
        except OSError as error:
            log.exception("I/O error occurred for file '%s'.", file_path.name, exc_info=error)
        except Exception as error:
            log.exception("An unexpected error occurred for file '%s'.", file_path.name, exc_info=error)

    # If all text encodings fail, try to write as binary.
    try:
        with Path(file_path).open("wb") as file:
            file.write(content.encode("utf-8", errors="replace"))
    except Exception as error:
        log.exception("Failed to write file even in binary mode: '%s'.", file_path.name, exc_info=error)


def unzip_files(input_directory: Path, output_directory: Path) -> None:
    """
    Finds ZIP files in a directory, extracts them, and moves the extracted files to a specified output folder.

    Process:
    -------
    -------
        - Iterates through all ZIP files within the input directory and its subdirectories.
        - Determines the immediate subdirectory containing the ZIP file.
        - Creates the corresponding subdirectory within the output directory.
        - Extracts the contents of the ZIP file into the designated output subdirectory.

    Args:
    ----
    ----
        - input_directory (Path): The directory containing the ZIP files.
        - output_directory (Path): The directory where extracted files will be moved.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - FileNotFoundError: If the input directory does not exist.
        - PermissionError: If there's a permission issue when accessing files.
        - OSError: If an I/O error occurs during file operations.
        - Exception: If an unexpected error occurs.
    """
    try:
        for zip_file in input_directory.rglob("*.zip"):
            # Find the subdirectory of input_directory that contains this ZIP.
            relative_path = zip_file.relative_to(input_directory)
            immediate_subdir = relative_path.parts[0]

            # Set the output path to this immediate subdirectory.
            output_path = output_directory / immediate_subdir
            output_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(output_path)
                log.debug("Extracted files from %s to %s", zip_file, output_path)

    except FileNotFoundError as error:
        log.exception("No .zip files found in %s, skipping...", input_directory, exc_info=error)
    except PermissionError as error:
        log.exception("Permission denied when accessing file: %s", input_directory, exc_info=error)
        sys.exit()
    except OSError as error:
        log.exception("Error processing %s.", input_directory, exc_info=error)
        raise
    except Exception as error:
        log.exception("Unexpected error processing %s.", input_directory, exc_info=error)
        raise


# ========================================================= #
#                 Image Utility Functions                   #
# ========================================================= #


def get_base64_encoded_image(file_path: Path) -> str:
    """
    Encode an image file as a base64-encoded string.

    Process:
    -------
    -------
        - Reads the image file from the specified path.
        - Encodes the binary image data using base64 encoding.
        - Decodes the encoded data into a UTF-8 string and returns it.

    Args:
    ----
    ----
        - file_path (str): The path to the image file to be encoded.

    Returns:
    -------
    -------
        - str: The base64-encoded string representation of the image data.

    Exceptions:
    ----------
    ----------
        - None.
    """
    with Path(file_path).read_bytes() as image_file:
        binary_data = image_file.read()
        base_64_encoded_data = base64.b64encode(binary_data)
        return base_64_encoded_data.decode("utf-8")


def save_base64_decoded_image(base64_string: str, output_path: Path) -> None:
    """
    Decode a base64-encoded string and save it as an image file.

    Process:
    -------
    -------
        - Encodes the input string as UTF-8.
        - Decodes the base64-encoded data into binary.
        - Writes the binary data to the specified output file path.

    Args:
    ----
    ----
        - base64_string (str): The base64-encoded string representation of the image data.
        - output_path (Path): The path where the decoded image will be saved.

    Returns:
    -------
    -------
        - None

    Exceptions:
    ----------
    ----------
        - None.
    """
    binary_data = base64.b64decode(base64_string.encode("utf-8"))
    with Path(output_path).open("wb") as image_file:
        image_file.write(binary_data)


# ============================================================= #
#                 Directory Utility Functions                   #
# ============================================================= #


def create_directory(directory: Path) -> None:
    """
    Create a directory if it doesn't exist.

    Process:
    -------
    -------
        - Attempts to create the specified directory using `mkdir` with `parents=True` and `exist_ok=True`.
        - Logs a debug message indicating the directory's existence or creation.

    Args:
    ----
    ----
        - directory (Path): The path to the directory to be created.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - PermissionError: Raised if permission is denied to create the directory.
        - OSError: Raised if an I/O error occurs during directory creation.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        log.debug("Directory %s exists or has been created.", directory)

    except PermissionError as error:
        log.exception("Permission denied", exc_info=error)
    except OSError as error:
        log.exception("I/O error occurred.", exc_info=error)
    except Exception as error:
        log.exception("An unexpected error occurred.", exc_info=error)


def delete_directory(directory: Path) -> None:
    """
    Delete a directory if it exists.

    Process:
    -------
    -------
        - Checks if the specified directory exists.
        - If it exists, uses shutil.rmtree to delete the directory and its contents.

    Args:
    ----
    ----
        - directory (Path): The directory to be deleted.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - PermissionError: Raised if permission is denied to delete the directory.
        - OSError: Raised if an I/O error occurs during the deletion process.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        if directory.exists():
            shutil.rmtree(directory)
            log.debug("Deleted the %s directory.", directory)

    except PermissionError as error:
        log.exception("Permission denied", exc_info=error)
    except OSError as error:
        log.exception("I/O error occurred.", exc_info=error)
    except Exception as error:
        log.exception("An unexpected error occurred.", exc_info=error)


# ======================================================== #
#                 YAML Utility Functions                   #
# ======================================================== #


def load_yaml(file_path: Path) -> dict[str, Any]:
    """
    Load and parse a YAML file, returning its contents as a dictionary.

    Process:
    -------
    -------
        - Opens the specified YAML file in read mode with locale encoding.
        - Parses the file content using `yaml.safe_load`.
        - Returns the parsed content as a dictionary.

    Args:
    ----
    ----
        - file_path (Path): The path to the YAML file to be loaded and parsed.

    Returns:
    -------
    -------
        - dict[str, Any]: A dictionary containing the parsed contents of the YAML file.

    Exceptions:
    ----------
    ----------
        - FileNotFoundError: Raised when the specified file cannot be found.
        - yaml.YAMLError: Raised when there's an error parsing the YAML content.
    """
    try:
        # Open and parse the YAML file.
        with Path(file_path).open("r", encoding="locale") as file:
            return yaml.safe_load(file)

    except FileNotFoundError as error:
        log.exception("'%s' file not found.", file_path.name, exc_info=error)
        raise
    except yaml.YAMLError as error:
        log.exception("Error parsing YAML file: '%s'.", file_path.name, exc_info=error)
        raise


def extract_key(yaml_content: dict[str, Any], key_name: str) -> list[dict[str, Any]]:
    """
    Extract a specific prompt from parsed YAML content.

    Process:
    -------
    -------
        - Attempts to retrieve the prompt data associated with the given key_name from the yaml_content dictionary.
        - If the key is found, returns the corresponding prompt data.

    Args:
    ----
    ----
        - yaml_content (dict[str, Any]): The parsed YAML content containing prompts.
        - key_name (str): The name of the specific prompt to extract.

    Returns:
    -------
    -------
        - list[dict[str, Any]]: The extracted prompt data.

    Exceptions:
    ----------
    ----------
        - ValueError: Raised when the specified prompt is not found in the YAML content.
    """
    try:
        # Extract the specified prompt.
        prompt_data = yaml_content.get(key_name)

    except ValueError as error:
        log.exception("Invalid prompt name: '%s'.", key_name, exc_info=error)
        raise

    else:
        return prompt_data


def replace_placeholders(data: Any, replacements: dict[str, str]) -> Any:
    """
    Replace placeholders in strings, lists, and dictionaries recursively.

    Process:
    -------
    -------
        - If the input data is a string, it replaces all occurrences of placeholders with their corresponding values
          from the `replacements` dictionary.
        - If the input data is a list, it recursively calls itself on each item in the list.
        - If the input data is a dictionary, it recursively calls itself on both the keys and values of the dictionary.
        - For any other data type, the input data is returned unchanged.

    Args:
    ----
    ----
        - data (Any): The input data containing placeholders to be replaced.
        - replacements (dict[str, str]): A dictionary mapping placeholders to their replacement values.

    Returns:
    -------
    -------
        - Any: The input data with all placeholders replaced by their corresponding values.

    Exceptions:
    ----------
    ----------
        - None specific to this function.
    """
    # Replace placeholders in strings.
    if isinstance(data, str):
        for placeholder, replacement in replacements.items():
            data = data.replace(placeholder, str(replacement))
        return data

    # Recursively replace placeholders in list items.
    if isinstance(data, list):
        return [replace_placeholders(item, replacements) for item in data]

    # Recursively replace placeholders in dictionary keys and values.
    if isinstance(data, dict):
        return {replace_placeholders(k, replacements): replace_placeholders(v, replacements) for k, v in data.items()}

    # Return unchanged for other data types.
    return data


def convert_to_message_list(
    prompt_data: list[dict[str, Any]], replacements: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """
    Convert prompt data to message list format and replace placeholders.

    Process:
    -------
        - Iterates through the provided prompt data, extracting roles and content from each item.
        - Applies placeholder replacements to the content if a `replacements` dictionary is provided.
        - Formats each prompt item into a standardized message structure for LLM input, including
          the role and JSON-encoded content.

    Args:
    ----
        - prompt_data (list[dict[str, Any]]): The structured prompt data to be converted.
        - replacements (dict[str, str], optional): Dictionary of placeholders and their replacements.

    Returns:
    -------
        - list[dict[str, Any]]: A list of dictionaries in the format required for LLM input.

    Exceptions:
    ----------
        - None specific to this function.
    """
    message_list = []
    for item in prompt_data:
        for key, value in item.items():
            # Extract role from the key.
            role = key.split("_")[0]

            # Apply replacements if provided.
            if replacements:
                value = replace_placeholders(value, replacements)

            # Format the message.
            message_list.append({"role": role, "content": json.dumps(value, ensure_ascii=False)})

    return message_list
