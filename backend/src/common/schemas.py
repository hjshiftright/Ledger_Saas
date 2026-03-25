from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(20, ge=1, le=100, description="Items per page")


class SortParams(BaseModel):
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_desc: bool = Field(False, description="Sort descending")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated collection response."""
    items: List[T]
    total: int = Field(..., description="Total number of items matching the query")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Requested page size")
    pages: int = Field(..., description="Total number of pages")
    offset: int = Field(0, description="Absolute offset of the first item in this page")
    has_next: bool = Field(False, description="Whether a next page exists")
    has_previous: bool = Field(False, description="Whether a previous page exists")


class ErrorResponse(BaseModel):
    """Standardised error response (inspired by RFC 7807)."""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[dict] = Field(None, description="Additional error context")
