from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class ErrorResponse(BaseModel):
    """Generic error response."""
    detail: str