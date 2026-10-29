from fastapi import HTTPException, status


class TruthLensException(HTTPException):
    """Base exception class for TruthLens application."""
    def __init__(self, status_code: int = 500, detail: str = "", message: str = ""):
        actual_detail = detail or message or "Internal application error"
        super().__init__(status_code=status_code, detail=actual_detail)



class NotFoundException(TruthLensException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationException(TruthLensException):
    def __init__(self, detail: str = "Invalid input data"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class SecurityRiskException(TruthLensException):
    def __init__(self, detail: str = "Request blocked due to security validation"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class DatabaseConnectionException(TruthLensException):
    def __init__(self, detail: str = "Database connection error"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class ConfigurationException(TruthLensException):
    def __init__(self, detail: str = "Configuration error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class SearchProviderException(TruthLensException):
    def __init__(self, detail: str = "Search provider error"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
