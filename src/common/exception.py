from typing import Union
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .error_codes import SfsErrorCodes


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


async def custom_exception_handler(request: Request, exc: Union[CustomHTTPException, Exception]) -> JSONResponse:
    """
    Custom exception handler for handling custom exceptions.

    :param request: Request object.
    :type request: Request
    :param exc: Custom exception object.
    :type exc: CustomHTTPException
    :return: JSONResponse containing the custom error code and message.
    :rtype: JSONResponse
    """

    return exc.to_json_response()


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Exception handler for handling internal server errors.

    :param request: Request object.
    :type request: Request
    :param exc: Exception object.
    :type exc: Exception
    :return: JSONResponse containing the error code and message.
    :rtype: JSONResponse
    """

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            {
                "error_code": SfsErrorCodes.INTERNAL_SERVER_ERROR,
                "error_message": str(exc),
            }
        ),
    )


async def bad_request_error_handler(request: Request, exc: Union[RequestValidationError, Exception]) -> JSONResponse:
    """
    Exception handler for handling bad request errors.
    :param request:
    :type request:
    :param exc:
    :type exc:
    :return:
    :rtype:
    """

    def _format_error(err):
        return {
            "field": err["loc"][-1],
            "message": err.get("msg", ""),
        }

    errors = [_format_error(err) for err in exc.errors()]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "code_error": SfsErrorCodes.REQUEST_VALIDATION_ERROR,
                "message_error": str(errors),
            }
        ),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup custom exception handlers for the FastAPI application.
    :param app:
    :type app:
    :return:
    :rtype:
    """
    app.add_exception_handler(CustomHTTPException, custom_exception_handler)
    app.add_exception_handler(Exception, internal_server_error_handler)
    app.add_exception_handler(RequestValidationError, bad_request_error_handler)
