#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import logging

from xcube.util.jsonschema import (
    JsonArraySchema,
    JsonComplexSchema,
    JsonDateSchema,
    JsonIntegerSchema,
    JsonNumberSchema,
    JsonObjectSchema,
    JsonStringSchema,
)

# general stac constants
DATA_STORE_ID = "eopf-zarr"
STAC_URL = "https://stac.core.eopf.eodc.eu"
SUPPORTED_STAC_COLLECTIONS = ["sentinel-2-l1c", "sentinel-2-l2a"]
EOPF_ZARR_OPENR_ID = "dataset:zarr:eopf-zarr"

# other constants
CONVERSION_FACTOR_DEG_METER = 111320
LOG = logging.getLogger("xcube.eopf")

# general schema definition
SCHEMA_ADDITIONAL_QUERY = JsonObjectSchema(
    additional_properties=True,
    title="Additional query options used during item search of STAC API.",
    description=(
        "Additional filtering based on the properties of Item objects "
        "is supported. For more information see "
        "https://github.com/stac-api-extensions/query"
    ),
)
SCHEMA_BBOX = JsonArraySchema(
    items=(
        JsonNumberSchema(),
        JsonNumberSchema(),
        JsonNumberSchema(),
        JsonNumberSchema(),
    ),
    title="Bounding box [west, south, east, north] in geographical coordinates.",
)
SCHEMA_TIME_RANGE = JsonArraySchema(
    items=[
        JsonDateSchema(nullable=True),
        JsonDateSchema(nullable=True),
    ],
    title="Time Range",
    description=(
        "Time range given as pair of start and stop dates. "
        "Dates must be given using format 'YYYY-MM-DD'. "
        "Start and stop are inclusive."
    ),
)
SCHEMA_VARIABLES = JsonComplexSchema(
    title="Names of variables in dataset",
    description="Names of variables which will be included in the data cube.",
    one_of=[
        JsonStringSchema(
            title="Variable name or regex pattern",
            min_length=0,
        ),
        JsonArraySchema(
            title="Iterable of variables",
            items=(JsonStringSchema(min_length=0)),
            unique_items=True,
        ),
    ],
)
SCHEMA_SPATIAL_RES = JsonNumberSchema(title="Spatial Resolution", exclusive_minimum=0.0)
SCHEMA_CRS = JsonStringSchema(title="Coordinate reference system")
SCHEMA_TILE_SIZE = JsonArraySchema(
    nullable=True,
    title="Tile size of returned dataset",
    description=(
        "Spatial tile size in y and x (or lat and lon if crs is geographic) "
        "in returned dataset."
    ),
    items=[JsonIntegerSchema(minimum=1), JsonIntegerSchema(minimum=1)],
)
