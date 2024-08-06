# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Insert succinct one-liner here (no more than 60 characters).

Insert more descriptive explanation of the module here, max 4 rows, max 100 characters per row.
"""

import json
import os
import sys
from pathlib import Path

import openai
import requests
import structlog
from dotenv import load_dotenv

from app.api import openrouter_text_generation
from app.core.config import PromptConfig
from app.utils import generation_utils

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)

# Create an instance of the PromptConfig class.
config = PromptConfig()

# Load environment variables.
load_dotenv()
os.environ["OPENAI_API_TOKEN"] = os.getenv("OPENAI_API_KEY")
specific_model = os.getenv("OPENROUTER_TEXT_GOOGLE_GEMINI-1.5_FLASH")


def generate_docstring(llm_model: str, temperature: float, output_path: Path = None) -> None:
    """
    Generate a docstring for the calling function using an LLM.

    Process:
    -------
    -------
        - Loads a pre-defined prompt for docstring generation.
        - Makes an API request to the specified LLM model with the prompt.
        - Parses the response, extracting the generated docstring.
        - Writes the docstring to a Markdown file named after the calling script.

    Args:
    ----
    ----
        - llm_model (str): The identifier for the language model to be used for docstring generation.
        - temperature (float): The temperature parameter for the LLM, controlling the creativity of the generated text.
        - output_path (Path, optional): The path to the output file for the generated docstring. Defaults to None, in which case the docstring is written to a file named after the calling script with a '.md' extension.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - openai.OpenAIError: Raised when an error occurs during API communication with OpenAI.
        - requests.RequestException: Raised when a network-related error occurs during API requests.
        - ValueError: Raised when invalid input parameters are provided.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        # Construct the message list for the API request.
        messages = generation_utils.load_llm_prompt(config.DOCUMENTATION_YAML, "docstring_writer")

        # Make the API request.
        content = openrouter_text_generation.standard_completion_request(
            messages=messages, llm_model=llm_model, temperature=temperature, stream=False
        )

        # Parse the JSON content
        content_list = json.loads(content)
        # The 'docstring' is in the second dictionary of the list
        docstring = content_list[1].get("docstring", "")

        # Get the name of the calling script
        caller_script = Path(sys.argv[0])
        output_path = caller_script.with_suffix(".md")

        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the docstring to the file
        output_path.write_text(docstring)

    except (openai.OpenAIError, requests.RequestException) as error:
        log.exception("API error occurred during text generation.", exc_info=error)
        raise
    except ValueError as error:
        log.exception("Invalid input parameter provided.", exc_info=error)
        raise
    except Exception as error:
        log.exception("An unexpected error occurred during the process execution.", exc_info=error)
        raise


if __name__ == "__main__":
    generate_docstring(llm_model=specific_model, temperature=0.3)
