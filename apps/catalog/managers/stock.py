from django.db import models


class StockQuerySet(models.QuerySet):
    def for_user_organization(self, user):
        return self.filter(warehouse__supplier=user.organization)

    def with_available_quantity(self):
        return self.annotate(
            available_quantity=models.F("quantity") - models.F("reserved_quantity")
        )

    def get_report_data(self):
        return self.aggregate(
            products_count=models.Count("product"),
            total_quantity=models.Sum("quantity"),
            total_reserved=models.Sum("reserved_quantity"),
            total_available=models.Sum("quantity") - models.Sum("reserved_quantity"),
        )
