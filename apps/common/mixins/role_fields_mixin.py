class RoleFieldsMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        if not request or not request.user:
            return data

        user = request.user

        supplier_fields = getattr(self, "supplier_fields", set())
        buyer_fields = getattr(self, "buyer_fields", set())

        all_role_fields = supplier_fields | buyer_fields
        allowed_fields = supplier_fields if user.is_supplier else buyer_fields

        fields_to_remove = all_role_fields - allowed_fields
        for field in fields_to_remove:
            data.pop(field, None)

        return data
