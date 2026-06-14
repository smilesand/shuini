# 水泥配比计算器

基于 Vue 3 + FastAPI 的前后端分离配比计算系统。

## 架构说明

- 前端：`frontend/` 使用 Vue 3 + Vite + Pinia + Vue Router。
- 后端：`backend/` 使用 FastAPI，统一对外暴露 `/api/*` 计算、认证、项目、记录、回收站接口。
- 前后端调用：浏览器端通过 `frontend/src/utils/request.ts` 中的 Axios 实例访问接口，默认请求 `/api`。
	- 开发模式下由 `frontend/vite.config.js` 代理到 `http://localhost:8000`。
	- 打包后的 Web 包和桌面版都由后端直接托管 `frontend/dist`，浏览器或桌面壳访问同一个本地服务入口。

## 双版本打包设计

项目仍然只维护一套前后端业务代码，打包层分为两种产物：

- Web 版：打包出 `frontend/dist` + `wtcmd-platform-backend`，后端通过 `SC_FRONTEND_DIST` 同时提供页面和 API。
- 桌面版：产物名称统一为 `WTCMD Platform`，在同一套后端二进制外面包一层 Electron 外壳，本地启动后端并加载本地页面，不需要额外部署服务器。

桌面壳代码位于 `desktop/`，统一打包脚本位于 `scripts/package.py`。

## 项目结构

```
shuini_calculator/
├── frontend/          # Vue 3 + Vite + Pinia + Vue Router
└── backend/           # Python FastAPI 计算服务
```

## 快速启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 2. 启动前端

```bash
cd frontend
npm install   # 首次运行
npm run dev
```

前端地址：http://localhost:5173

## 常用验证命令

### 后端

```bash
cd backend
python -m unittest tests.test_hpc_trial_service tests.test_record_trial_data
```

### 前端

```bash
cd frontend
npm run build
npm run build:web
npm run build:desktop
npm run typecheck
```

- `npm run build:web` 使用生产模式，读取 `frontend/.env.production`，面向 Web 部署。
- `npm run build:desktop` 使用桌面模式，读取 `frontend/.env.desktop`，面向内置本地后端的桌面版。
- `scripts/package.py` 会按产物类型自动选择对应前端构建：web 产物走 `build:web`，desktop 产物走 `build:desktop`。

## 一键打包

要求：

- Windows 上执行 PowerShell 包装脚本。
- Debian 上执行 shell 包装脚本。
- 桌面版必须在目标平台原生打包，当前脚本不做跨平台交叉编译。

### Windows

```powershell
.\package-web.ps1
.\package-desktop.ps1
.\package-all.ps1
```

### Debian

```bash
bash ./package-web.sh
bash ./package-desktop.sh
bash ./package-all.sh
```

### 产物目录

- Web 版：`release/web/windows` 或 `release/web/debian`
- 桌面版：`release/desktop/windows` 或 `release/desktop/debian`

Web 包启动后默认监听 `http://127.0.0.1:8000`。

## Nginx 部署说明

前端使用 Vue Router 的 history 模式（`createWebHistory()`）。
如果 Nginx 没有把前端子路由回退到 `index.html`，访问或刷新诸如 `/projects`、`/calc/hpc`、`/adapt/hpc` 这样的地址时会直接返回 404。

可参考 [frontend/nginx.conf.example](frontend/nginx.conf.example) 中的配置，核心规则如下：

```nginx
location / {
	try_files $uri $uri/ /index.html;
}
```

如果前后端通过同域名部署，当前项目前端接口默认走 `/api`，Nginx 还需要把 `/api/` 反向代理到 FastAPI 服务。

### 黑盒 API 回归

```bash
python document/run_blackbox_tests.py
```

## 功能

| 标签页 | 接口 | 说明 |
|--------|------|------|
| 水胶比 | `POST /api/water-binder` | 鲍罗米公式计算 W/B |
| 水胶比 | `POST /api/fit-coefficients` | 从 CSV 拟合回归系数 |
| 骨料用量 | `POST /api/aggregate` | 计算 mg、ms |
| 胶凝材料 | `POST /api/binder` | 计算 ρb、Vp、mb 及各组分 |
| 水和外加剂 | `POST /api/water-admixture` | 计算 mw、ma |

## CSV 导入格式

回归系数拟合 CSV（无表头，每行三列）：

```
胶水比, 胶材强度fb(MPa), 混凝土强度fcu(MPa)
2.5, 45, 60
3.0, 48, 75
...
```

## 状态管理（Pinia）

所有计算中间值（wb、mg、ms、mb、mw、ma 等）统一存储在 `src/stores/calcStore.ts`，
各计算步骤自动从 Store 中读取前序结果，无需手动传递。
