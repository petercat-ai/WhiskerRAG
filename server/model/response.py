from pydantic import BaseModel
from typing import Optional, Any
from typing import TypeVar, Generic


T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
