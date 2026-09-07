from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.catalog.api.filters.warehouse import WarehouseFilter
from apps.catalog.models.warehouse import Warehouse

User = get_user_model()


@pytest.mark.django_db
class TestWarehouseFilter:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        from apps.organizations.models import Organization

        self.org_apple = Organization.objects.create(name="Apple Inc", type="SUPPLIER")
        self.org_sony = Organization.objects.create(name="Sony Corp", type="SUPPLIER")
        self.org_buyer = Organization.objects.create(name="Retail LLC", type="BUYER")

        self.wh_1 = Warehouse.objects.create(
            name="Central Moscow",
            supplier=self.org_apple,
            is_active=True,
            address="г. Москва, ул. Ленина, д. 1",
        )
        self.wh_2 = Warehouse.objects.create(
            name="Siberia Main",
            supplier=self.org_sony,
            is_active=False,
            address="г. Новосибирск, ул. Новая, д. 10",
        )
        self.wh_3 = Warehouse.objects.create(
            name="Apple Backup",
            supplier=self.org_apple,
            is_active=True,
            address="г. Москва, ул. Тверская, д. 5",
        )

    def _get_filter_qs(self, query_params, user) -> QuerySet:
        request = Mock()
        request.user = user
        queryset = Warehouse.objects.all()

        filter_set = WarehouseFilter(
            data=query_params, queryset=queryset, request=request
        )
        return filter_set.qs

    def test_search_by_warehouse_name(self):
        user = Mock(is_supplier=True)
        qs = self._get_filter_qs({"search": "Moscow"}, user)

        assert qs.count() == 1
        assert self.wh_1 in qs

    def test_search_by_supplier_organization_name(self):
        user = Mock(is_supplier=True)
        qs = self._get_filter_qs({"search": "Sony"}, user)

        assert qs.count() == 1
        assert self.wh_2 in qs

    def test_supplier_user_can_see_and_use_is_active_filter(self):
        user = Mock(is_supplier=True)
        qs = self._get_filter_qs({"is_active": "false"}, user)

        assert qs.count() == 1
        assert self.wh_2 in qs

    def test_non_supplier_user_cannot_use_is_active_filter(self):
        user = Mock(is_supplier=False)

        request = Mock(user=user)
        filter_set = WarehouseFilter(
            data={"is_active": "false"},
            queryset=Warehouse.objects.all(),
            request=request,
        )

        assert "is_active" not in filter_set.filters
        assert filter_set.qs.count() == 3
