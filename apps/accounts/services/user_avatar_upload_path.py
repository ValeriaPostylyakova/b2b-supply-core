import os
import uuid


class AccountService:
    @staticmethod
    def user_avatar_upload_path(instance, filename):
        ext = filename.split(".")[-1].lower()
        new_filename = f"{uuid.uuid4()}.{ext}"
        return os.path.join("accounts/avatars/", new_filename)
