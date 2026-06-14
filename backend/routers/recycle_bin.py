from fastapi import APIRouter, Depends, HTTPException

from database import (
    is_admin_user,
    list_recycle_bin,
    purge_project,
    purge_record,
    restore_project,
    restore_record,
)
from models.schemas import RecycleBinItemResponse, ok
from routers.auth import get_current_user


router = APIRouter()


@router.get("/recycle-bin", summary="分页查询回收站")
def api_list_recycle_bin(
    item_type: str = "all",
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    username=Depends(get_current_user),
):
    try:
        result = list_recycle_bin(
            item_type=item_type,
            search=search,
            page=page,
            page_size=page_size,
            username=username,
            is_admin=is_admin_user(username),
        )
        result["items"] = [RecycleBinItemResponse(**item).model_dump() for item in result["items"]]
        return ok(result)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="获取回收站数据失败")


@router.post("/recycle-bin/projects/{project_id}/restore", summary="恢复回收站项目")
def api_restore_project(project_id: int, username=Depends(get_current_user)):
    try:
        restore_project(project_id, username=username, is_admin=is_admin_user(username))
        return ok({"restored": project_id, "item_type": "project"})
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="恢复项目失败")


@router.post("/recycle-bin/records/{record_id}/restore", summary="恢复回收站记录")
def api_restore_record(record_id: int, username=Depends(get_current_user)):
    try:
        restore_record(record_id, username=username, is_admin=is_admin_user(username))
        return ok({"restored": record_id, "item_type": "record"})
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="恢复记录失败")


@router.delete("/recycle-bin/projects/{project_id}", summary="物理删除回收站项目")
def api_purge_project(project_id: int, username=Depends(get_current_user)):
    try:
        purge_project(project_id, username=username, is_admin=is_admin_user(username))
        return ok({"deleted": project_id, "item_type": "project"})
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="彻底删除项目失败")


@router.delete("/recycle-bin/records/{record_id}", summary="物理删除回收站记录")
def api_purge_record(record_id: int, username=Depends(get_current_user)):
    try:
        purge_record(record_id, username=username, is_admin=is_admin_user(username))
        return ok({"deleted": record_id, "item_type": "record"})
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="彻底删除记录失败")