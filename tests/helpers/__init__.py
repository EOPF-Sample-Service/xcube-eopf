#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from .sentinel2 import l2a_10m, l2a_60m, l2a_60m_wo_scl

__all__ = ["l2a_10m", "l2a_60m", "l2a_60m_wo_scl"]
