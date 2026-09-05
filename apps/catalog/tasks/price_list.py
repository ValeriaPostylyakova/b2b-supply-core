import logging
from typing import Any

import openpyxl
from celery import shared_task
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from apps.catalog.api.serializers.price_list import ProductImportRowSerializer
from apps.catalog.exceptions.price_list import (
    EmptyFileError,
    EmptyWorkbookError,
    ExcelImportError,
    MissingHeadersError,
    MissingRequiredColumnsError,
)
from apps.catalog.models.price_list import PriceListImport
from apps.catalog.models.product import Product
from apps.catalog.models.stock import Stock
from apps.catalog.models.warehouse import Warehouse
from config.storages import PrivateMediaStorage

logger = logging.getLogger(__name__)


EXPECTED_FIELDS = {
    "sku",
    "name",
    "price",
    "warehouse",
    "quantity",
}


@shared_task(bind=True, time_limit=1800)
def process_price_list_import_task(self, import_id: int) -> str:
    logger.info(
        "Старт задачи импорта прайс-листа #%s",
        import_id,
    )

    private_storage = PrivateMediaStorage()
    import_record = get_object_or_404(PriceListImport, id=import_id)

    import_record.status = PriceListImport.Status.PROCESSING
    import_record.save(update_fields=["status"])

    logger.info(
        "Импорт #%s переведен в PROCESSING",
        import_id,
    )

    success_count = 0
    error_count = 0
    total_processed_rows = 0

    try:
        logger.info(
            "Открытие файла из storage: %s",
            import_record.storage_key,
        )

        file_obj = private_storage.open(import_record.storage_key)

        wb = openpyxl.load_workbook(
            file_obj,
            read_only=True,
            data_only=True,
        )

        try:
            if not wb.worksheets:
                raise EmptyWorkbookError()

            sheet = wb.worksheets[0]
            row_iterator = sheet.iter_rows(values_only=True)

            try:
                raw_headers = next(row_iterator)
            except StopIteration:
                raise EmptyFileError()

            if not raw_headers or not any(raw_headers):
                raise MissingHeadersError()

            headers = [
                str(header).strip().lower()
                for header in raw_headers
                if header is not None
            ]

            logger.info("Получены заголовки: %s", headers)

            missing_fields = EXPECTED_FIELDS - set(headers)

            if missing_fields:
                raise MissingRequiredColumnsError(missing_fields)

            header_indexes = {header: index for index, header in enumerate(headers)}

            for excel_row_number, row in enumerate(row_iterator, start=2):
                total_processed_rows += 1

                try:
                    raw_data = {
                        "sku": _get_cell_value(row, header_indexes, "sku"),
                        "name": _get_cell_value(row, header_indexes, "name"),
                        "price": _get_cell_value(row, header_indexes, "price"),
                        "warehouse": _get_cell_value(row, header_indexes, "warehouse"),
                        "quantity": _get_cell_value(row, header_indexes, "quantity"),
                    }

                    serializer = ProductImportRowSerializer(data=raw_data)

                    if not serializer.is_valid():
                        error_msg = (
                            f"Ошибка в строке {excel_row_number}: {serializer.errors}"
                        )
                        logger.error(error_msg)
                        raise serializers.ValidationError(serializer.errors)

                    valid_data = serializer.validated_data

                    sku = valid_data["sku"]
                    name = valid_data["name"]
                    warehouse_name = valid_data["warehouse"]
                    price_decimal = valid_data["price"]
                    quantity_int = valid_data["quantity"]

                    warehouse = Warehouse.objects.filter(
                        supplier=import_record.supplier,
                        name=warehouse_name,
                        is_active=True,
                    ).first()

                    if warehouse is None:
                        raise ValueError(
                            f"Активный склад '{warehouse_name}' не найден."
                        )

                    with transaction.atomic():
                        product, created = Product.objects.update_or_create(
                            supplier=import_record.supplier,
                            sku=sku,
                            defaults={
                                "name": name,
                                "price": price_decimal,
                                "is_active": True,
                            },
                        )
                        logger.info(
                            f"{'Создан' if created else 'Обновлен'} Product: sku={sku}"
                        )

                        stock, stock_created = (
                            Stock.objects.select_for_update().get_or_create(
                                product=product,
                                warehouse=warehouse,
                                defaults={
                                    "quantity": quantity_int,
                                    "reserved_quantity": 0,
                                },
                            )
                        )

                        if stock_created:
                            logger.info(
                                f"Создан Stock: product={product.id} warehouse={warehouse.id}"
                            )
                        else:
                            if quantity_int < stock.reserved_quantity:
                                raise ValueError(
                                    f"Нельзя установить quantity {quantity_int}, "
                                    f"потому что зарезервировано {stock.reserved_quantity}."
                                )

                            stock.quantity = quantity_int
                            stock.save(update_fields=["quantity"])
                            logger.info(
                                f"Обновлен Stock: product={product.id} warehouse={warehouse.id} quantity={quantity_int}"
                            )

                    success_count += 1

                except Exception as row_error:
                    error_count += 1

                    logger.exception(
                        "Ошибка обработки строки Excel #%s: %s",
                        excel_row_number,
                        row_error,
                    )
                    continue

        finally:
            wb.close()
            file_obj.close()

        if error_count == 0:
            import_record.status = PriceListImport.Status.COMPLETED

        elif success_count > 0:
            import_record.status = PriceListImport.Status.COMPLETED_WITH_ERRORS

        else:
            import_record.status = PriceListImport.Status.FAILED

        import_record.total_rows = total_processed_rows
        import_record.success_rows = success_count
        import_record.error_rows = error_count

        import_record.save(
            update_fields=["status", "total_rows", "success_rows", "error_rows"]
        )

        logger.info(
            "Импорт #%s завершен. Всего строк: %s, успешно: %s, ошибок: %s",
            import_id,
            total_processed_rows,
            success_count,
            error_count,
        )

        return (
            f"Импорт #{import_id} завершен. "
            f"Строк: {total_processed_rows}, "
            f"успешно: {success_count}, "
            f"ошибок: {error_count}."
        )

    except ExcelImportError() as e:
        logger.error("Ошибка валидации Excel: %s", e.message)

        import_record.status = PriceListImport.Status.FAILED
        import_record.save(update_fields=["status"])

        return f"Импорт #{import_id} завершился критической ошибкой."


def _get_cell_value(
    row: tuple[Any, ...],
    header_indexes: dict[str, int],
    field: str,
) -> Any:
    index = header_indexes.get(field)

    if index is None:
        return None

    if index >= len(row):
        return None

    return row[index]
