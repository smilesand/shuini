"""配比记录保存/查询"""
from fastapi import APIRouter, Header, HTTPException
from routers.auth import require_auth
from models.schemas import RecordResponse, RecordSaveRequest, ok
from database import save_record, list_records, delete_record, is_admin_user

router = APIRouter()


@router.post("/records")
def api_save_record(req: RecordSaveRequest, authorization: str | None = Header(default=None)):
    try:
        username = require_auth(authorization)
        # 仅更新客户端显式提交的字段，避免主配比保存时误清空试配快照等扩展数据。
        payload = req.model_dump(exclude_unset=True)
        if req.id is None and "category" not in payload:
            payload["category"] = req.category
        rid = save_record(payload, username=username, is_admin=is_admin_user(username))
        return ok({"ok": True, "id": rid})
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="保存记录失败")


@router.get("/records")
def api_list_records(authorization: str | None = Header(default=None), category: str | None = None,
                      search: str = "", page: int = 1, page_size: int = 20,
                      project_id: int | None = None):
    try:
        username = require_auth(authorization)
        result = list_records(
            category,
            search,
            page,
            page_size,
            project_id=project_id,
            username=username,
            is_admin=is_admin_user(username),
        )
        result["items"] = [RecordResponse(**item).model_dump() for item in result["items"]]
        return ok(result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="查询记录失败")


@router.delete("/records/{record_id}")
def api_delete_record(record_id: int, authorization: str | None = Header(default=None)):
    try:
        username = require_auth(authorization)
        delete_record(record_id, username=username, is_admin=is_admin_user(username))
        return ok({"ok": True})
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="删除记录失败")
