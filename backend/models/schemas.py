from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Literal


def ok(data: Any = None) -> dict:
    return {'code': 0, 'message': 'ok', 'data': data}


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)

class TokenResponse(BaseModel):
    access_token: str; token_type: str; username: str
    is_admin: bool = False; must_reset: bool = False

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=100)

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: str = Field(default='', max_length=100)
    phone: str = Field(default='', max_length=30)
    is_admin: bool = False

class ProfileUpdateRequest(BaseModel):
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=4, max_length=100)

class UserResponse(BaseModel):
    id: int; username: str; email: str = ''; phone: str = ''
    is_admin: bool; must_reset: bool; created_at: str

class RecordSaveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: Optional[int] = Field(default=None, gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default='hpc', pattern=r'^(hpc|uhpc)$')
    project_id: Optional[int] = Field(default=None, gt=0)
    record_data: Optional[dict[str, Any]] = None
    source: str = Field(default='system', pattern=r'^(system|import)$')

class RecordResponse(BaseModel):
    id: int; name: str; category: str = 'hpc'; created_by: str; created_at: str
    project_id: Optional[int]=None
    record_data: dict[str, Any] = Field(default_factory=dict)
    source: str = 'system'

class ProjectCreateRequest(BaseModel):
    project_code: str = Field(..., min_length=1, max_length=50)
    project_name: str = Field(..., min_length=1, max_length=200)
    requirements: str = Field(default='', max_length=2000)
    source: str = Field(default='system', pattern=r'^(system|import)$')

class ProjectUpdateRequest(BaseModel):
    project_code: Optional[str] = Field(default=None, max_length=50)
    project_name: Optional[str] = Field(default=None, max_length=200)
    requirements: Optional[str] = Field(default=None, max_length=2000)

class ProjectResponse(BaseModel):
    id: int; project_code: str; project_name: str; requirements: str = ''
    created_by: str; created_at: str; updated_at: str; record_count: int = 0
    source: str = 'system'


class RecycleBinItemResponse(BaseModel):
    item_type: Literal['project', 'record']
    id: int
    name: str
    category: Optional[str] = None
    project_code: str = ''
    project_name: str = ''
    project_id: Optional[int] = None
    created_by: str
    created_at: str
    deleted_at: Optional[str] = None
    deleted_by: str = ''
    deleted_with_project: bool = False


class ClientLogRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    source: str = Field(default='frontend', min_length=1, max_length=50)
    event: Optional[str] = Field(default=None, max_length=100)
    message: str = Field(..., min_length=1, max_length=4000)
    route: Optional[str] = Field(default=None, max_length=500)
    url: Optional[str] = Field(default=None, max_length=1000)
    session_id: Optional[str] = Field(default=None, max_length=100)
    request_id: Optional[str] = Field(default=None, max_length=100)
    user_agent: Optional[str] = Field(default=None, max_length=1000)
    created_at: Optional[str] = Field(default=None, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
