import pytest

from apps.catalog.api.filters.product import ProductFilter
from apps.catalog.models.product import Product
from apps.catalog.models.stock import Stock


@pytest.mark.django_db
class TestProductFilter:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        from apps.catalog.models.warehouse import Warehouse
        from apps.organizations.models import Organization

        self.supplier = Organization.objects.create(
            name="Test Supplier Organization", type="supplier"
        )

        self.warehouse = Warehouse.objects.create(
            name="Test Warehouse",
            address="123 Test St",
            supplier=self.supplier,
        )

        self.p1 = Product.objects.create(
            name="iPhone 15",
            price=1000,
            sku="iph-15",
            supplier=self.supplier,
        )
        self.p2 = Product.objects.create(
            name="Samsung S24",
            price=900,
            sku="sam-24",
            supplier=self.supplier,
        )

        Stock.objects.create(
            product=self.p1, warehouse=self.warehouse, quantity=10, reserved_quantity=2
        )
        Stock.objects.create(
            product=self.p2, warehouse=self.warehouse, quantity=5, reserved_quantity=5
        )

    def test_search_by_name_and_sku(self):
        f = ProductFilter(data={"search": "iphone"}, queryset=Product.objects.all())
        assert self.p1 in f.qs
        assert self.p2 not in f.qs

        f = ProductFilter(data={"search": "sam"}, queryset=Product.objects.all())
        assert self.p2 in f.qs

    def test_available_filter_true(self):
        f = ProductFilter(data={"available": "true"}, queryset=Product.objects.all())
        assert self.p1 in f.qs
        assert self.p2 not in f.qs

    def test_available_filter_false(self):
        f = ProductFilter(data={"available": "false"}, queryset=Product.objects.all())
        assert self.p2 in f.qs
        assert self.p1 not in f.qs
