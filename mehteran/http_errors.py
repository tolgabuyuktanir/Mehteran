class HTTPError(Exception):
    def __init__(self, code: int, message: str, problems: list[str] | None = None):
        super().__init__(message)
        self.code, self.problems = code, problems or []
