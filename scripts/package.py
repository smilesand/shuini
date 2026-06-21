from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / 'backend'
FRONTEND_DIR = ROOT_DIR / 'frontend'
DESKTOP_DIR = ROOT_DIR / 'desktop'
RELEASE_DIR = ROOT_DIR / 'release'

HIDDEN_IMPORTS = [
    'uvicorn.logging',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan.on',
    'scipy.special._ufuncs',
    'scipy.special._ufuncs_cxx',
    'scipy.linalg._fblas',
    'scipy.linalg._flapack',
    'scipy.sparse._csparsetools',
    'scipy.optimize._minpack',
]

DATA_DIRS = [
    ('models', 'models'),
    ('routers', 'routers'),
    ('services', 'services'),
    ('core', 'core'),
    ('repositories', 'repositories'),
]


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    pretty = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
    print(f'\n>>> {pretty}')
    subprocess.run(command, cwd=cwd, check=True, env=env)


def npm_command() -> str:
    return 'npm.cmd' if os.name == 'nt' else 'npm'


def current_platform_name() -> str:
    if sys.platform.startswith('win'):
        return 'windows'
    if sys.platform.startswith('linux'):
        return 'debian'
    raise SystemExit('Only Windows and Debian/Linux hosts are supported for packaging.')


def ensure_python_build_dependencies() -> None:
    required_modules = ['fastapi', 'numpy', 'scipy', 'PyInstaller']
    missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
    if not missing:
        return

    print(f'Missing Python build dependencies: {", ".join(missing)}')
    run(
        [
            sys.executable,
            '-m',
            'pip',
            'install',
            '-r',
            str(BACKEND_DIR / 'requirements.txt'),
            '-r',
            str(BACKEND_DIR / 'requirements-dev.txt'),
        ]
    )


def ensure_node_dependencies(package_dir: Path) -> None:
    node_modules = package_dir / 'node_modules'
    if node_modules.exists():
        return

    run([npm_command(), 'install'], cwd=package_dir)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def pyinstaller_data_arg(source: Path, destination: str) -> str:
    separator = ';' if os.name == 'nt' else ':'
    return f'{source}{separator}{destination}'


def frontend_build_script(variant: str) -> str:
    if variant == 'desktop':
        return 'build:desktop'
    if variant == 'web':
        return 'build:web'
    raise ValueError(f'Unsupported frontend variant: {variant}')


def build_frontend(variant: str) -> Path:
    ensure_node_dependencies(FRONTEND_DIR)
    run([npm_command(), 'run', frontend_build_script(variant)], cwd=FRONTEND_DIR)

    dist_dir = FRONTEND_DIR / 'dist'
    if not dist_dir.exists():
        raise RuntimeError(f'Frontend build output not found: {dist_dir}')
    return dist_dir


def build_backend_binary(platform_name: str) -> Path:
    ensure_python_build_dependencies()

    dist_dir = RELEASE_DIR / '.backend-dist' / platform_name
    work_dir = RELEASE_DIR / '.backend-work' / platform_name
    spec_dir = RELEASE_DIR / '.backend-spec' / platform_name
    binary_name = 'wtcmd-platform-backend.exe' if platform_name == 'windows' else 'wtcmd-platform-backend'

    ensure_clean_dir(dist_dir)
    ensure_clean_dir(work_dir)
    ensure_clean_dir(spec_dir)

    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onefile',
        '--name',
        'wtcmd-platform-backend',
        '--distpath',
        str(dist_dir),
        '--workpath',
        str(work_dir),
        '--specpath',
        str(spec_dir),
    ]

    for source, destination in DATA_DIRS:
        command.extend(['--add-data', pyinstaller_data_arg(BACKEND_DIR / source, destination)])

    # 授权公钥以内嵌混淆模块 core/_license_pubkey.py 编译进后端内部，无需再夹带明文公钥文件。
    pubkey_module = BACKEND_DIR / 'core' / '_license_pubkey.py'
    if not pubkey_module.is_file():
        raise RuntimeError(
            f'Embedded license public-key module not found: {pubkey_module}. '
            f'Run "python scripts/init_license_keys.py" first.'
        )
    command.extend(['--hidden-import', 'core._license_pubkey'])

    # 数据库整库加密主密钥以内嵌混淆模块 core/_db_secret.py 编译进后端内部。
    db_secret_module = BACKEND_DIR / 'core' / '_db_secret.py'
    if not db_secret_module.is_file():
        raise RuntimeError(
            f'Embedded database-key module not found: {db_secret_module}. '
            f'Run "python scripts/init_license_keys.py" first.'
        )
    command.extend(['--hidden-import', 'core._db_secret'])
    command.extend(['--hidden-import', 'core.secure_db'])
    # AES-GCM 整库加解密依赖 cryptography 的 C 后端子模块，确保全部打包。
    command.extend(['--collect-submodules', 'cryptography'])

    for hidden_import in HIDDEN_IMPORTS:
        command.extend(['--hidden-import', hidden_import])

    command.append('main.py')
    run(command, cwd=BACKEND_DIR)

    binary_path = dist_dir / binary_name
    if not binary_path.exists():
        raise RuntimeError(f'Backend binary not found after build: {binary_path}')
    return binary_path


