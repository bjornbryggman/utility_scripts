# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Establishes relationships between geographical entities in the database.

This module provides a function to set relationships between provinces, areas,
regions, superregions, and continents based on their foreign keys in the database.
It ensures that all related entities have their relationships set correctly.
"""

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from app.database.models import Province
from app.utils import db_utils

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)


# ================================================================= #
#             Database Relationship Management Functions            #
# ================================================================= #


def set_geographical_relationships() -> None:
    """
    Establish relationships between geographical entities in the database.

    Process:
    -------
    -------
        - Retrieves all provinces from the database.
        - For each province, it sets relationships between province, area, region, superregion, and continent based on their foreign keys.
        - Ensures that all related entities have their continent set correctly.

    Args:
    ----
    ----
        - None.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - SQLAlchemyError: Raised when a database-related error occurs.
        - Exception: Raised for any other unexpected errors during execution.
    """
    try:
        with db_utils.session_scope() as session:
            # Fetch all provinces.
            provinces = session.exec(select(Province)).all()

            for province in provinces:
                if province.area:
                    # Set Region and SuperRegion for Province.
                    province.region = province.area.region
                    province.superregion = province.area.region.superregion

                    # Set Continent for Area, Region, and SuperRegion if missing.
                    if province.area and not province.area.continent:
                        province.area.continent = province.continent
                    if province.region and not province.region.continent:
                        province.region.continent = province.continent
                    if province.superregion and not province.superregion.continent:
                        province.superregion.continent = province.continent

                    # Set SuperRegion for Area if missing.
                    if province.area and not province.area.superregion:
                        province.area.superregion = province.superregion

    except SQLAlchemyError as error:
        log.exception("Database error.", exc_info=error)
        raise
    except Exception as error:
        log.exception("An unexpected error occured.", exc_info=error)
        raise

    log.info("Database relationships set successfully.")
