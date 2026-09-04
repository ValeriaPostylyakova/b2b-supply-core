import uuid

from apps.catalog.models.price_list import PriceListImport
from apps.catalog.tasks.price_list import process_price_list_import_task
from apps.organizations.models import Organization
from config.storages import PrivateMediaStorage


class PriceListImportService:
    @staticmethod
    def process_price_list_import(storage_key, original_name, organization_id):
        supplier = Organization.objects.get(id=organization_id)

        import_record = PriceListImport.objects.create(
            supplier=supplier,
            original_name=original_name,
            storage_key=storage_key,
            status=PriceListImport.Status.PENDING,
        )

        process_price_list_import_task.delay_on_commit(import_record.id)
        return import_record.external_id

    @staticmethod
    def generate_pricelist_upload_data(file_name: str) -> dict:
        ext = file_name.split(".")[-1]
        storage_key = f"price_lists/{uuid.uuid4()}.{ext}"
        storage = PrivateMediaStorage()

        upload_url = storage.generate_presigned_put_url(storage_key)

        return {"upload_url": upload_url, "storage_key": storage_key}