def build_license_admin_binary(platform_name: str) -> Path:
    """编译管理员授权客户端（license_admin/app.py）为独立可执行文件。

    ⚠️ 签发工具内嵌混淆私钥（编译进 exe 内部），仅限授权方内部使用，切勿分发给客户。
    """
    ensure_python_build_dependencies()

    tool_path = ROOT_DIR / 'release' / 'license-tool' / 'wtcmd-license-tool.py'
    if not tool_path.is_file():
        raise RuntimeError(
            f'License signing tool not found: {tool_path}. '
            'Run "python scripts/init_license_keys.py" first to generate the embedded-key tool.'
        )

    app_entry = ROOT_DIR / 'license_admin' / 'app.py'
    dist_dir = RELEASE_DIR / 'license-admin' / platform_name
    work_dir = RELEASE_DIR / '.admin-work' / platform_name
    spec_dir = RELEASE_DIR / '.admin-spec' / platform_name
    binary_name = 'wtcmd-license-admin.exe' if platform_name == 'windows' else 'wtcmd-license-admin'

    ensure_clean_dir(dist_dir)
    ensure_clean_dir(work_dir)
    ensure_clean_dir(spec_dir)

    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onefile',
        '--windowed',
        '--name',
        'wtcmd-license-admin',
        '--distpath',
        str(dist_dir),
        '--workpath',
        str(work_dir),
        '--specpath',
        str(spec_dir),
        # 签发工具以数据文件方式打包，运行时由 app.py 动态 import；PyInstaller 静态分析
        # 看不到工具内部对 cryptography 子模块（serialization 等）的依赖，必须显式收集，
        # 否则点击“签发授权码”会报 No module named 'cryptography.hazmat.primitives.serialization'。
        '--collect-submodules',
        'cryptography',
        # 捆绑内嵌混淆私钥的签发工具：运行时 app.py 从 _MEIPASS/license-tool 加载并解码。
        '--add-data',
        pyinstaller_data_arg(tool_path, 'license-tool'),
        str(app_entry),
    ]
    run(command, cwd=ROOT_DIR)

    binary_path = dist_dir / binary_name
    if not binary_path.exists():
        raise RuntimeError(f'License admin binary not found after build: {binary_path}')

    print('\n[!] wtcmd-license-admin 内嵌授权私钥，仅限授权方内部使用，切勿分发给客户。')
    return binary_path


