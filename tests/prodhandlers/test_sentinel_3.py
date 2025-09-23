#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
from unittest import TestCase

import pystac
import xarray as xr

from xcube_eopf.prodhandlers.sentinel3 import group_items


class Sentinel3Test(TestCase):

    def test_group_items(self):
        item0 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
            },
        )
        item1 = pystac.Item(
            id="S2A_MSIL2A_20240604T103031_N0500_R108_T32UQD_20240604T120000",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
            },
        )

        grouped_item = group_items([item0, item1])
        self.assertIsInstance(grouped_item, xr.DataArray)
        self.assertEqual(dict(time=1), grouped_item.sizes)
        self.assertIsInstance(grouped_item[0].item(), list)
        self.assertEqual(2, len(grouped_item[0].item()))
