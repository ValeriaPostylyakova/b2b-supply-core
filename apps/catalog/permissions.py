from apps.accounts.permissions import BaseOrganizationPermission


class IsSupplierAdminOwner(BaseOrganizationPermission):
    role_name = 'SUPPLIER_ADMIN'
    org_field = 'supplier'

class IsSupplierManagerOwner(BaseOrganizationPermission):
    role_name = 'SUPPLIER_MANAGER'
    org_field = 'supplier'

class IsWarehouseManagerOwner(BaseOrganizationPermission):
    role_name = 'WAREHOUSE_MANAGER'
    org_field = 'warehouse'