def build_dev_tools(platform_name: str) -> Path:
    """编译开发者/运维工具（数据库解密加密工具 + 试用期修改工具）为独立 exe。

    两个工具都需要数据库主密钥 ``scripts/keys/db_key.bin``。这里把它以数据文件方式
    内嵌进每个 exe，运行时由 ``decrypt_db.load_db_key()`` 从 ``sys._MEIPASS`` 读取，
    因此客户拿到 exe 后无需任何额外密钥文件即可解密/查看自己的数据库与验证过期逻辑。

    ⚠️ 这两个工具内嵌数据库主密钥，可解密所有客户端数据库，请按内部工具管理；
       只在确需让客户自助验证数据/过期时再分发。
    """
    ensure_python_build_dependencies()

    scripts_dir = ROOT_DIR / 'scripts'
    db_key = scripts_dir / 'keys' / 'db_key.bin'
    if not db_key.is_file():
        raise RuntimeError(
            f'Database master key not found: {db_key}. '
            'Run "python scripts/init_license_keys.py" first to generate it.'
        )

    dist_dir = RELEASE_DIR / 'dev-tools' / platform_name
    work_dir = RELEASE_DIR / '.tools-work' / platform_name
    spec_dir = RELEASE_DIR / '.tools-spec' / platform_name
    ensure_clean_dir(dist_dir)
    ensure_clean_dir(work_dir)
    ensure_clean_dir(spec_dir)

    tools = [
        ('wtcmd-db-tool', scripts_dir / 'decrypt_db.py'),
        ('wtcmd-expire-tool', scripts_dir / 'expire_trial.py'),
    ]
    exe_suffix = '.exe' if platform_name == 'windows' else ''

    for name, entry in tools:
        if not entry.is_file():
            raise RuntimeError(f'Dev tool entry not found: {entry}')
        command = [
            sys.executable,
            '-m',
            'PyInstaller',
            '--noconfirm',
            '--clean',
            '--onefile',
            '--console',
            '--name',
            name,
            '--distpath',
            str(dist_dir),
            '--workpath',
            str(work_dir),
            '--specpath',
            str(spec_dir),
            # 把工具脚本所在目录加入搜索路径：expire_trial 运行时 import decrypt_db。
            '--paths',
            str(scripts_dir),
            # 主密钥以数据文件内嵌进 exe；运行时从 _MEIPASS 读取。
            '--add-data',
            pyinstaller_data_arg(db_key, '.'),
            # AES-GCM 解密依赖 cryptography 的 C 后端子模块。
            '--collect-submodules',
            'cryptography',
            '--hidden-import',
            'decrypt_db',
            str(entry),
        ]
        run(command, cwd=scripts_dir)
        binary_path = dist_dir / f'{name}{exe_suffix}'
        if not binary_path.exists():
            raise RuntimeError(f'Dev tool binary not found after build: {binary_path}')

    write_dev_tools_readme(dist_dir, platform_name)
    print('\n[!] dev-tools 内嵌数据库主密钥，可解密所有客户端数据库，请作为内部工具妥善保管。')
    return dist_dir


def write_dev_tools_readme(target_dir: Path, platform_name: str) -> None:
    db_tool = 'wtcmd-db-tool.exe' if platform_name == 'windows' else './wtcmd-db-tool'
    expire_tool = 'wtcmd-expire-tool.exe' if platform_name == 'windows' else './wtcmd-expire-tool'
    readme = target_dir / 'README.txt'
    readme.write_text(
        "WTCMD 平台 开发者/运维工具\n"
        "============================\n\n"
        "本目录包含两个独立可执行工具，已内嵌数据库主密钥，无需任何额外密钥文件。\n"
        "客户端数据库 data.db 在磁盘上是整库 AES-256-GCM 加密的，普通工具无法直接打开；\n"
        "用下列工具可以解密查看、修改后再加密写回，或验证试用期/过期逻辑。\n\n"
        "桌面版数据库默认位置（Windows）：\n"
        "  %APPDATA%\\WTCMD Platform\\data.db\n\n"
        "1) 数据库解密/加密/查看工具：" + db_tool + "\n"
        "  - 解密为明文 sqlite（可用 DBeaver/sqlite3 打开）：\n"
        "      " + db_tool + " decrypt --in \"<data.db>\" --out plain.db\n"
        "  - 改完明文库后加密写回：\n"
        "      " + db_tool + " encrypt --in plain.db --out \"<data.db>\"\n"
        "  - 直接查看授权状态（含防篡改校验）：\n"
        "      " + db_tool + " show --in \"<data.db>\"\n\n"
        "2) 试用期修改工具（验证到期行为）：" + expire_tool + "\n"
        "  - 让试用期立刻过期：\n"
        "      " + expire_tool + "\n"
        "  - 指定还剩 1 天（first_seen 设为 2 天前）：\n"
        "      " + expire_tool + " --days-ago 2\n"
        "  - 清除已激活授权码回到试用状态：\n"
        "      " + expire_tool + " --clear-activation\n"
        "  - 指定数据库路径：\n"
        "      " + expire_tool + " --db \"<data.db>\"\n\n"
        "注意：修改前请先关闭桌面客户端，避免运行中的程序再次落盘覆盖你的改动。\n"
        "安全提示：这两个工具内嵌主密钥，可解密任意客户端数据库，请妥善保管。\n",
        encoding='utf-8',
    )


