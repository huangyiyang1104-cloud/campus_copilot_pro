from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """前端提交的登录参数"""

    username: str = Field(min_length=1, max_length=32, description="账号")
    password: str = Field(min_length=1, max_length=64, description="密码")


class UserInfo(BaseModel):
    """返回给前端的用户信息（不含密码）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str


class TokenResponse(BaseModel):
    """AT 放在响应体里，RT 走 httpOnly Cookie，不会出现在这里"""

    access_token: str = Field(description="访问令牌，放在 Authorization: Bearer 后面")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(description="access_token 有效期（秒）")


class LoginResponse(TokenResponse):
    user: UserInfo
