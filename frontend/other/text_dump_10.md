You're right, let's refactor our code thoroughly.  We'll break down the refactoring into several steps to ensure clarity and comprehensiveness.

**Step 1:  Extract Common Logic into Helper Functions**

We'll start by identifying common logic that can be extracted into helper functions to improve code reusability and readability.

**1.1.  Extracting Value Scaling Logic:**

```python
def scale_value(match: re.Match, scale_factor: float) -> str:
    """
    Scales a matched value according to the scaling factor.

    Args:
    ----
    - match (re.Match): A regex match object containing the property and value.
    - scale_factor (float): The scaling factor to apply.

    Returns:
    -------
    - str: A string with the scaled value in the format "property = scaled_value",
        or the original string if the value is "-1".
    """
    prop = match.group(1)
    value = match.group(2).strip()

    # Return the original string if value contains '%', '@', '10s', or is "-1".
    if any(x in value for x in ["%", "@", "10s"]) or value == "-1":
        return f"{prop} = {value}"

    # Handle complex size format, e.g.: size = {x = 5 y = 5}.
    if value.startswith("{"):
        return f"{prop} = " + re.sub(
            r"([\w_]+)\s*=\s*(-?\d+(?:\.\d+)?)",
            lambda m: f"{m.group(1)} = {m.group(2) if m.group(2) == '-1' or any(x in m.group(2) for x in ['%', '@', '10s']) else round(float(m.group(2)) * scale_factor)}",
            value,
        )

    # Handle simple size format, e.g.: size = 17.
    try:
        scaled_value = round(float(value) * scale_factor)
    # Return original if not a number.
    except ValueError:
        return f"{prop} = {value}"
    else:
        return f"{prop} = {scaled_value}"
```

- We've extracted the logic for scaling a single value (`scale_value`) into a separate function. This function now takes the `scale_factor` as an argument, making it more flexible.

**1.2.  Extracting Content Processing Logic:**

```python
def process_content(content: str, scale_factor: float) -> str:
    """
    Scales specific values in the content according to the scaling factor.

    Args:
    ----
    - content (str): The content of a text file.
    - scale_factor (float): The scaling factor to apply.

    Returns:
    -------
    - str: The content with scaled positional values.
    """
    # Regular expression to match & scale positional properties and their values.
    pattern = r"(\b(?:x|y|width|height|maxWidth|maxHeight|size|borderSize|spacing|position|pos_x)\b)\s*=\s*({[^}]+}|-?\d+(?:\.\d+)?%?|[^}\n]+)"

    return re.sub(pattern, lambda m: scale_value(m, scale_factor), content, flags=re.IGNORECASE)
```

- We've extracted the logic for scaling the entire content (`process_content`) into a separate function. This function now takes the `scale_factor` as an argument, making it more flexible.

**Step 2:  Refactoring `scale_positional_values_worker`**

We'll now refactor the `scale_positional_values_worker` function to use the newly extracted helper functions.

```python
def scale_positional_values_worker(args: tuple) -> str:
    """
    Worker function for scaling positional values in text files.

    This function processes a single text file, scaling specific positional attributes
    according to a provided scaling factor. It then writes the modified content to the
    output directory.

    Args:
    ----
    - args (tuple): A tuple containing the following arguments:
        - input_file (Path): The input text file.
        - input_directory (Path): The directory containing the input text files.
        - output_directory (Path): The directory to output processed files.
        - scale_factor (float): The scaling factor to apply to positional values.

    Returns:
    -------
    - None

    Raises:
    ------
    - PermissionError: If there's a permission issue when accessing files.
    - OSError: If there's an operating system related error.
    - Exception: For any other unexpected errors during processing.
    """
    input_file, input_directory, output_directory, scale_factor = args

    try:
        # Read the content of the copied file.
        content = file_utils.read_file(input_file)

        if content is not None:
            # Calculate the relative output path to maintain directory structure.
            relative_path = input_file.relative_to(input_directory)
            output_path = output_directory / relative_path.parent

            # Process the content and scale positional attributes.
            updated_content = process_content(content, scale_factor)
            if content != updated_content:
                output_path.mkdir(parents=True, exist_ok=True)
                output_file = output_path / input_file.name
                file_utils.write_file(output_file, updated_content)
                log.debug("Updated %s with scaled values.", output_file.name)

            else:
                log.debug("No changes have been made to %s.", input_file.name)

        else:
            # Skip to the next file if no content is found.
            log.error("No content found in file: %s", input_file)

    except PermissionError as error:
        log.exception("Permission denied when accessing file: %s", input_file, exc_info=error)
        sys.exit()
    except OSError as error:
        log.exception("OS error while processing file: %s", input_file, exc_info=error)
    except Exception as error:
        log.exception("Unexpected error while processing file: %s", input_file, exc_info=error)
```

- We've replaced the inline scaling logic with a call to `process_content`, which now handles the scaling using the extracted helper functions.

**Step 3:  Refactoring `apply_scaling_factors`**

We'll refactor the `apply_scaling_factors` function to use the extracted `scale_value` function.

```python
def apply_scaling_factors(content: str, original_values: dict[str, list[float]], resolution: str) -> str:
    """
    Applies scaling factors to the content of a text file.

    This function iterates through the original values and applies scaling factors
    from the database based on the resolution.

    Args:
    ----
    - content (str): The content of the text file.
    - original_values (dict[str, list[float]]): Original positional values for the file.
    - resolution (str): The target resolution (e.g., "2K", "4K").

    Returns:
    -------
    - str: The content with scaled positional values.

    Raises:
    ------
    - Exception: If an error occurs during database interaction.
    """
    try:
        with Session(engine) as session:
            # Identify properties and apply scaling factors
            for prop, values in original_values.items():
                # Retrieve scaling factors for the property and resolution
                scaling_factor = (
                    session.exec(
                        select(ScalingFactor).where(
                            ScalingFactor.property_id == Property.id,
                            Property.name == prop,
                            ScalingFactor.resolution == resolution,
                        )
                    )
                    .join(Property)
                    .first()
                )

                # Apply scaling factor if found
                if scaling_factor:
                    # Calculate scaled values
                    scaled_values = [round(v * scaling_factor.mean) for v in values]

                    # Update the content with scaled values
                    # Optimized regex for better performance
                    content = re.sub(
                        rf"\b{prop}\b\s*=\s*(?:{{[^}]+}}|-?\d+(?:\.\d+)?%?|[^}\n]+)",
                        lambda m: scale_value(m, scaling_factor.mean),
                        content,
                        flags=re.IGNORECASE,
                    )

        return content

    except Exception as error:
        log.exception("An unexpected error occurred while applying scaling factors.", exc_info=error)
```

- We've replaced the inline scaling logic with a call to `scale_value`, which now handles the scaling using the extracted helper function.

**Next Steps:**

- We'll continue refactoring in subsequent responses, focusing on improving the structure and organization of the code.

Let me know if you have any questions!