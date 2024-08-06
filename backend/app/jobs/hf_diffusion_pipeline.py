# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides functions for generating images using Huggingface diffusion pipelines.

This module offers a function to set up and configure a Huggingface diffusion pipeline
for optimal performance, as well as a function to generate images using the configured
pipeline based on input parameters and settings.
"""

import os
import subprocess
from typing import Any

import structlog
import torch
from diffusers import DiffusionPipeline
from dotenv import load_dotenv

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)

# Load environment variables.
load_dotenv()
os.environ["HUGGINGFACE_TOKEN"] = os.getenv("HUGGINGFACE_TOKEN")


# ======================================================== #
#                 Pipeline Configuration                   #
# ======================================================== #


def setup_pipeline(diffusion_pipeline: DiffusionPipeline, model_id: str) -> DiffusionPipeline:
    """
    Set up and configure the diffusion pipeline.

    Process:
    -------
    -------
        - Loads a pre-trained diffusion model.
        - Sets up performance optimizations for PyTorch.
        - Configures the pipeline for optimal performance on the available hardware.

    Args:
    ----
    ----
        - diffusion_pipeline (DiffusionPipeline): The diffusion pipeline that is to be used.
        - model_id (str): The string pointing at the relevant Huggingface of the chosen pipeline.

    Returns:
    -------
    -------
        - DiffusionPipeline: The configured and optimized pipeline object.

    Exceptions:
    ----------
    ----------
        - RuntimeError: Raised when there's an issue loading or configuring the model.
        - ValueError: Raised when invalid configuration parameters are provided.
    """
    try:
        # Use CUDA if available
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load and configure the pipeline
        pipeline = diffusion_pipeline.from_pretrained(model_id, torch_dtype=torch.float16).to(device)
        pipeline.set_progress_bar_config(disable=True)

        # Set up performance optimizations
        torch.set_float32_matmul_precision("high")
        torch._inductor.config.conv_1x1_as_mm = True
        torch._inductor.config.coordinate_descent_tuning = True
        torch._inductor.config.epilogue_fusion = False
        torch._inductor.config.coordinate_descent_check_all_directions = True

        # Apply CUDA-specific optimizations
        if device == "cuda":
            pipeline.transformer.to(memory_format=torch.channels_last)
            pipeline.vae.to(memory_format=torch.channels_last)
            pipeline.transformer = torch.compile(pipeline.transformer, mode="max-autotune", fullgraph=True)
            pipeline.vae.decode = torch.compile(pipeline.vae.decode, mode="max-autotune", fullgraph=True)

    except RuntimeError as error:
        log.exception("Error setting up the diffusion pipeline.", exc_info=error)
        raise
    except ValueError as error:
        log.exception("Invalid configuration parameters.", exc_info=error)
        raise

    else:
        return pipeline


# =============================================== #
#                 Main Function                   #
# =============================================== #


def huggingface_diffusion_pipeline(
    input_parameters: tuple[int | str, str], settings: dict[str, Any]
) -> tuple[int | str, str]:
    """
    Generate images using a Huggingface diffusion pipeline based on YAML settings.

    Process:
    -------
    -------
        - Authenticates with Huggingface using a provided token.
        - Extracts settings from the provided YAML configuration.
        - Sets up the diffusion pipeline based on the chosen model and settings.
        - Generates images for each prompt in the input parameters.
        - Encodes the generated images as Base64 strings and returns them along with their identifiers.

    Args:
    ----
    ----
        - input_parameters (tuple[int | str, str]): A tuple of input parameters, where each element is a tuple
          containing an identifier and a prompt.
        - settings (dict[str, Any]): A dictionary containing settings for the diffusion pipeline, including model ID,
          inference steps, image dimensions, and guidance scale.

    Returns:
    -------
    -------
        - tuple[int | str, str]: A tuple of results, where each element is a tuple containing an identifier
          and the Base64-encoded generated image.

    Exceptions:
    ----------
    ----------
        - subprocess.CalledProcessError: Raised if Huggingface authentication fails.
        - torch.cuda.OutOfMemoryError: Raised if a CUDA out-of-memory error occurs.
        - RuntimeError: Raised if an error occurs while setting up the diffusion pipeline.
        - ValueError: Raised if invalid configuration parameters are provided.
        - OSError: Raised if an error occurs while saving generated images.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        # Huggingface authentication
        huggingface_login = "huggingface-cli login --token $HUGGINGFACE_TOKEN"
        subprocess.run(huggingface_login, check=True, shell=True)

        # Extract settings
        diffusion_pipeline = settings["diffusion_pipeline"]
        model_id = settings["model_id"]
        num_inference_steps = settings["num_inference_steps"]
        height = settings["height"]
        width = settings["width"]
        guidance_scale = settings["guidance_scale"]

        # Set up the diffusion pipeline
        pipeline = setup_pipeline(diffusion_pipeline=diffusion_pipeline, model_id=model_id)

        # Generate images
        results = []
        for input_tuples in input_parameters:
            for identifier, prompt in input_tuples:
                generated_image = pipeline(
                    prompt=prompt,
                    num_inference_steps=num_inference_steps,
                    height=height,
                    width=width,
                    guidance_scale=guidance_scale,
                ).images[0]

                # Store the generated image as a Base64-encoded string, together with its identifier
                results.append((identifier, generated_image))

    except subprocess.CalledProcessError as error:
        log.exception("Huggingface authentication failed.", exc_info=error)
        raise
    except torch.cuda.OutOfMemoryError as error:
        log.exception("CUDA 'out of memory' error.", exc_info=error)
        raise
    except RuntimeError as error:
        log.exception("Error setting up the diffusion pipeline.", exc_info=error)
        raise
    except ValueError as error:
        log.exception("Invalid configuration parameters.", exc_info=error)
        raise
    except OSError as error:
        log.exception("Error saving generated images.", exc_info=error)
        raise
    except Exception as error:
        log.exception("An unexpected error occurred.", exc_info=error)
        raise

    else:
        return results
