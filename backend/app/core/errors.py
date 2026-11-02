class DomainError(Exception):
    """Business errors carry no HTTP dependencies; main.py maps them to responses."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
