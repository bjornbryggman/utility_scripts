You're right, let's dive into implementing those optimizations and refactoring our code. I'll focus on the `text_processing.py` file, as it's the core of our scaling logic.

**1. Database Optimizations (Batch Operations):**

```python
def store_scaling_factors_in_database(
    original_file: Path,
    original_values: dict[str, list[float]],
    scale_2k: dict[str, dict[str, float]],
    scale_4k: dict[str, dict[str, float]],
) -> None:
    """
    Stores original values and scaling factors in the database.

    Args:
    ----
    - original_file (Path): Path to the original text file.
    - original_values (dict[str, list[float]]): Original positional values for the file.
    - scale_2k (dict[str, dict[str, float]]): Scaling factors for 2K resolution.
    - scale_4k (dict[str, dict[str, float]]): Scaling factors for 4K resolution.

    Returns:
    -------
    - None
    """
    with Session(engine) as session:
        # Create or get the File record
        file_record = session.exec(select(File).where(File.path == str(original_file))).first()
        if not file_record:
            file_record = File(filename=original_file.name, path=str(original_file))
            session.add(file_record)
            session.commit()
            session.refresh(file_record)

        # Store original values and scaling factors for each property
        original_value_records = []
        scaling_factor_2k_records = []
        scaling_factor_4k_records = []
        for prop, values in original_values.items():
            property_record = Property(name=prop, file_id=file_record.id)
            session.add(property_record)
            session.commit()
            session.refresh(property_record)

            # Store original values
            original_value_records.extend(
                [OriginalValue(property_id=property_record.id, value=value) for value in values]
            )

            # Store 2K scaling factors
            if prop in scale_2k:
                scaling_factor_2k_records.append(
                    ScalingFactor(
                        property_id=property_record.id,
                        resolution="2K",
                        **scale_2k[prop]
                    )
                )

            # Store 4K scaling factors
            if prop in scale_4k:
                scaling_factor_4k_records.append(
                    ScalingFactor(
                        property_id=property_record.id,
                        resolution="4K",
                        **scale_4k[prop]
                    )
                )

        session.add_all(original_value_records)
        session.add_all(scaling_factor_2k_records)
        session.add_all(scaling_factor_4k_records)
        session.commit()
```

- We've grouped the creation of `OriginalValue` and `ScalingFactor` records into lists.
- We then use `session.add_all` to add all records in a batch, reducing the number of database interactions.

**2. Code Optimizations (Regular Expression Optimization):**

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
                        lambda m: f"{prop} = {m.group(1) if m.group(1) == '-1' or any(x in m.group(1) for x in ['%', '@', '10s']) else scaled_values.pop(0)}",
                        content,
                        flags=re.IGNORECASE,
                    )

        return content

    except Exception as error:
        log.exception("An unexpected error occurred while applying scaling factors.", exc_info=error)
```

- We've optimized the regex pattern in `re.sub` to be more specific and avoid unnecessary backtracking.

**3. Refactoring (Function Encapsulation):**

```python
def scale_file_contents(file_path: Path, resolution: str) -> str:
    """
    Scales positional values in a text file based on stored scaling factors.

    This function reads the file, identifies positional properties, and applies
    scaling factors from the database based on the resolution.

    Args:
    ----
    - file_path (Path): The path to the text file.
    - resolution (str): The target resolution (e.g., "2K", "4K").

    Returns:
    -------
    - str: The scaled content of the file.

    Raises:
    ------
    - Exception: If an error occurs during file processing or database interaction.
    """
    try:
        # Read the content of the file.
        content = file_utils.read_file(file_path)

        if content is not None:
            # Extract positional values from the file.
            original_values = extract_positional_values(file_path)

            # Apply scaling factors to the values
            scaled_content = _apply_scaling_factors(content, original_values, resolution)

            return scaled_content

        else:
            # Skip to the next file if no content is found.
            log.error("No content found in file: %s", file_path)

    except Exception as error:
        log.exception("An unexpected error occurred while scaling file: %s", file_path, exc_info=error)

def _apply_scaling_factors(content: str, original_values: dict[str, list[float]], resolution: str) -> str:
    # ... (Implementation of apply_scaling_factors remains the same) ...
```

- We've extracted the `apply_scaling_factors` logic into a separate private function `_apply_scaling_factors` to improve code organization and readability.

**Next Steps:**

- **Profiling:** Run your code with a representative set of input files and use a profiling tool to identify any remaining performance bottlenecks.
- **Further Optimization:** Apply additional optimizations based on the profiling results.
- **Refactoring:** Continue refactoring your code to improve readability, maintainability, and structure.

Remember to test your changes thoroughly after each optimization or refactoring to ensure that the code still functions correctly.

Let me know if you have any other questions!