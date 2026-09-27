from urllib.parse import urlencode

from django.core.cache import cache

VERSION_KEY = "products:version"


def get_products_version():
    return cache.get_or_set(VERSION_KEY, 1, timeout=None)


def build_products_cache_key(request):
    current_version = get_products_version()

    params = sorted(request.query_params.items())
    query_string = urlencode(params)

    return f"products:list:version:{current_version}:{query_string}"


def invalidate_products_cache():
    cache.incr(VERSION_KEY)


def product_detail_cache_key(product_id):
    return f"products:detail:{product_id}"
