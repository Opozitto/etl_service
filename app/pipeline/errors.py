class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_error") -> None:
        super().__init__(message)
        self.code = code
