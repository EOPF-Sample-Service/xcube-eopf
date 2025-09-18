#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.


from abc import ABC, abstractmethod
from typing import Optional, Type

import pystac
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema


class ProductHandler(ABC):
    """Provides product-type specific properties and behaviour
    for the xcube EOPF-Zarr data store.
    """

    # Registry for product handler
    registry: "ProductHandlerRegistry"

    # data ID in this data store which represents the STAC Collection ID
    data_id: str

    @classmethod
    def guess(cls, data_id: str) -> Optional["ProductHandler"]:
        """Guess the suitable product handler for a given data id.

        Args:
            data_id: Data identifier of the data source.

        Returns:
            The product handler.

        Raises:
            ValueError: if guessing the product handler failed.
        """
        product_handler = ProductHandler.from_data_id(data_id)
        if product_handler is None:
            raise ValueError(
                f"Unable to detect product handler for {data_id!r}."
                " Use `data_id` argument to pass one of"
                f" {', '.join(map(repr, cls.registry.keys()))}."
            )
        return product_handler

    @classmethod
    def from_data_id(cls, data_id: str) -> Optional["ProductHandler"]:
        """Get the product handler for given `data_id`."""
        return cls.registry.get(data_id)

    @abstractmethod
    def get_open_data_params_schema(self) -> JsonObjectSchema:
        """Return opening parameters specific for the product handler."""

    @abstractmethod
    def open_data(self, items: list[pystac.Item], **open_params) -> xr.Dataset:
        """Open and return the dataset corresponding to the given parameters
        for the product handler.
        """


class ProductHandlerRegistry:
    """A simple registry for `ProductHandler` instances."""

    def __init__(self):
        self._product_handlers: dict[str, ProductHandler] = {}

    def keys(self) -> tuple[str, ...]:
        """Get registered product handler keys."""
        return tuple(self._product_handlers.keys())

    def values(self) -> tuple[ProductHandler, ...]:
        """Get registered product handlers."""
        # noinspection PyTypeChecker
        return tuple(self._product_handlers.values())

    def get(self, data_id: str) -> Optional["ProductHandler"]:
        """Get a specific product handler for given `data_id`."""
        return self._product_handlers.get(data_id)

    def register(self, cls: Type[ProductHandler]):
        """Register the product handler given as its class `cls`."""
        assert issubclass(cls, ProductHandler)
        assert isinstance(cls.data_id, str)
        self._product_handlers[cls.data_id] = cls()

    def unregister(self, cls: Type[ProductHandler]):
        """Unregister the product handler given as its class `cls`."""
        assert issubclass(cls, ProductHandler)
        assert isinstance(cls.data_id, str)
        del self._product_handlers[cls.data_id]


ProductHandler.registry = ProductHandlerRegistry()
