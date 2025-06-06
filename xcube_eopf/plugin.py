#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from xcube.constants import EXTENSION_POINT_DATA_STORES
from xcube.util import extension

from .constants import DATA_STORE_ID


def init_plugin(ext_registry: extension.ExtensionRegistry):
    ext_registry.add_extension(
        loader=extension.import_component("xcube_eopf.store:EOPFZarrDataStore"),
        point=EXTENSION_POINT_DATA_STORES,
        name=DATA_STORE_ID,
        description="EOPF-Zarr DataStore",
    )
