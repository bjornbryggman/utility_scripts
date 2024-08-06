# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Defines SQLModel and Pydantic models for various entities in the game.

This module defines SQLModel and Pydantic models for various entities in the game,
These models are used for representing and interacting with data in the database 
and for generating image prompts.
"""

import structlog
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

# Initialize logger for this module.
log = structlog.stdlib.get_logger(__name__)


# =============================================================== #
#               SQLModels used for 'terrain_script.py'            #
# =============================================================== #


class Continent(SQLModel, table=True):
    """
    Represents a continent in EU4.

    Attributes:
    ----------
    - id (int): The primary key of the continent.
    - name (str): The name of the continent (e.g., "europe").
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    # One-to-many relationships.
    superregions: list["Region"] = Relationship(back_populates="continent")
    regions: list["Region"] = Relationship(back_populates="continent")
    areas: list["Area"] = Relationship(back_populates="continent")
    provinces: list["Province"] = Relationship(back_populates="continent")


class SuperRegion(SQLModel, table=True):
    """
    Represents a super-region in EU4.

    Attributes:
    ----------
    - id (int): The primary key of the super-region.
    - name (str): The name of the super-region (e.g., "europe_superregion").
    - continent_id (int): Foreign key referencing the continent this super-region belongs to.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    # Foreign keys for relationships.
    continent_id: int | None = Field(default=None, foreign_key="continent.id")

    # One-to-one relationships.
    continent: Continent | None = Relationship(back_populates="superregions")

    # One-to-many relationships.
    regions: list["Region"] = Relationship(back_populates="superregion")
    areas: list["Area"] = Relationship(back_populates="superregion")
    provinces: list["Province"] = Relationship(back_populates="superregion")


class Region(SQLModel, table=True):
    """
    Represents a region in EU4.

    Attributes:
    ----------
    - id (int): The primary key of the region.
    - name (str): The name of the region (e.g., "scandinavia_region").
    - superregion_id (int): Foreign key referencing the super-region this region belongs to.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "scandinavia_region"

    # Foreign keys for relationships.
    continent_id: int | None = Field(default=None, foreign_key="continent.id")
    superregion_id: int | None = Field(default=None, foreign_key="superregion.id")

    # One-to-one relationships.
    continent: Continent | None = Relationship(back_populates="superregions")
    superregion: SuperRegion | None = Relationship(back_populates="regions")

    # One-to-many relationships.
    areas: list["Area"] = Relationship(back_populates="region")
    provinces: list["Province"] = Relationship(back_populates="region")


class Area(SQLModel, table=True):
    """
    Represents an area within a region in EU4.

    Attributes:
    ----------
    - id (int): The primary key of the area.
    - name (str): The name of the area (e.g., "svealand_area").
    - region_id (int): Foreign key referencing the region this area belongs to.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    # Foreign keys for relationships.
    continent_id: int | None = Field(default=None, foreign_key="continent.id")
    superregion_id: int | None = Field(default=None, foreign_key="superregion.id")
    region_id: int | None = Field(default=None, foreign_key="region.id")

    # One-to-one relationships.
    continent: Continent | None = Relationship(back_populates="areas")
    superregion: SuperRegion | None = Relationship(back_populates="areas")
    region: Region | None = Relationship(back_populates="areas")

    # One-to-many relationships.
    provinces: list["Province"] = Relationship(back_populates="area")


class Climate(SQLModel, table=True):
    """
    Represents a climate type in EU4.

    Attributes:
    ----------
        - id (int): The primary key of the climate type.
        - name (str): The name of the climate type (e.g., "tropical", "arid").
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    # One-to-many relationships.
    provinces: list["Province"] = Relationship(back_populates="climate")


