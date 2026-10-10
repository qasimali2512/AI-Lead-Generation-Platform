class APIException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "API_ERROR",
        status_code: int = 400,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code

        super().__init__(message)


class ResourceNotFoundException(APIException):
    def __init__(
        self,
        message: str = "Resource not found.",
    ):
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
        )


class ResourceConflictException(APIException):
    def __init__(
        self,
        message: str = "Resource conflict.",
    ):
        super().__init__(
            message=message,
            code="RESOURCE_CONFLICT",
            status_code=409,
        )


class BusinessRuleException(APIException):
    def __init__(
        self,
        message: str = "Business rule validation failed.",
    ):
        super().__init__(
            message=message,
            code="BUSINESS_RULE_FAILED",
            status_code=422,
        )