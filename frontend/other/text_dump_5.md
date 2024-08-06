Right, let's update the main script (`main.py`) to use the new database-driven scaling workflow.

Here's the updated `main.py` code:

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
    text_processing.calculate_scaling_factors(
        config.TEXT_COMPARISON_ORIGINAL_DIR,
        config.TEXT_COMPARISON_DIR_2K,
        config.TEXT_COMPARISON_DIR_4K,
        "GUI",
    )

if __name__ == "__main__":
    text_positional_value_comparison()
    text_positional_value_scaling()
```

**Key Changes:**

- **`text_positional_value_scaling`:**
    - We now call `text_processing.scale_positional_values` with the resolution ("2K" or "4K") as an argument instead of a single scaling factor.
- **`text_positional_value_comparison`:**
    - We've added this function to calculate and store scaling factors in the database.
    - It calls `text_processing.calculate_scaling_factors` to perform the calculation.
- **`if __name__ == "__main__":`:**
    - We now call both `text_positional_value_comparison` and `text_positional_value_scaling` to first calculate the scaling factors and then use them to scale the files.

**Workflow:**

1. **`text_positional_value_comparison`:**
   - Calculates scaling factors for each property in the GUI files, comparing original, 2K, and 4K versions.
   - Stores the scaling factors in the database.
2. **`text_positional_value_scaling`:**
   - Reads the GUI and GFX files from the input directory.
   - Retrieves the appropriate scaling factors from the database based on the resolution.
   - Applies the scaling factors to the files and writes the scaled content to the output directory.

**Next Steps:**

- Implement the remaining steps of the action plan (testing, optimization, documentation).

We have now successfully integrated the database and the new scaling workflow into our main script. The next steps will focus on ensuring the quality and efficiency of our solution.

Let me know if you have any questions or want to proceed with the next step!