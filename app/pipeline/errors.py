class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_error") -> None:
        super().__init__(message)
        self.code = code


class UnsupportedImageFormatError(ValueError):
    def __init__(self, suffix: str, supported_suffixes: tuple[str, ...]) -> None:
        normalized_suffix = suffix.lower()
        supported_list = ", ".join(supported_suffixes)
        message = (
            f"Неподдерживаемый формат изображения: {normalized_suffix}. "
            f"Поддерживаемые standalone image-форматы: {supported_list}. "
            "OCR пока не реализован."
        )
        super().__init__(message)
        self.code = "unsupported_image_format"
        self.suffix = normalized_suffix
        self.supported_suffixes = supported_suffixes


class UnsupportedSpreadsheetFormatError(ValueError):
    def __init__(self, suffix: str, supported_suffixes: tuple[str, ...]) -> None:
        normalized_suffix = suffix.lower()
        supported_list = ", ".join(supported_suffixes)
        message = (
            f"Неподдерживаемый формат электронной таблицы: {normalized_suffix}. "
            f"Поддерживаемый spreadsheet-формат: {supported_list}. "
            "Старый бинарный XLS пока не реализован."
        )
        super().__init__(message)
        self.code = "unsupported_spreadsheet_format"
        self.suffix = normalized_suffix
        self.supported_suffixes = supported_suffixes
