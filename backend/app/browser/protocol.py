from typing import Any, Optional, Union
from pydantic import BaseModel, Field

class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[dict[str, Any]] = Field(default_factory=dict)

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[JsonRpcError] = None

class JsonRpcNotification(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict[str, Any]] = Field(default_factory=dict)