class Terrain(SQLModel, table=True):
    """
    Represents a terrain type in EU4.

    Attributes:
    ----------
        - id (int): The primary key of the terrain type.
        - name (str): The name of the terrain type (e.g., "farmlands", "mountains").
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    # One-to-many relationships.
    provinces: list["Province"] = Relationship(back_populates="terrain")


class Province(SQLModel, table=True):
    """
    Represents a province in EU4.

    Attributes:
    ----------
        - id (int): The primary key of the province (same as the province ID in game files).
        - name (str): The name of the province (e.g., "Stockholm").
        - area_id (int): Foreign key referencing the area this province belongs to.
        - climate_id (int): Foreign key referencing the climate type of this province.
        - terrain_id (int): Foreign key referencing the terrain type of this province.
        - image_path (str): The path to the generated image for this province.
    """

    id: int = Field(primary_key=True)
    name: str
    prompt: str | None = Field(default=None)
    image_url: str | None = Field(default=None)

    # Foreign keys for relationships.
    continent_id: int | None = Field(default=None, foreign_key="continent.id")
    superregion_id: int | None = Field(default=None, foreign_key="superregion.id")
    region_id: int | None = Field(default=None, foreign_key="region.id")
    area_id: int | None = Field(default=None, foreign_key="area.id")
    climate_id: int | None = Field(default=None, foreign_key="climate.id")
    terrain_id: int | None = Field(default=None, foreign_key="terrain.id")

    # One-to-one relationships.
    continent: Continent | None = Relationship(back_populates="provinces")
    superregion: SuperRegion | None = Relationship(back_populates="provinces")
    region: Region | None = Relationship(back_populates="provinces")
    area: Area | None = Relationship(back_populates="provinces")
    climate: Climate | None = Relationship(back_populates="provinces")
    terrain: Terrain | None = Relationship(back_populates="provinces")


# ===================================================================== #
#               Pydantic models used for 'terrain_script.py'            #
# ===================================================================== #


class TerrainImageGenerationPrompt(BaseModel):
    """
    A Pydantic model for structured generation of image prompts for Europa Universalis 4 provinces.

    Purpose:
    --------
    --------
        - To provide a standardized format for generating detailed image prompts.
        - To ensure consistency and completeness in prompt generation for EU4 province terrains.

    Utility:
    --------
    --------
        - Facilitates the creation of rich, descriptive prompts for AI image generation.
        - Ensures all necessary elements (terrain, climate, reasoning, final prompt) are included.
        - Aids in maintaining a consistent style across generated province images.

    Attributes:
    ----------
    ----------
        - terrain_feature (str): A specific geological or topographical feature characteristic of the terrain type.
        - climate_detail (str): A particular aspect or phenomenon related to the climate type.
        - internal_reasoning (str): The thought process behind selecting the terrain feature and climate detail.
        - prompt (str): The final, concise prompt for AI image generation, incorporating all elements.

    Usage:
    ------
    ------
        - Used in conjunction with LLM APIs to generate structured image prompts.
        - Can be easily serialized to and from JSON for API interactions.
        - Provides a clear structure for prompt generation, enhancing consistency across multiple provinces.

    Note:
    ----
    ----
        - All fields are required and must be provided when creating an instance of this model.
    """

    terrain_feature: str = Field(..., description="A specific geological or topographical feature characteristic of the terrain type.")
    climate_detail: str = Field(..., description="A particular aspect or phenomenon related to the climate type.")
    internal_reasoning: str = Field(..., description="The thought process behind selecting the terrain feature and climate detail, and how they relate to the province.")
    prompt: str = Field(..., description="The final, concise prompt for AI image generation, incorporating the terrain and climate elements in the specified digital concept art style.")

    class Config:
        schema_extra = {
            "description": "A structured format for generating image prompts for Europa Universalis 4 provinces, focusing on terrain and climate characteristics in a digital concept art style.",
            "example": {
                "terrain_feature": "gently sloping arable land",
                "climate_detail": "golden autumnal foliage",
                "internal_reasoning": "The province features rolling farmlands in a temperate climate, with gently sloping arable land and the warm hues of golden autumnal foliage. We need to capture a sense of serene beauty and the bounty of the harvest season.",
                "prompt": "Digital concept art of a serene, pastoral landscape with rolling farmlands. Golden wheat fields and vibrant green pastures stretch to the horizon. Soft, diffused lighting bathes the scene in a warm glow. A winding river in the distance reflects the sky, dotted with small boats. Atmospheric perspective creates layers of depth. Painterly style with a color palette of warm golds, soft greens, and cool blues. Wispy clouds drift across a vast sky."
            }
        }