def write_web_start_script(target_dir: Path, platform_name: str, backend_binary: Path) -> None:
    if platform_name == 'windows':
        script_path = target_dir / 'start-web.ps1'
        script_path.write_text(
            "$ErrorActionPreference = 'Stop'\n"
            "$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path\n"
            "$DataDir = Join-Path $ScriptDir 'data'\n"
            "if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }\n"
            "if (-not $env:SC_HOST) { $env:SC_HOST = '0.0.0.0' }\n"
            "if (-not $env:SC_PORT) { $env:SC_PORT = '8000' }\n"
            "$env:SC_FRONTEND_DIST = Join-Path $ScriptDir 'frontend'\n"
            "$env:SC_DB_PATH = Join-Path $DataDir 'data.db'\n"
            f"& (Join-Path $ScriptDir '{backend_binary.name}')\n",
            encoding='utf-8',
        )
        return

    script_path = target_dir / 'start-web.sh'
    script_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
        "mkdir -p \"${SCRIPT_DIR}/data\"\n"
        "export SC_HOST=\"${SC_HOST:-0.0.0.0}\"\n"
        "export SC_PORT=\"${SC_PORT:-8000}\"\n"
        "export SC_FRONTEND_DIST=\"${SCRIPT_DIR}/frontend\"\n"
        "export SC_DB_PATH=\"${SCRIPT_DIR}/data/data.db\"\n"
        f"exec \"${{SCRIPT_DIR}}/{backend_binary.name}\"\n",
        encoding='utf-8',
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)


def write_web_readme(target_dir: Path, platform_name: str) -> None:
    launch_hint = 'start-web.ps1' if platform_name == 'windows' else './start-web.sh'
    readme = target_dir / 'README.txt'
    readme.write_text(
        "WTCMD Platform Web Bundle\n"
        "=========================\n\n"
        "This bundle contains a single backend executable plus the built frontend dist.\n"
        "The backend serves both the API and the frontend static files on the same port.\n\n"
        "Usage\n"
        "-----\n"
        f"1. Start the service with: {launch_hint}\n"
        "2. Open http://127.0.0.1:8000 in a browser.\n\n"
        "You can override the default host/port before launch with SC_HOST and SC_PORT.\n\n"
        "Data\n"
        "----\n"
        "The SQLite database is created in the local data/ directory next to the launcher script.\n",
        encoding='utf-8',
    )


def build_web_bundle(platform_name: str, frontend_dist: Path, backend_binary: Path) -> Path:
    target_dir = RELEASE_DIR / 'web' / platform_name
    ensure_clean_dir(target_dir)

    # Web 形态默认 SC_EDITION=web，后端始终放行（不强制激活/试用），数据库也不加密，
    # 因此 Web 包无需分发授权公钥，避免夹带授权相关产物。
    shutil.copy2(backend_binary, target_dir / backend_binary.name)
    shutil.copytree(frontend_dist, target_dir / 'frontend')
    (target_dir / 'data').mkdir(parents=True, exist_ok=True)
    write_web_start_script(target_dir, platform_name, backend_binary)
    write_web_readme(target_dir, platform_name)
    return target_dir


def stage_desktop_resources(frontend_dist: Path, backend_binary: Path) -> None:
    resources_dir = DESKTOP_DIR / 'resources'
    backend_target = resources_dir / 'backend'
    frontend_target = resources_dir / 'frontend-dist'

    ensure_clean_dir(resources_dir)
    backend_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backend_binary, backend_target / backend_binary.name)
    shutil.copytree(frontend_dist, frontend_target)


