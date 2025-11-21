#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
from unittest import TestCase
import logging

import pystac
import xarray as xr

from xcube_eopf.prodhandlers.sentinel3 import group_items, IgnoreZeroSizedDimension,_get_base_id


class Sentinel3Test(TestCase):

    def test_group_items(self):
        item0 = pystac.Item(
            id="S3A_SL_2_LST____20251121T072112_20251121T072412_20251121T094300_0180_133_049_2160_PS1_O_NR_004",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
            },
        )
        item1 = pystac.Item(
            id="S3A_SL_2_LST____20251121T072112_20251121T072412_20251121T094300_0180_133_049_2160_PS1_O_NT_004",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
            },
        )
        item2 = pystac.Item(
            id="S3A_SL_2_LST____20251121T072112_20251121T072412_20251121T102143_0180_133_049_2160_PS1_O_NT_004",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 4, 10, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 10, 30, 31),
            },
        )
        item3 = pystac.Item(
            id="S3A_SL_2_LST____20251121T054636_20251121T054876_20251121T456789_0180_133_049_2160_PS1_O_NT_004",
            geometry=None,
            bbox=[1, 52, 2, 53],
            datetime=datetime.datetime(2024, 6, 4, 8, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 4, 8, 30, 31),
            },
        )
        item4 = pystac.Item(
            id="S3A_SL_2_LST____20251121T064636_20251121T074876_20251121T3456721_0180_133_049_2160_PS1_O_NT_004",
            geometry=None,
            bbox=[1, 52, 2, 53],
            datetime=datetime.datetime(2024, 6, 5, 8, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 5, 8, 30, 31),
            },
        )
        item5 = pystac.Item(
            id="S3A_SL_2_LST____20251121T142032_20251121T234521_20251121T456789_0180_133_049_2160_PS1_O_NR_004",
            geometry=None,
            bbox=[1, 52, 2, 53],
            datetime=datetime.datetime(2024, 6, 6, 8, 30, 31),
            properties={
                "datetime_nominal": datetime.datetime(2024, 6, 6, 8, 30, 31),
            },
        )

        grouped_item = group_items([item0, item1, item2, item3, item4, item5])
        self.assertIsInstance(grouped_item, xr.DataArray)
        self.assertEqual(dict(time=3), grouped_item.sizes)
        self.assertIsInstance(grouped_item[0].item(), list)
        self.assertEqual(2, len(grouped_item[0].item()))

    def test_get_base_id(self):
        item_id = "S3A_SL_2_LST____abc_abc_20251121T456789_0180_133_049_2160_PS1_O_NR_"
        with self.assertLogs("xcube.eopf", level="WARNING") as cm:
            item_id_return = _get_base_id(item_id)
        self.assertIn("does not contain 3 timestamp.", cm.output[-1])
        self.assertEqual(item_id, item_id_return)

class TestIgnoreZeroSizedDimension(TestCase):
    def setUp(self):
        self.filter = IgnoreZeroSizedDimension()
        # Create a dummy LogRecord for testing
        self.logger_name = "xcube.resampling"

    def make_record(self, msg):
        return logging.LogRecord(
            name=self.logger_name,
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None
        )

    def test_suppresses_target_message(self):
        record = self.make_record("Clipped dataset contains at least one zero-sized dimension.")
        self.assertFalse(self.filter.filter(record), "Filter should suppress the target message")

    def test_allows_other_messages(self):
        record = self.make_record("Some other warning message")
        self.assertTrue(self.filter.filter(record), "Filter should allow non-target messages")

