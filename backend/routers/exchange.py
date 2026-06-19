"""
导入/导出路由
============
提供 Excel 模板下载、单条/项目导出、导入校验等功能。
"""

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import Response
from starlette.responses import StreamingResponse

from models.schemas import ok
from database import (
    get_project,
    list_project_records,
    get_record,
    save_record,
    create_project,
    is_admin_user,
)
from routers.auth import get_current_user
from services.excel_export import (
    generate_template_bytes,
    generate_record_export_bytes,
    generate_project_export_bytes,
    _export_filename,
)
from services.excel_import import parse_and_validate_excel

router = APIRouter(prefix="/exchange", tags=["import-export"])

# ── 模板下载 ──────────────────────────────────────────────────────────────────

@router.get("/template", summary="下载导入模板")
def download_template(category: str = Query("hpc", description="配比类别: hpc | uhpc")):
    if category not in ("hpc", "uhpc"):
        raise HTTPException(status_code=422, detail="category 必须为 hpc 或 uhpc")
    try:
        content = generate_template_bytes(category)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{category}_import_template.xlsx"',
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模板生成失败: {e}")


# ── 导出 ──────────────────────────────────────────────────────────────────────

@router.get("/export/record/{record_id}", summary="导出单条记录")
def export_record(record_id: int, username=Depends(get_current_user)):
    record = get_record(
        record_id,
        username=username,
        is_admin=is_admin_user(username),
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    try:
        project_name = ""
        pid = record.get("project_id")
        if pid:
            project = get_project(pid, username=username, is_admin=is_admin_user(username))
            if project:
                project_name = project.get("project_name", "")

        content = generate_record_export_bytes(record, project_name)
        name = record.get("name", "record")
        filename = _export_filename(name)
        encoded_filename = quote(filename, safe="")
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")


@router.get("/export/project/{project_id}", summary="导出项目及其所有记录")
def export_project(project_id: int, username=Depends(get_current_user)):
    project = get_project(project_id, username=username, is_admin=is_admin_user(username))
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    try:
        records = list_project_records(project_id, username=username, is_admin=is_admin_user(username))
        content = generate_project_export_bytes(project, records)
        code = project.get("project_code", "project")
        filename = _export_filename(code)
        encoded_filename = quote(filename, safe="")
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")


# ── 导入校验 ──────────────────────────────────────────────────────────────────

@router.post("/import/validate", summary="导入 Excel 并校验关键参数")
async def import_validate(
    file: UploadFile = File(...),
    username=Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="仅支持 .xlsx 格式文件")

    try:
        file_bytes = await file.read()
        result = parse_and_validate_excel(file_bytes, file.filename)
        return ok(result)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"文件解析失败: {e}")


# ── 导入保存 ──────────────────────────────────────────────────────────────────

@router.post("/import/record", summary="导入单条记录并保存")
async def import_record(
    file: UploadFile = File(...),
    project_id: int | None = Query(None, description="关联项目 ID"),
    dry_run: bool = Query(False, description="仅校验不保存"),
    username=Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="仅支持 .xlsx 格式文件")

    try:
        file_bytes = await file.read()
        result = parse_and_validate_excel(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"文件解析失败: {e}")

    validation = result.get("validation", {})
    if not validation.get("valid"):
        return ok({
            "saved": False,
            "category": result.get("category"),
            "data": result.get("data"),
            "validation": validation,
            "message": "校验未通过，请修正后重新导入",
        })

    if dry_run:
        return ok({
            "saved": False,
            "category": result.get("category"),
            "data": result.get("data"),
            "validation": validation,
            "message": "校验通过（dry_run 模式，未实际保存）",
        })

    # 保存记录
    try:
        data = result.get("data", {})
        category = result.get("category", "hpc")
        name = data.get("record_name") or f"导入_{file.filename.replace('.xlsx', '')}"

        record_payload = {
            "name": str(name),
            "category": category,
            "project_id": project_id,
            "record_data": data,
            "source": "import",
        }
        rid = save_record(record_payload, username=username, is_admin=is_admin_user(username))
        return ok({
            "saved": True,
            "record_id": rid,
            "category": category,
            "data": data,
            "validation": validation,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")
