#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.


def register_product_handlers():
    from xcube_eopf.prodhandler import ProductHandler

    from .sentinel1 import register as register_s1
    from .sentinel2 import register as register_s2
    from .sentinel3 import register as register_s3

    register_s1(ProductHandler.registry)
    register_s2(ProductHandler.registry)
    register_s3(ProductHandler.registry)
