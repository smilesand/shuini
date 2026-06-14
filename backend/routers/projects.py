from fastapi import APIRouter, HTTPException, Depends
from models.schemas import (
    ProjectCreateRequest, ProjectUpdateRequest, ProjectResponse, RecordResponse, ok,
)
from database import (
    create_project, list_projects, get_project,
    update_project, delete_project, list_project_records, is_admin_user,
)
from routers.auth import get_current_user

router = APIRouter()


@router.post("/projects", summary="创建项目")
def api_create_project(req: ProjectCreateRequest, username=Depends(get_current_user)):
    try:
        p = create_project(req.project_code, req.project_name, username, req.requirements)
        return ok(ProjectResponse(**p).model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/projects", summary="查询项目列表")
def api_list_projects(search: str = "", page: int = 1, page_size: int = 20,
                      username=Depends(get_current_user)):
    try:
        result = list_projects(search, page, page_size, username=username, is_admin=is_admin_user(username))
        result["items"] = [ProjectResponse(**it).model_dump() for it in result["items"]]
        return ok(result)
    except Exception:
        raise HTTPException(status_code=500, detail="获取项目列表失败")


@router.get("/projects/{project_id}", summary="获取项目详情")
def api_get_project(project_id: int, username=Depends(get_current_user)):
    p = get_project(project_id, username=username, is_admin=is_admin_user(username))
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ok(ProjectResponse(**p).model_dump())


@router.put("/projects/{project_id}", summary="更新项目")
def api_update_project(project_id: int, req: ProjectUpdateRequest, username=Depends(get_current_user)):
    is_admin = is_admin_user(username)
    if get_project(project_id, username=username, is_admin=is_admin) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        update_project(
            project_id,
            req.project_code,
            req.project_name,
            req.requirements,
            username=username,
            is_admin=is_admin,
        )
        p = get_project(project_id, username=username, is_admin=is_admin)
        return ok(ProjectResponse(**p).model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/projects/{project_id}", summary="删除项目")
def api_delete_project(project_id: int, username=Depends(get_current_user)):
    is_admin = is_admin_user(username)
    if get_project(project_id, username=username, is_admin=is_admin) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        delete_project(project_id, username=username, is_admin=is_admin)
        return ok({"deleted": project_id})
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/projects/{project_id}/records", summary="获取项目下的配比记录")
def api_project_records(project_id: int, username=Depends(get_current_user)):
    is_admin = is_admin_user(username)
    if get_project(project_id, username=username, is_admin=is_admin) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    records = list_project_records(project_id, username=username, is_admin=is_admin)
    return ok([RecordResponse(**record).model_dump() for record in records])