WINCODESIGN_VERSION = '2.6.0'
WINCODESIGN_URL = (
    'https://github.com/electron-userland/electron-builder-binaries/releases/'
    f'download/winCodeSign-{WINCODESIGN_VERSION}/winCodeSign-{WINCODESIGN_VERSION}.7z'
)


def ensure_wincodesign_cache() -> None:
    """预解压 electron-builder 的 winCodeSign 缓存（排除 darwin 符号链接）。

    Windows 普通用户无权创建符号链接，electron-builder 解压 winCodeSign 时
    会因 darwin/*.dylib 符号链接失败而中断。这里提前用 7za 解压并排除 darwin
    目录，使 electron-builder 检测到缓存已就绪而跳过自身的解压步骤。
    """
    if os.name != 'nt':
        return

    local_appdata = os.getenv('LOCALAPPDATA')
    if not local_appdata:
        return

    cache_dir = Path(local_appdata) / 'electron-builder' / 'Cache' / 'winCodeSign'
    final_dir = cache_dir / f'winCodeSign-{WINCODESIGN_VERSION}'
    if (final_dir / 'windows-10').exists():
        return

    seven_zip = DESKTOP_DIR / 'node_modules' / '7zip-bin' / 'win' / 'x64' / '7za.exe'
    if not seven_zip.exists():
        return

    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = next((p for p in cache_dir.glob('*.7z')), None)
    if archive is None:
        archive = cache_dir / f'winCodeSign-{WINCODESIGN_VERSION}.7z'
        print(f'Downloading winCodeSign archive -> {archive}')
        import urllib.request

        urllib.request.urlretrieve(WINCODESIGN_URL, archive)

    if final_dir.exists():
        shutil.rmtree(final_dir)

    print(f'Pre-extracting winCodeSign cache (excluding darwin) -> {final_dir}')
    subprocess.run(
        [str(seven_zip), 'x', str(archive), f'-o{final_dir}', '-x!darwin', '-y'],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def build_desktop_bundle(platform_name: str) -> Path:
    ensure_node_dependencies(DESKTOP_DIR)

    if platform_name == 'windows':
        ensure_wincodesign_cache()

    output_dir = RELEASE_DIR / 'desktop' / platform_name
    if output_dir.exists():
        shutil.rmtree(output_dir)

    command = [
        npm_command(),
        'exec',
        'electron-builder',
        '--',
        '--x64',
        f'-c.directories.output=../release/desktop/{platform_name}',
    ]
    if platform_name == 'windows':
        command.extend(['--win', 'nsis'])
    else:
        command.extend(['--linux', 'AppImage', 'deb'])

    env = os.environ.copy()
    env['CSC_IDENTITY_AUTO_DISCOVERY'] = 'false'
    run(command, cwd=DESKTOP_DIR, env=env)
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build web and desktop packages from one codebase.')
    parser.add_argument('--variant', choices=['web', 'desktop', 'admin', 'tools', 'all'], default='all')
    parser.add_argument('--platform', choices=['windows', 'debian'], default=current_platform_name())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host_platform = current_platform_name()
    if args.platform != host_platform:
        raise SystemExit(
            f'Cross-platform packaging is not supported. Run this on a {args.platform} host instead.'
        )

    built_paths: list[Path] = []
    backend_binary: Path | None = None

    if args.variant in {'web', 'desktop', 'all'}:
        backend_binary = build_backend_binary(args.platform)

    if args.variant in {'web', 'all'}:
        assert backend_binary is not None
        frontend_dist = build_frontend('web')
        built_paths.append(build_web_bundle(args.platform, frontend_dist, backend_binary))

    if args.variant in {'desktop', 'all'}:
        assert backend_binary is not None
        frontend_dist = build_frontend('desktop')
        stage_desktop_resources(frontend_dist, backend_binary)
        built_paths.append(build_desktop_bundle(args.platform))

    if args.variant in {'admin', 'all'}:
        built_paths.append(build_license_admin_binary(args.platform))

    if args.variant in {'tools', 'all'}:
        built_paths.append(build_dev_tools(args.platform))

    print('\nBuild complete.')
    for path in built_paths:
        print(f' - {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())