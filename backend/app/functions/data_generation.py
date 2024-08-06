# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Insert succinct one-liner here (no more than 60 characters).

Insert more descriptive explanation of the module here, max 4 rows, max 100 characters per row.
"""

import os

import openai
import requests
import structlog
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from app.api import openrouter_text_generation
from app.core.config import PromptConfig
from app.database.models import Province, TerrainImageGenerationPrompt
from app.utils import db_utils, generation_utils

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)

# Create an instance of the PromptConfig class.
config = PromptConfig()

# Load environment variables.
load_dotenv()
os.environ["OPENROUTER_API_TOKEN"] = os.getenv("OPENROUTER_API_KEY")
specific_model = os.getenv("OPENROUTER_TEXT_META_LLAMA-3_70B_NITRO")


# ========================================== #
#               Prompt Generation            #
# ========================================== #


def generate_prompts_for_province_terrain_images(llm_model: str) -> float:
    """
    Generate image prompts for all provinces based on their terrain and climate.

    Process:
    -------
    -------
        - Retrieves all provinces from the database.
        - For each province, generates a custom prompt using its terrain and climate data.
        - Updates the database with the generated prompts.
        - Tracks and returns the total API cost for all operations.

    Args:
    ----
    ----
        - llm_model (str): The identifier for the language model to be used for prompt generation.

    Returns:
    -------
    -------
        - float: The total cost incurred for API calls during the prompt generation process.

    Exceptions:
    ----------
    ----------
        - SQLAlchemyError: Raised when a database-related error occurs.
        - openai.OpenAIError: Raised when an error occurs during API communication with OpenAI.
        - requests.RequestException: Raised when a network-related error occurs during API requests.
        - ValueError: Raised when invalid input parameters are provided.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        # Set up a cost counter.
        total_cost = 0

        # Fetch all provinces.
        with db_utils.session_scope() as session:
            provinces = session.exec(select(Province)).all()
            for province in provinces:
                terrain_value = province.terrain.name
                climate_value = province.climate.name

                # Insert terrain and climate values.
                replacements = {"INSERT_TERRAIN_VALUE_HERE": terrain_value, "INSERT_CLIMATE_VALUE_HERE": climate_value}

                # Construct the message list for the API request.
                messages = generation_utils.load_llm_prompt(
                    config.PROMPT_YAML, "Province_Prompt_Generator", replacements
                )

                # Make the API request.
                llm_response = openrouter_text_generation.structured_completion_request(
                    messages=messages, llm_model=llm_model, pydantic_data_model=TerrainImageGenerationPrompt
                )

                # Process the API response.
                for content, api_cost in llm_response:
                    # Update the province database entry with the generated prompt.
                    province.prompt = content.prompt
                    log.debug("'Prompt' attribute recorded for province '%s'.", province.name)

                    # Update the total_cost counter with the API cost.
                    for number in api_cost:
                        total_cost += number

        # Format the total cost as a string with 10 decimal places.
        cost_string = f"${float(total_cost):.10f}"
        log.info("Total cost for 'generate_prompts_for_province_terrain_images': %s", cost_string)

    except SQLAlchemyError as error:
        log.exception("Database error.", exc_info=error)
        raise
    except (openai.OpenAIError, requests.RequestException) as error:
        log.exception("API error occurred during text generation.", exc_info=error)
        raise
    except ValueError as error:
        log.exception("Invalid input parameter provided.", exc_info=error)
        raise
    except Exception as error:
        log.exception("An unexpected error occurred during the process execution.", exc_info=error)
        raise

    else:
        # Return the total_cost variable.
        return total_cost
