"""
授权激活路由
============
提供桌面/单机版的授权状态查询与激活接口。

  GET  /api/license/status    -> 机器指纹、激活/试用状态
  POST /api/license/activate   -> 提交授权码完成激活

契约与 desktop/main.cjs、desktop/activation.html 保持一致：
返回统一信封 ``{code, message, data}``，其中 data 含 ``can_use``、``activated``、
``fingerprint`` 等字段。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core import license as license_core
from models.schemas import ok

router = APIRouter()


class ActivateRequest(BaseModel):
    license_code: str = Field(..., min_length=1)


@router.get("/license/status")
def license_status():
    try:
        return ok(license_core.get_license_status())
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="获取授权状态失败")


@router.post("/license/activate")
def license_activate(req: ActivateRequest):
    try:
        result = license_core.activate_license(req.license_code)
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result.get("message", "激活失败"))
        return ok(result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="激活失败")
