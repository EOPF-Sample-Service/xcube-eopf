#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from collections.abc import Container, Iterator
from typing import Any

import pystac_client
import xarray as xr
from xcube.core.mldataset import MultiLevelDataset
from xcube.core.store import (
    DATASET_TYPE,
    DatasetDescriptor,
    DataStore,
    DataStoreError,
    DataTypeLike,
)
from xcube.util.jsonschema import JsonObjectSchema

from .constants import EOPF_ZARR_OPENR_ID, STAC_URL
from .prodhandler import ProductHandler
from .prodhandlers import register_product_handlers
from .utils import (
    bbox_to_geojson,
    filter_items_deprecated,
    filter_items_wrong_footprint,
    reproject_bbox,
)


class EOPFZarrDataStore(DataStore):
    """EOPF-Zarr implementation of the data store."""

    def __init__(self):
        register_product_handlers()

    @classmethod
    def get_data_store_params_schema(cls) -> JsonObjectSchema:
        return JsonObjectSchema(
            description="Describes the parameters of the xcube data store 'eopf-zarr'.",
            properties=dict(),
            required=[],
            additional_properties=False,
        )

    @classmethod
    def get_data_types(cls) -> tuple[str, ...]:
        return (DATASET_TYPE.alias,)

    def get_data_types_for_data(self, data_id: str) -> tuple[str, ...]:
        self._assert_has_data(data_id)
        return (DATASET_TYPE.alias,)

    def get_data_ids(
        self,
        data_type: DataTypeLike = None,
        include_attrs: Container[str] | bool = False,
    ) -> Iterator[str | tuple[str, dict[str, Any]], None]:
        self._assert_valid_data_type(data_type)
        for data_id in ProductHandler.registry.keys():
            if not include_attrs:
                yield data_id
            else:
                yield data_id, dict()

    def has_data(self, data_id: str, data_type: DataTypeLike = None) -> bool:
        self._assert_valid_data_type(data_type)
        if data_id in ProductHandler.registry.keys():
            return True
        return False

    def get_data_opener_ids(
        self, data_id: str = None, data_type: DataTypeLike = None
    ) -> tuple[str, ...]:
        self._assert_valid_data_type(data_type)
        if data_id is not None:
            self._assert_has_data(data_id)
        return (EOPF_ZARR_OPENR_ID,)

    def get_open_data_params_schema(
        self, data_id: str = None, opener_id: str = None
    ) -> JsonObjectSchema:
        self._assert_valid_opener_id(opener_id)
        if data_id is not None:
            self._assert_has_data(data_id)
            product_handler = ProductHandler.guess(data_id)
            return product_handler.get_open_data_params_schema()
        else:
            return JsonObjectSchema(
                title="Opening parameters for all supported Sentinel products.",
                properties={
                    key: ph.get_open_data_params_schema()
                    for (key, ph) in zip(
                        ProductHandler.registry.keys(), ProductHandler.registry.values()
                    )
                },
            )

    def open_data(
        self,
        data_id: str,
        opener_id: str = None,
        data_type: DataTypeLike = None,
        **open_params,
    ) -> xr.Dataset | MultiLevelDataset:
        self._assert_has_data(data_id)
        self._assert_valid_data_type(data_type)
        self._assert_valid_opener_id(opener_id)
        schema = self.get_open_data_params_schema()
        schema.validate_instance(open_params)

        # search for items
        bbox_wgs84 = reproject_bbox(
            open_params["bbox"], open_params["crs"], "EPSG:4326"
        )

        search_params = dict(
            collections=[data_id],
            datetime=open_params["time_range"],
            intersects=bbox_to_geojson(bbox_wgs84),
            query=open_params.get("query"),
        )
        catalog = pystac_client.Client.open(STAC_URL)
        items = list(catalog.search(**search_params).items())
        # filter deprecated items
        items = filter_items_deprecated(items)
        # fiter items with incorrectly assigned footprint
        items = filter_items_wrong_footprint(items)
        if len(items) == 0:
            raise DataStoreError(f"No items found for search_params {search_params}.")

        product_handler = ProductHandler.guess(data_id)
        return product_handler.open_data(items, **open_params)

    def describe_data(
        self, data_id: str, data_type: DataTypeLike = None
    ) -> DatasetDescriptor:
        self._assert_has_data(data_id)
        self._assert_valid_data_type(data_type)
        raise NotImplementedError("`describe_data` is not implemented, yet.")

    def search_data(
        self, data_type: DataTypeLike = None, **search_params
    ) -> Iterator[DatasetDescriptor]:
        raise NotImplementedError(
            "Search is not supported. Only Sentinel-2 L1C and L2A products "
            "are currently handled."
        )

    def get_search_params_schema(
        self, data_type: DataTypeLike = None
    ) -> JsonObjectSchema:
        self._assert_valid_data_type(data_type)
        return JsonObjectSchema(
            properties=dict(),
            required=[],
            additional_properties=True,
        )

    # Auxiliary internal functions
    def _assert_has_data(self, data_id: str) -> None:
        if not self.has_data(data_id):
            raise DataStoreError(f"Data resource {data_id!r} is not available.")

    @staticmethod
    def _assert_valid_opener_id(opener_id: str) -> None:
        if opener_id is not None and opener_id is not EOPF_ZARR_OPENR_ID:
            raise DataStoreError(
                f"Data opener identifier must be {EOPF_ZARR_OPENR_ID!r}, "
                f"but got {opener_id!r}."
            )

    def _assert_valid_data_type(self, data_type: DataTypeLike) -> None:
        if not self._is_valid_data_type(data_type):
            raise DataStoreError(
                f"Data type must be {DATASET_TYPE.alias!r} "
                f"or None, but got {data_type!r}."
            )

    @staticmethod
    def _is_valid_data_type(data_type: DataTypeLike) -> bool:
        return data_type is None or DATASET_TYPE.is_super_type_of(data_type)
