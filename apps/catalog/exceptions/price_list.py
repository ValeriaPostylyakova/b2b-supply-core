class ExcelImportError(Exception):
    message = "Ошибка при импорте Excel-файла."

    def __init__(self, message=None):
        if message:
            self.message = message
        super().__init__(self.message)


class EmptyWorkbookError(ExcelImportError):
    message = "Excel-файл не содержит листов."


class EmptyFileError(ExcelImportError):
    message = "Excel-файл пуст."


class MissingHeadersError(ExcelImportError):
    message = "В Excel-файле отсутствуют заголовки."


class MissingRequiredColumnsError(ExcelImportError):
    def __init__(self, missing_fields):
        fields_str = ", ".join(sorted(missing_fields))
        message = f"В файле отсутствуют обязательные колонки: {fields_str}"
        self.missing_fields = missing_fields
        super().__init__(message)
