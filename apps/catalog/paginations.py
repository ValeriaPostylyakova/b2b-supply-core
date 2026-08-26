from rest_framework.pagination import PageNumberPagination


class ProductNumberPagination(PageNumberPagination):
    page_size = 20
    page_query_param = 'page'
    page_size_query_param = "page_size"
    max_page_size = 100

class StockNumberPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = "page_size"
    max_page_size = 100