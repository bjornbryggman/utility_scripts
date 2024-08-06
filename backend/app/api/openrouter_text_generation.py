# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides functions for interacting with the OpenRouter API.

This module offers functions for making completion requests to the OpenRouter API
using both standard and structured methods. It also includes a utility function
for querying OpenRouter to retrieve the cost and statistics associated with a
specific generation ID.
"""

import os

import instructor
import openai
import requests
import structlog
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)

# Load environment variables.
load_dotenv()
os.environ["OPENAI_API_TOKEN"] = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ======================================================= #
#                    Standard function                    #
# ======================================================= #


@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
def standard_completion_request(messages: list[dict], llm_model: str, temperature: float, stream: bool) -> tuple:
    """
    Make a standard completion request to the OpenRouter API with retry mechanism.

    Process:
    -------
    -------
        - Sends a chat completion request to the OpenRouter API using the OpenAI client.
        - Handles streaming responses if specified.
        - Returns the generated response from the LLM.

    Args:
    ----
    ----
        - messages (list[dict]): The list of messages to be sent to the LLM.
        - llm_model (str): The identifier of the LLM model to be used.
        - temperature (float): The temperature parameter for controlling the creativity of the LLM.
        - stream (bool): Whether to stream the response as chunks or return the full response at once.

    Returns:
    -------
    -------
        - tuple: A tuple containing the generated response from the LLM.

    Exceptions:
    ----------
    ----------
        - openai.OpenAIError: Raised when an error occurs during API communication with OpenAI.
        - requests.RequestException: Raised when a network-related error occurs during API requests.
        - ValueError: Raised when invalid input parameters are provided.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        log.debug("Calling the OpenRouter API...")

        # Make a synchronous completion request using the OpenAI client.
        client = OpenAI()
        completion = client.chat.completions.create(
            messages=messages,
            model=llm_model,
            temperature=temperature,
            stream=stream,
            extra_query={"transforms": {}, "min_p": {"value": 0.1}},
        )

        # Stream the output as chunks if stream = True.
        if stream:
            chunks = []
            for chunk in completion:
                if not hasattr(completion, "id"):
                    completion.id = chunk.id
                part = chunk.choices[0].delta.content
                chunks.append(part)
            response = "".join(chunks)

        else:
            # Filter the response into a readable format.
            response = completion.choices[0].message.content

        log.debug("OpenRouter completion request successful: %s", completion)

    except openai.OpenAIError as error:
        log.exception("APIError occurred while interacting with the OpenRouter model.", exc_info=error)
    except requests.RequestException as error:
        log.exception("Request to the OpenRouter API failed.", exc_info=error)
    except ValueError as error:
        log.exception("Invalid input parameter provided.", exc_info=error)
    except Exception as error:
        log.exception("An unexpected error occurred during the process execution.", exc_info=error)

    else:
        return response


# ======================================================= #
#                   Structured function                   #
# ======================================================= #


def structured_completion_request(
    messages: list[dict], llm_model: str, pydantic_data_model: BaseModel
) -> tuple[dict, float]:
    """
    Makes a completion request to the OpenRouter API and returns a structured JSON response.

    Process:
    -------
    -------
        - Initializes an OpenAI client in JSON mode.
        - Sends a completion request to the OpenRouter API with the provided messages and model.
        - Extracts the response content and API cost from the completion result.

    Args:
    ----
    ----
        - messages (list[dict]): A list of dictionaries containing the messages for the completion request.
        - llm_model (str): The identifier for the language model to be used for the completion request.
        - pydantic_data_model (BaseModel): The Pydantic data model for the response.

    Returns:
    -------
    -------
        - tuple[dict, float]: A tuple containing the response content as a dictionary and the API cost as a float.

    Exceptions:
    ----------
    ----------
        - openai.OpenAIError: Raised when an error occurs during API communication with OpenAI.
        - requests.RequestException: Raised when a network-related error occurs during API requests.
        - ValueError: Raised when invalid input parameters are provided.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        log.debug("Calling the OpenRouter API...")

        # Make a synchronous completion request using the patched OpenAI client.
        client = instructor.from_openai(OpenAI(), mode=instructor.Mode.JSON)
        completion = client.chat.completions.create(
            messages=messages, model=llm_model, response_model=pydantic_data_model
        )

        # Filter the response into a readable format.
        response = completion.choices[0].message.content

        # Fetch the cost of the API call.
        cost_and_stats = query_cost_and_stats(completion.id, OPENAI_API_KEY)
        api_cost = cost_and_stats.get("total_cost")

        log.debug("OpenRouter completion request successful: %s", completion)

    except openai.OpenAIError as error:
        log.exception("APIError occurred while interacting with the OpenRouter model.", exc_info=error)
    except requests.RequestException as error:
        log.exception("Request to the OpenRouter API failed.", exc_info=error)
    except ValueError as error:
        log.exception("Invalid input parameter provided.", exc_info=error)
    except Exception as error:
        log.exception("An unexpected error occurred during the process execution.", exc_info=error)

    else:
        return (response, api_cost)


# ==================================================== #
#                   Utility function                   #
# ==================================================== #


def query_cost_and_stats(generation_id: str, api_key: str) -> dict:
    """
    Query OpenRouter for the cost and stats associated with a specific generation ID.

    Process:
    -------
    -------
        - Constructs the API URL using the provided generation ID.
        - Sets up headers with the provided API key.
        - Makes a GET request to the OpenRouter API.
        - Extracts the cost data from the JSON response.
        - Returns a dictionary containing the total cost.

    Args:
    ----
    ----
        - generation_id (str): The unique identifier of the generation to query.
        - api_key (str): The API key for accessing OpenRouter.

    Returns:
    -------
    -------
        - dict: A dictionary containing the total cost of the generation, or an empty dictionary if the request fails.

    Exceptions:
    ----------
    ----------
        - requests.RequestException: Raised if an error occurs during the HTTP request to OpenRouter.
    """
    # Construct the API URL with the generation ID.
    api_url = f"https://openrouter.ai/api/v1/generation?id={generation_id}"

    # Set up the headers with the API key.
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Make a GET request to the OpenRouter API.
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Extract the data from the JSON response.
        data = response.json().get("data")

    except requests.exceptions.RequestException:
        log.exception("HTTP Request to OpenRouter failed.")

    else:
        # Return a dictionary with the total cost.
        return {"total_cost": data.get("total_cost")}
