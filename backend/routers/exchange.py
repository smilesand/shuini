"""
Excel 导入路由
============
提供 Excel 导入模板下载、导入校验和导入保存功能。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import Response

from models.schemas import ok
from database import (
    save_record,
    create_project,
    is_admin_user,
)
from routers.auth import get_current_user
from services.excel_export import (
    generate_template_bytes,
)
from services.excel_import import parse_and_validate_excel, parse_project_import_excel

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


# ── 项目导入 ──────────────────────────────────────────────────────────────────

@router.post("/import/project", summary="导入项目 Excel（含项目信息与所有记录）")
async def import_project(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="仅校验不保存"),
    username=Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="仅支持 .xlsx 格式文件")

    try:
        file_bytes = await file.read()
        result = parse_project_import_excel(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"文件解析失败: {e}")

    project_info = result.get("project", {})
    records = result.get("records", [])
    all_valid = result.get("all_valid", False)

    if dry_run:
        return ok({
            "saved": False,
            "project": project_info,
            "records": records,
            "all_valid": all_valid,
            "message": "校验完成（dry_run 模式，未实际保存）",
        })

    # 创建项目
    project_code = project_info.get("project_code") or f"IMP_{file.filename.replace('.xlsx', '')[:20]}"
    project_name = project_info.get("project_name") or f"导入项目_{file.filename.replace('.xlsx', '')[:20]}"
    requirements = project_info.get("requirements", "")

    is_admin = is_admin_user(username)
    try:
        project_row = create_project(project_code, project_name, username, requirements, source="import")
        pid = project_row["id"]
    except RuntimeError as e:
        # 项目编号重复时尝试加后缀
        import time
        suffix = int(time.time()) % 10000
        alt_code = f"{project_code[:40]}_{suffix}"
        try:
            project_row = create_project(alt_code, project_name, username, requirements, source="import")
            pid = project_row["id"]
        except RuntimeError as e2:
            raise HTTPException(status_code=422, detail=str(e2))

    # 逐条创建记录
    created_ids: list[int] = []
    record_results: list[dict[str, Any]] = []
    for rec in records:
        try:
            record_payload = {
                "name": rec.get("name", "未命名"),
                "category": rec.get("category", "hpc"),
                "project_id": pid,
                "record_data": rec.get("data", {}),
                "source": "import",
            }
            rid = save_record(record_payload, username=username, is_admin=is_admin)
            created_ids.append(rid)
            record_results.append({
                "name": rec.get("name"),
                "record_id": rid,
                "category": rec.get("category"),
                "validation": rec.get("validation"),
                "saved": True,
            })
        except Exception as e:
            record_results.append({
                "name": rec.get("name"),
                "record_id": None,
                "category": rec.get("category"),
                "validation": rec.get("validation"),
                "saved": False,
                "error": str(e),
            })

    return ok({
        "saved": True,
        "project_id": pid,
        "project_code": project_code,
        "project_name": project_name,
        "records_created": len(created_ids),
        "records_total": len(records),
        "all_valid": all_valid,
        "record_details": record_results,
    })
