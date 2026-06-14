from fastapi import APIRouter, HTTPException, Header
from models.schemas import (
    LoginRequest, TokenResponse, ResetPasswordRequest,
    UserCreateRequest, ProfileUpdateRequest, ChangePasswordRequest, ok,
)
from database import (
    create_session,
    create_user,
    delete_user,
    get_session_user,
    get_user,
    list_users,
    password_needs_rehash,
    revoke_session,
    update_password,
    update_profile,
    upgrade_password_hash,
    verify_password,
)


def verify_token(token: str) -> str | None:
    return get_session_user(token)


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    return authorization[7:]


def require_auth(authorization: str | None) -> str:
    """从 Authorization Header 中提取并验证 token，返回用户名；失败时抛出 401"""
    username = verify_token(extract_bearer_token(authorization))
    if not username:
        raise HTTPException(status_code=401, detail="令牌无效或已过期，请重新登录")
    return username


def get_current_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI 依赖注入版本（向后兼容）"""
    return require_auth(authorization)


def require_admin(username: str):
    user = get_user(username)
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


router = APIRouter()


@router.post("/auth/login")
def login(req: LoginRequest):
    try:
        user = get_user(req.username)
        if not user or not verify_password(req.password, user["password"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if password_needs_rehash(user["password"]):
            upgrade_password_hash(req.username, req.password)
            user = get_user(req.username)
            if not user:
                raise HTTPException(status_code=500, detail="登录失败: 用户信息刷新失败")

        token = create_session(req.username)
        return ok(TokenResponse(
            access_token=token,
            token_type="bearer",
            username=req.username,
            is_admin=bool(user["is_admin"]),
            must_reset=bool(user["must_reset"]),
        ).model_dump())
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="登录失败")


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    try:
        token = extract_bearer_token(authorization)
        username = verify_token(token)
        if not username:
            raise HTTPException(status_code=401, detail="令牌无效或已过期，请重新登录")
        revoke_session(token)
        return ok({"ok": True})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="退出登录失败")


@router.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest, authorization: str | None = Header(default=None)):
    """首次登录后修改默认密码"""
    try:
        token_user = require_auth(authorization)
        update_password(token_user, req.new_password, must_reset=False)
        return ok({"ok": True})
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="密码修改失败")


@router.get("/auth/users")
def api_list_users(authorization: str | None = Header(default=None)):
    try:
        username = require_auth(authorization)
        require_admin(username)
        return ok(list_users())
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="获取用户列表失败")


@router.post("/auth/users")
def api_create_user(req: UserCreateRequest, authorization: str | None = Header(default=None)):
    try:
        username = require_auth(authorization)
        require_admin(username)
        existing = get_user(req.username)
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        user = create_user(req.username, "123456", req.is_admin,
                           email=req.email, phone=req.phone)
        return ok(user)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="创建用户失败")


@router.post("/auth/users/{target_username}/reset-password")
def api_admin_reset_password(target_username: str, req: ResetPasswordRequest,
                              authorization: str | None = Header(default=None)):
    """管理员重置任意用户密码"""
    try:
        username = require_auth(authorization)
        require_admin(username)
        user = get_user(target_username)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        update_password(target_username, req.new_password, must_reset=True)
        return ok({"ok": True})
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="重置密码失败")


@router.delete("/auth/users/{target_username}")
def api_delete_user(target_username: str, authorization: str | None = Header(default=None)):
    try:
        username = require_auth(authorization)
        require_admin(username)
        if target_username == username:
            raise HTTPException(status_code=400, detail="不能删除自己")
        user = get_user(target_username)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        delete_user(target_username)
        return ok({"ok": True})
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="删除用户失败")


@router.get("/auth/profile")
def api_get_profile(authorization: str | None = Header(default=None)):
    """获取当前登录用户的个人资料"""
    try:
        username = require_auth(authorization)
        user = get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return ok({
            "username": user["username"],
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "is_admin": bool(user["is_admin"]),
            "must_reset": bool(user["must_reset"]),
            "created_at": user["created_at"],
        })
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="获取个人资料失败")


@router.put("/auth/profile")
def api_update_profile(req: ProfileUpdateRequest, authorization: str | None = Header(default=None)):
    """更新当前用户的邮箱和手机号"""
    try:
        username = require_auth(authorization)
        update_profile(username, req.email, req.phone)
        user = get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return ok({
            "username": user["username"],
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
        })
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="更新个人资料失败")


@router.post("/auth/change-password")
def api_change_password(req: ChangePasswordRequest, authorization: str | None = Header(default=None)):
    """修改当前用户密码（需验证原密码）"""
    try:
        username = require_auth(authorization)
        user = get_user(username)
        if not user or not verify_password(req.old_password, user["password"]):
            raise HTTPException(status_code=401, detail="原密码错误")
        update_password(username, req.new_password, must_reset=False)
        return ok({"ok": True})
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="修改密码失败")
