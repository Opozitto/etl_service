class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_error") -> None:
        super().__init__(message)
        self.code = code


class UnsupportedImageFormatError(ValueError):
    def __init__(self, suffix: str, supported_suffixes: tuple[str, ...]) -> None:
        normalized_suffix = suffix.lower()
        supported_list = ", ".join(supported_suffixes)
        message = (
            f"Unsupported image format: {normalized_suffix}. "
            f"Supported standalone image formats: {supported_list}. "
            "OCR is not implemented yet."
        )
        super().__init__(message)
        self.code = "unsupported_image_format"
        self.suffix = normalized_suffix
        self.supported_suffixes = supported_suffixes
