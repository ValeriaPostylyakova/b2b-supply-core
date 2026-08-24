from apps.accounts.permissions import BaseOrganizationPermission


class IsSupplierAdminOwner(BaseOrganizationPermission):
    role_name = 'SUPPLIER_ADMIN'
    org_field = 'supplier'

class IsSupplerManagerOwner(BaseOrganizationPermission):
    role_name = 'SUPPLIER_MANAGER'
    org_field = 'supplier'