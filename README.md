# 混凝土配合比设计系统

一套面向高性能混凝土（HPC）与超高性能混凝土（UHPC）的配合比设计、试配调整与配比记录管理系统，采用前后端分离架构，可部署为 Web 服务或打包为桌面应用。

## 功能简介

- **配比计算**：按抗压强度等级、原材料性能等参数，计算 HPC / UHPC 的水胶比、砂率（砂胶比）、各胶凝材料占比及每方用量。
- **试配调整**：三点强度试验 + 最小二乘线性回归，推荐最优水胶比与硅灰用量；支持工作性试拌、密度校正与实验室配合比确定。
- **性能评价**：对坍落度 / 扩展度、28d 抗压强度、抗拉强度等指标自动判定合格与否。
- **项目与记录管理**：按项目组织配比记录，支持历史检索、载入与回收站恢复。
- **导入导出**：Excel 模板导入（含关键参数合理性校验）、单条记录与整项目导出，以及 PDF 配比记录报告导出。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus |
| 后端 | Python + FastAPI + openpyxl |
| 桌面 | Electron（复用同一套前后端） |

浏览器端通过 `frontend/src/utils/request.ts` 中的 Axios 实例访问后端 `/api/*` 接口。开发模式由 Vite 代理到本地后端；打包后的 Web 包与桌面版均由后端直接托管 `frontend/dist`。

## 项目结构

```
shuini_calculator/
├── frontend/          # Vue 3 前端
├── backend/           # FastAPI 后端与配比计算逻辑
├── desktop/           # Electron 桌面外壳
├── scripts/           # 打包脚本（package.py 等）
├── license_admin/     # 授权管理辅助工具
├── package-*.ps1/.sh  # 一键打包包装脚本
└── package-source.ps1 # 源代码交付打包脚本
```

## 环境要求

- Node.js ≥ 18（建议 LTS）
- Python ≥ 3.11
- npm ≥ 9

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

前端地址：http://localhost:5173（接口默认代理到后端 8000 端口）

## 构建

### 前端

```bash
cd frontend
npm run build          # 通用构建
npm run build:web      # Web 部署（读取 .env.production）
npm run build:desktop  # 桌面版（读取 .env.desktop）
npm run typecheck      # 类型检查
```

### 后端

后端使用 PyInstaller 打包为独立可执行文件，脚本位于 `backend/build.ps1`（Windows）/ `backend/build.sh`（Linux，基于 Docker）。

## 一键打包

在对应平台上执行（桌面版需在目标平台原生打包，不支持跨平台交叉编译）：

### Windows

```powershell
.\package-web.ps1        # Web 版
.\package-desktop.ps1    # 桌面版
.\package-all.ps1        # 两者
```

### Debian / Linux

```bash
bash ./package-web.sh
bash ./package-desktop.sh
bash ./package-all.sh
```

产物输出到 `release/` 目录。Web 包启动后默认监听 `http://127.0.0.1:8000`。

## 部署提示（Nginx）

前端使用 Vue Router 的 history 模式（`createWebHistory()`），需将未匹配的前端路由回退到 `index.html`，并把 `/api/` 反向代理到后端，否则刷新 `/projects`、`/calc/hpc` 等地址会返回 404：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
```

可参考 [frontend/nginx.conf.example](frontend/nginx.conf.example)。

## 源代码交付打包

如需将源代码打包交付（自动排除文档、依赖、编译缓存、构建产物及密钥等敏感文件，由收到方自行安装依赖），在 Windows 上执行：

```powershell
.\package-source.ps1
```

生成的 zip 位于 `code-package/` 目录。收到方解压后，按上文「快速启动」安装依赖即可运行。

