from django.db import models


class OrderQuerySet(models.QuerySet):
    def get_report_data(self):
        return self.aggregate(
            orders_count=models.Count("id"),
            orders_total_amount=models.Sum("total_amount"),
            average_order_amount=models.Avg("total_amount"),
            min_order_amount=models.Min("total_amount"),
            max_order_amount=models.Max("total_amount"),
        )
