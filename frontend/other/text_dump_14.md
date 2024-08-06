Okay, here's the third module: `config.py` with detailed documentation.

```python
# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module defines configuration settings for the text processing application.

It provides settings for input/output directories, logging, and other relevant parameters.
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class DirectoryConfig:
    """
    Configuration class for directory paths.

    Attributes:
    -----------
    - INPUT_DIR (Path): Path to the directory containing the input files.
    - OUTPUT_DIR_2K (Path): Path to the directory for outputting 2K scaled files.
    - OUTPUT_DIR_4K (Path): Path to the directory for outputting 4K scaled files.
    - TEXT_COMPARISON_ORIGINAL_DIR (Path): Path to the directory containing original files for scaling factor comparison.
    - TEXT_COMPARISON_DIR_2K (Path): Path to the directory containing 2K scaled files for scaling factor comparison.
    - TEXT_COMPARISON_DIR_4K (Path): Path to the directory containing 4K scaled files for scaling factor comparison.
    - LOG_DIR (Path): Path to the directory for storing log files.
    - LOG_LEVEL (str): Logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
    """

    def __init__(self):
        """
        Initializes the DirectoryConfig with values from environment variables.
        """
        self.INPUT_DIR = Path(os.getenv("INPUT_DIR", "path/to/input_dir"))
        self.OUTPUT_DIR_2K = Path(os.getenv("OUTPUT_DIR_2K", "path/to/output_dir_2k"))
        self.OUTPUT_DIR_4K = Path(os.getenv("OUTPUT_DIR_4K", "path/to/output_dir_4k"))
        self.TEXT_COMPARISON_ORIGINAL_DIR = Path(os.getenv("TEXT_COMPARISON_ORIGINAL_DIR", "path/to/original_dir"))
        self.TEXT_COMPARISON_DIR_2K = Path(os.getenv("TEXT_COMPARISON_DIR_2K", "path/to/scaled_2k_dir"))
        self.TEXT_COMPARISON_DIR_4K = Path(os.getenv("TEXT_COMPARISON_DIR_4K", "path/to/scaled_4k_dir"))
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

```

We've added a docstring to the `DirectoryConfig` class, explaining its purpose, attributes, and initialization process. We've also documented the use of environment variables for setting configuration values.

Let's move on to the next module.