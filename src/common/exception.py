from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


class CustomHTTPException(HTTPException):
    """
    Custom HTTPException class to include custom error codes and messages.

    :param error_code: Custom error code.
    :type error_code: str
    :param error_message: Custom error message.
    :type error_message: str
    :param status_code: HTTP status code.
    :type status_code: int

    .. code-block:: python example usage
        raise CustomHTTPException(
            code_error="CUSTOM_ERROR_CODE",
            message_error="Custom error message",
            status_code=400
        )
    """

    def __init__(self, error_code: str, error_message: str, status_code: int):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(status_code=status_code, detail=error_message)

    def to_json_response(self) -> JSONResponse:
        """
        Convert the exception to a JSONResponse.

        :return: Response containing the custom error code and message.
        :rtype: JSONResponse
        """

        return JSONResponse(
            status_code=self.status_code,
            content=jsonable_encoder(
                {
                    "error_code": self.error_code,
                    "error_message": self.error_message,
                }
            ),
        )
