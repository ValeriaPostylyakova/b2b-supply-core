from unittest.mock import Mock

import pytest
from rest_framework.request import Request

from apps.organizations.api.permissions import (
    IsBuyer,
    IsOrganizationAdmin,
    IsSupplierAdminOwner,
)


class FakeOrganization:
    def __init__(self, id: int):
        self.id = id


class FakeUser:
    def __init__(self, role: str, organization: FakeOrganization = None):
        self.role = role
        self.organization = organization


class FakeModelObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def make_request(user: FakeUser) -> Request:
    request = Mock(spec=Request)
    request.user = user
    return request


class TestIsOrganizationAdmin:
    @pytest.mark.parametrize(
        "role, expected",
        [
            ("SUPPLIER_ADMIN", True),
            ("BUYER_ADMIN", True),
            ("SUPPLIER_MANAGER", False),
            ("BUYER_MANAGER", False),
            ("WAREHOUSE_MANAGER", False),
        ],
    )
    def test_has_permission_by_role(self, role, expected):
        permission = IsOrganizationAdmin()
        user = FakeUser(role=role)
        request = make_request(user)

        assert permission.has_permission(request, view=Mock()) is expected

    def test_has_object_permission_same_organization(self):
        org = FakeOrganization(id=1)
        user = FakeUser(role="SUPPLIER_ADMIN", organization=org)
        obj = FakeModelObject(organization=org)

        permission = IsOrganizationAdmin()
        assert (
            permission.has_object_permission(make_request(user), view=Mock(), obj=obj)
            is True
        )

    def test_has_object_permission_different_organization(self):
        org_a = FakeOrganization(id=1)
        org_b = FakeOrganization(id=2)
        user = FakeUser(role="SUPPLIER_ADMIN", organization=org_a)
        obj = FakeModelObject(organization=org_b)

        permission = IsOrganizationAdmin()
        assert (
            permission.has_object_permission(make_request(user), view=Mock(), obj=obj)
            is False
        )


class TestSupplierAdminOwnerPermission:
    def test_has_permission_exact_role(self):
        permission = IsSupplierAdminOwner()

        assert (
            permission.has_permission(
                make_request(FakeUser(role="SUPPLIER_ADMIN")), Mock()
            )
            is True
        )
        assert (
            permission.has_permission(
                make_request(FakeUser(role="SUPPLIER_MANAGER")), Mock()
            )
            is False
        )

    def test_has_object_permission_matches_supplier_field(self):
        org_supplier = FakeOrganization(id=10)

        user = FakeUser(role="SUPPLIER_ADMIN", organization=org_supplier)
        obj = FakeModelObject(supplier=org_supplier)

        permission = IsSupplierAdminOwner()
        assert (
            permission.has_object_permission(make_request(user), view=Mock(), obj=obj)
            is True
        )

    def test_has_object_permission_mismatch_supplier_field(self):
        org_a = FakeOrganization(id=10)
        org_b = FakeOrganization(id=20)

        user = FakeUser(role="SUPPLIER_ADMIN", organization=org_a)
        obj = FakeModelObject(supplier=org_b)

        permission = IsSupplierAdminOwner()
        assert (
            permission.has_object_permission(make_request(user), view=Mock(), obj=obj)
            is False
        )


class TestCompositePermissions:
    @pytest.mark.parametrize(
        "role, expected",
        [
            ("BUYER_ADMIN", True),
            ("BUYER_MANAGER", True),
            ("SUPPLIER_ADMIN", False),
            ("SUPPLIER_MANAGER", False),
            ("WAREHOUSE_MANAGER", False),
        ],
    )
    def test_is_buyer_composite_permission(self, role, expected):
        user = FakeUser(role=role)
        request = make_request(user)

        assert IsBuyer.has_permission(request, view=Mock()) is expected
