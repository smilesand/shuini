from __future__ import annotations

import argparse
import json
import math
import random
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any


def random_suffix(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1))
    return ordered[index]


@dataclass
class ResponseData:
    status: int
    body: Any
    latency_ms: float
    text: str


class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> ResponseData:
        headers = dict(headers or {})
        url = f"{self.base_url}{path}"
        if query:
            encoded = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
            url = f"{url}?{encoded}"

        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        request = urllib.request.Request(url, data=data, method=method.upper())
        for key, value in headers.items():
            request.add_header(key, value)

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        latency_ms = (time.perf_counter() - start) * 1000.0

        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = None

        return ResponseData(status=status, body=body, latency_ms=latency_ms, text=text)

    def upload_file(
        self,
        path: str,
        *,
        field_name: str,
        filename: str,
        content: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> ResponseData:
        boundary = f"----GitHubCopilotBoundary{random_suffix(12)}"
        parts = [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8"),
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
        payload = b"".join(parts)
        request_headers = dict(headers or {})
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        return self.request("POST", path, data=payload, headers=request_headers)


class Report:
    def __init__(self) -> None:
        self.tests: list[dict[str, Any]] = []
        self.metrics: dict[str, Any] = {}

    def add(self, name: str, category: str, passed: bool, *, expected: str, actual: str, latency_ms: float | None = None) -> None:
        self.tests.append(
            {
                "name": name,
                "category": category,
                "passed": passed,
                "expected": expected,
                "actual": actual,
                "latency_ms": None if latency_ms is None else round(latency_ms, 2),
            }
        )

    def summary(self) -> dict[str, int]:
        passed = sum(1 for item in self.tests if item["passed"])
        return {
            "total": len(self.tests),
            "passed": passed,
            "failed": len(self.tests) - passed,
        }


def body_message(response: ResponseData) -> str:
    if isinstance(response.body, dict):
        if "message" in response.body:
            return str(response.body["message"])
        if "detail" in response.body:
            return str(response.body["detail"])
    return response.text[:240]


def expect_status(report: Report, category: str, name: str, response: ResponseData, expected_status: int) -> None:
    report.add(
        name,
        category,
        response.status == expected_status,
        expected=f"HTTP {expected_status}",
        actual=f"HTTP {response.status}; {body_message(response)}",
        latency_ms=response.latency_ms,
    )


def benchmark(client: HttpClient, path: str, payload: dict[str, Any], *, total: int, concurrency: int) -> dict[str, Any]:
    latencies: list[float] = []
    failures = 0

    def call_once() -> float:
        response = client.request("POST", path, json_body=payload, timeout=30.0)
        if response.status != 200 or not isinstance(response.body, dict) or response.body.get("code") != 0:
            raise RuntimeError(f"unexpected response {response.status}: {body_message(response)}")
        return response.latency_ms

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(call_once) for _ in range(total)]
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except Exception:
                failures += 1
    duration_ms = (time.perf_counter() - start) * 1000.0
    return {
        "total": total,
        "success": len(latencies),
        "failures": failures,
        "concurrency": concurrency,
        "wall_time_ms": round(duration_ms, 2),
        "avg_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "p95_ms": round(percentile(latencies, 0.95), 2) if latencies else None,
        "max_ms": round(max(latencies), 2) if latencies else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run black-box API tests against the shuini_calculator backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", default="123456")
    args = parser.parse_args()

    client = HttpClient(args.base_url)
    report = Report()

    cleanup: dict[str, Any] = {"user": None, "project": None, "record": None}

    root = client.request("GET", "/")
    report.add(
        "服务根路径可访问",
        "smoke",
        root.status == 200 and isinstance(root.body, dict) and "docs" in root.body,
        expected="HTTP 200 and docs link",
        actual=f"HTTP {root.status}; {root.text[:120]}",
        latency_ms=root.latency_ms,
    )

    unauthorized_projects = client.request("GET", "/api/projects")
    expect_status(report, "security", "未登录访问项目列表被拒绝", unauthorized_projects, 401)

    wrong_login = client.request(
        "POST",
        "/api/auth/login",
        json_body={"username": args.admin_username, "password": f"{args.admin_password}x"},
    )
    expect_status(report, "security", "错误密码登录被拒绝", wrong_login, 401)

    admin_login = client.request(
        "POST",
        "/api/auth/login",
        json_body={"username": args.admin_username, "password": args.admin_password},
    )
    admin_ok = admin_login.status == 200 and isinstance(admin_login.body, dict) and admin_login.body.get("code") == 0
    report.add(
        "管理员登录成功",
        "auth",
        admin_ok,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {admin_login.status}; {body_message(admin_login)}",
        latency_ms=admin_login.latency_ms,
    )
    if not admin_ok:
        print(json.dumps({"error": "admin login failed", "report": report.tests}, ensure_ascii=False, indent=2))
        return 1

    admin_data = admin_login.body["data"]
    admin_headers = {"Authorization": f"Bearer {admin_data['access_token']}"}

    profile = client.request("GET", "/api/auth/profile", headers=admin_headers)
    report.add(
        "管理员资料查询成功",
        "auth",
        profile.status == 200 and isinstance(profile.body, dict) and profile.body.get("code") == 0,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {profile.status}; {body_message(profile)}",
        latency_ms=profile.latency_ms,
    )

    admin_users = client.request("GET", "/api/auth/users", headers=admin_headers)
    report.add(
        "管理员可查看用户列表",
        "security",
        admin_users.status == 200 and isinstance(admin_users.body, dict) and admin_users.body.get("code") == 0,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {admin_users.status}; {body_message(admin_users)}",
        latency_ms=admin_users.latency_ms,
    )

    tampered = client.request("GET", "/api/auth/profile", headers={"Authorization": f"Bearer {admin_data['access_token']}tampered"})
    expect_status(report, "security", "篡改 token 被拒绝", tampered, 401)

    injected_search = client.request(
        "GET",
        "/api/projects",
        headers=admin_headers,
        query={"search": "' OR 1=1 --", "page": 1, "page_size": 20},
    )
    report.add(
        "SQL 注入样式搜索未击穿查询",
        "security",
        injected_search.status == 200 and isinstance(injected_search.body, dict) and injected_search.body.get("code") == 0,
        expected="HTTP 200 and stable JSON shape",
        actual=f"HTTP {injected_search.status}; {body_message(injected_search)}",
        latency_ms=injected_search.latency_ms,
    )

    user_name = f"tester_{random_suffix().lower()}"
    create_user = client.request(
        "POST",
        "/api/auth/users",
        headers=admin_headers,
        json_body={"username": user_name, "email": "", "phone": "", "is_admin": False},
    )
    user_created = create_user.status == 200 and isinstance(create_user.body, dict) and create_user.body.get("code") == 0
    report.add(
        "管理员可创建普通用户",
        "auth",
        user_created,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {create_user.status}; {body_message(create_user)}",
        latency_ms=create_user.latency_ms,
    )
    if user_created:
        cleanup["user"] = user_name

    user_headers: dict[str, str] | None = None
    if user_created:
        user_login = client.request(
            "POST",
            "/api/auth/login",
            json_body={"username": user_name, "password": "123456"},
        )
        user_login_ok = user_login.status == 200 and isinstance(user_login.body, dict) and user_login.body.get("code") == 0
        report.add(
            "普通用户可使用默认密码登录",
            "auth",
            user_login_ok,
            expected="HTTP 200 and code=0",
            actual=f"HTTP {user_login.status}; {body_message(user_login)}",
            latency_ms=user_login.latency_ms,
        )
        if user_login_ok:
            user_headers = {"Authorization": f"Bearer {user_login.body['data']['access_token']}"}
            user_list_attempt = client.request("GET", "/api/auth/users", headers=user_headers)
            expect_status(report, "security", "普通用户访问用户列表被拒绝", user_list_attempt, 403)

    project_code = f"BB-{random_suffix()}"
    project_payload = {
        "project_code": project_code,
        "project_name": "黑盒测试项目",
        "requirements": "黑盒自动化验证用数据",
    }
    create_project = client.request("POST", "/api/projects", headers=admin_headers, json_body=project_payload)
    project_created = create_project.status == 200 and isinstance(create_project.body, dict) and create_project.body.get("code") == 0
    report.add(
        "项目创建成功",
        "business",
        project_created,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {create_project.status}; {body_message(create_project)}",
        latency_ms=create_project.latency_ms,
    )
    project_id = None
    if project_created:
        project_id = create_project.body["data"]["id"]
        cleanup["project"] = project_id

    duplicate_project = client.request("POST", "/api/projects", headers=admin_headers, json_body=project_payload)
    expect_status(report, "boundary", "重复项目编号被拒绝", duplicate_project, 422)

    record_payload = {
        "name": "黑盒测试配比",
        "category": "hpc",
        "project_id": project_id,
        "record_data": {
            "wb": 0.31,
            "mb": 520.0,
            "mc": 360.0,
            "m1": 80.0,
            "m2": 50.0,
            "m3": 20.0,
            "m4": 10.0,
            "mg": 980.0,
            "ms": 760.0,
            "mw": 161.2,
            "ma": 8.5,
            "alpha": 1.63,
            "trial_data": {"version": 1, "source": "blackbox"},
        },
    }
    if project_id is not None:
        create_record = client.request("POST", "/api/records", headers=admin_headers, json_body=record_payload)
        record_created = create_record.status == 200 and isinstance(create_record.body, dict) and create_record.body.get("code") == 0
        report.add(
            "记录创建成功",
            "business",
            record_created,
            expected="HTTP 200 and code=0",
            actual=f"HTTP {create_record.status}; {body_message(create_record)}",
            latency_ms=create_record.latency_ms,
        )
        if record_created:
            cleanup["record"] = create_record.body["data"]["id"]

        project_records = client.request("GET", f"/api/projects/{project_id}/records", headers=admin_headers)
        has_record = (
            project_records.status == 200
            and isinstance(project_records.body, dict)
            and project_records.body.get("code") == 0
            and any(
                item.get("name") == "黑盒测试配比"
                and isinstance(item.get("record_data"), dict)
                and item["record_data"].get("trial_data", {}).get("source") == "blackbox"
                for item in project_records.body.get("data", [])
            )
        )
        report.add(
            "项目记录列表返回新建记录",
            "business",
            has_record,
            expected="HTTP 200 and contains created record",
            actual=f"HTTP {project_records.status}; {body_message(project_records)}",
            latency_ms=project_records.latency_ms,
        )

    valid_water_binder = client.request(
        "POST",
        "/api/water-binder",
        json_body={"fcuk": 60, "fb": 48, "aa": 0.33, "ab": 1.09, "ac": -49.54},
    )
    report.add(
        "水胶比正常计算成功",
        "boundary",
        valid_water_binder.status == 200 and isinstance(valid_water_binder.body, dict) and valid_water_binder.body.get("code") == 0,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {valid_water_binder.status}; {body_message(valid_water_binder)}",
        latency_ms=valid_water_binder.latency_ms,
    )

    invalid_water_binder = client.request(
        "POST",
        "/api/water-binder",
        json_body={"fcuk": 0, "fb": 48, "aa": 0.33, "ab": 1.09, "ac": -49.54},
    )
    expect_status(report, "boundary", "水胶比零边界输入被拒绝", invalid_water_binder, 422)

    aggregate_near_limit = client.request(
        "POST",
        "/api/aggregate",
        json_body={"vg": 0.7, "rhog": 2700, "beta_s": 0.9999, "rhos": 2600},
    )
    report.add(
        "骨料砂率接近上限仍可计算",
        "boundary",
        aggregate_near_limit.status == 200 and isinstance(aggregate_near_limit.body, dict) and aggregate_near_limit.body.get("code") == 0,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {aggregate_near_limit.status}; {body_message(aggregate_near_limit)}",
        latency_ms=aggregate_near_limit.latency_ms,
    )

    aggregate_limit = client.request(
        "POST",
        "/api/aggregate",
        json_body={"vg": 0.7, "rhog": 2700, "beta_s": 1, "rhos": 2600},
    )
    expect_status(report, "boundary", "骨料砂率上限输入被拒绝", aggregate_limit, 422)

    water_admix_limit = client.request(
        "POST",
        "/api/water-admixture",
        json_body={"mb": 520, "wb": 0.31, "alpha": 100},
    )
    report.add(
        "外加剂掺量 100% 边界可计算",
        "boundary",
        water_admix_limit.status == 200 and isinstance(water_admix_limit.body, dict) and water_admix_limit.body.get("code") == 0,
        expected="HTTP 200 and code=0",
        actual=f"HTTP {water_admix_limit.status}; {body_message(water_admix_limit)}",
        latency_ms=water_admix_limit.latency_ms,
    )

    water_admix_exceed = client.request(
        "POST",
        "/api/water-admixture",
        json_body={"mb": 520, "wb": 0.31, "alpha": 100.01},
    )
    expect_status(report, "boundary", "外加剂掺量超上限被拒绝", water_admix_exceed, 422)

    hpc_trial_payload = {
        "wb": 0.31,
        "beta_s": 41,
        "mb": 520,
        "mc": 360,
        "m1": 80,
        "m2": 50,
        "m3": 20,
        "m4": 10,
        "mg": 980,
        "ms": 760,
        "mw": 161.2,
        "ma": 8.5,
        "alpha": 1.63,
        "batch_volume": 20,
        "workability_binder_delta": 10,
        "workability_sand_ratio_delta": 1,
        "workability_alpha_delta": 0.2,
        "delta_wb": 0.02,
        "delta_bs": 2,
        "strength0": 65,
        "strength_p": 71,
        "strength_n": 60,
        "target_strength": 68,
        "wb_adj": 0.3,
        "mb_adj": 530,
        "sand_ratio_adj": 42,
        "alpha_adj": 1.8,
        "measured_density": 2430,
    }
    valid_hpc_trial = client.request("POST", "/api/hpc-trial", json_body=hpc_trial_payload)
    hpc_valid = (
        valid_hpc_trial.status == 200
        and isinstance(valid_hpc_trial.body, dict)
        and valid_hpc_trial.body.get("code") == 0
        and isinstance(valid_hpc_trial.body.get("data", {}).get("strength_mixes"), list)
    )
    report.add(
        "高性能试配正常计算成功",
        "boundary",
        hpc_valid,
        expected="HTTP 200 and strength_mixes list",
        actual=f"HTTP {valid_hpc_trial.status}; {body_message(valid_hpc_trial)}",
        latency_ms=valid_hpc_trial.latency_ms,
    )

    invalid_hpc_trial = dict(hpc_trial_payload)
    invalid_hpc_trial["batch_volume"] = 0
    invalid_hpc = client.request("POST", "/api/hpc-trial", json_body=invalid_hpc_trial)
    expect_status(report, "boundary", "试配批量为零被拒绝", invalid_hpc, 422)

    invalid_upload_type = client.upload_file(
        "/api/upload-fit",
        field_name="file",
        filename="bad.txt",
        content=b"1,2,3\n4,5,6\n",
        content_type="text/plain",
    )
    expect_status(report, "security", "非法上传文件类型被拒绝", invalid_upload_type, 400)

    oversized_csv = b"a,b,c\n" + (b"1,2,3\n" * 900000)
    oversized_upload = client.upload_file(
        "/api/upload-fit",
        field_name="file",
        filename="large.csv",
        content=oversized_csv,
        content_type="text/csv",
    )
    expect_status(report, "security", "超大上传文件被拒绝", oversized_upload, 400)

    report.metrics["water_binder_benchmark"] = benchmark(
        client,
        "/api/water-binder",
        {"fcuk": 60, "fb": 48, "aa": 0.33, "ab": 1.09, "ac": -49.54},
        total=60,
        concurrency=6,
    )
    report.metrics["hpc_trial_benchmark"] = benchmark(
        client,
        "/api/hpc-trial",
        hpc_trial_payload,
        total=24,
        concurrency=4,
    )

    if cleanup["record"] is not None:
        delete_record = client.request("DELETE", f"/api/records/{cleanup['record']}", headers=admin_headers)
        report.add(
            "测试记录清理成功",
            "cleanup",
            delete_record.status == 200 and isinstance(delete_record.body, dict) and delete_record.body.get("code") == 0,
            expected="HTTP 200 and code=0",
            actual=f"HTTP {delete_record.status}; {body_message(delete_record)}",
            latency_ms=delete_record.latency_ms,
        )

    if cleanup["project"] is not None:
        delete_project = client.request("DELETE", f"/api/projects/{cleanup['project']}", headers=admin_headers)
        report.add(
            "测试项目清理成功",
            "cleanup",
            delete_project.status == 200 and isinstance(delete_project.body, dict) and delete_project.body.get("code") == 0,
            expected="HTTP 200 and code=0",
            actual=f"HTTP {delete_project.status}; {body_message(delete_project)}",
            latency_ms=delete_project.latency_ms,
        )

    if cleanup["user"] is not None:
        delete_user = client.request("DELETE", f"/api/auth/users/{cleanup['user']}", headers=admin_headers)
        report.add(
            "测试用户清理成功",
            "cleanup",
            delete_user.status == 200 and isinstance(delete_user.body, dict) and delete_user.body.get("code") == 0,
            expected="HTTP 200 and code=0",
            actual=f"HTTP {delete_user.status}; {body_message(delete_user)}",
            latency_ms=delete_user.latency_ms,
        )

    result = {
        "base_url": args.base_url,
        "summary": report.summary(),
        "tests": report.tests,
        "metrics": report.metrics,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["summary"]["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())