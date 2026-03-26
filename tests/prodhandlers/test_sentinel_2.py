#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
from unittest import TestCase

import pystac
import pytest
import xarray as xr

from xcube_eopf.prodhandlers.sentinel2 import group_items, _get_bounding_box


class Sentinel2Test(TestCase):

    def test_group_items(self):
        item0 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
                "grid:code": "32UQD",
            },
        )
        item1 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
                "grid:code": "32UQD",
            },
        )

        grouped_item = group_items([item0, item1])
        self.assertIsInstance(grouped_item, xr.DataArray)
        self.assertEqual(dict(time=1, tile_id=1), grouped_item.sizes)
        self.assertIsInstance(grouped_item[0, 0].item(), list)
        self.assertEqual(2, len(grouped_item[0, 0].item()))

    def test_get_bounding_box(self):
        item0 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
                "grid:code": "32UQD",
                "proj:bbox": [10000, 10000, 20000, 20000],
            },
            assets={"B02_10m": pystac.Asset("https://test")},
        )
        item1 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
                "grid:code": "32UQE",
            },
            assets={
                "B02_10m": pystac.Asset(
                    "https://test",
                    extra_fields={"proj:bbox": [20000, 20000, 30000, 30000]},
                )
            },
        )
        item2 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
                "grid:code": "32UQF",
            },
            assets={"B02_10m": pystac.Asset("https://test")},
        )

        bbox = _get_bounding_box(group_items([item0, item1]))
        self.assertEqual([10000, 10000, 30000, 30000], bbox)

        with pytest.raises(
            Exception, match="Required metadata field proj:bbox not found"
        ):
            _ = _get_bounding_box(group_items([item0, item1, item2]))
