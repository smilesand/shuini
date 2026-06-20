"""
单机版授权管理系统（带 UI）
==========================
需求 #10：使用加密 SQLite 管理所有被授权设备的信息（设备码、使用人、授权日期、
过期时间等），并可直接为设备签发授权码。

特性：
  * Tkinter 图形界面，零额外 UI 依赖。
  * 设备库使用 **AES-256-GCM 全文件加密**（口令派生密钥，PBKDF2-SHA256）。
    打开时输入主口令解密到临时明文库，任何变更后立即重新加密落盘。
  * 复用现有签发工具 (release/license-tool/wtcmd-license-tool.py) 的 RSA 私钥，
    为设备指纹签发授权码 —— 与后端校验所用公钥严格匹配。

运行::

    python license_admin/app.py
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _data_dir() -> Path:
    """设备库存放目录：打包后为 exe 同级目录（持久化），源码运行时为脚本目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _tool_path() -> Path:
    """签发工具路径：打包后从 _MEIPASS 内的捆绑资源读取，源码运行时取 release/。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "license-tool" / "wtcmd-license-tool.py"
    return Path(__file__).resolve().parents[1] / "release" / "license-tool" / "wtcmd-license-tool.py"


DATA_DIR = _data_dir()
ENC_DB_PATH = DATA_DIR / "devices.db.enc"
SALT_PATH = DATA_DIR / ".salt"
TOOL_PATH = _tool_path()

PBKDF2_ITERATIONS = 200_000


# ──────────────────────────────────────────────────────────────────────────
# 加密存储
# ──────────────────────────────────────────────────────────────────────────
def _load_or_create_salt() -> bytes:
    if SALT_PATH.exists():
        return SALT_PATH.read_bytes()
    salt = os.urandom(16)
    SALT_PATH.write_bytes(salt)
    return salt


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


class EncryptedDeviceStore:
    """AES-GCM 全文件加密的 SQLite 设备库。"""

    def __init__(self, key: bytes):
        self._key = key
        self._aes = AESGCM(key)
        # 临时明文库
        fd, self._plain_path = tempfile.mkstemp(suffix=".db", prefix="licadmin_")
        os.close(fd)
        self._decrypt_to_plain()
        self._conn = sqlite3.connect(self._plain_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # -- 加解密 --
    def _decrypt_to_plain(self) -> None:
        if not ENC_DB_PATH.exists():
            # 全新库：留空明文文件，由 sqlite 初始化。
            Path(self._plain_path).write_bytes(b"")
            return
        blob = ENC_DB_PATH.read_bytes()
        nonce, ciphertext = blob[:12], blob[12:]
        try:
            plain = self._aes.decrypt(nonce, ciphertext, None)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("主口令错误或设备库已损坏") from exc
        Path(self._plain_path).write_bytes(plain)

    def _flush(self) -> None:
        self._conn.commit()
        plain = Path(self._plain_path).read_bytes()
        nonce = os.urandom(12)
        ciphertext = self._aes.encrypt(nonce, plain, None)
        ENC_DB_PATH.write_bytes(nonce + ciphertext)

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint  TEXT    NOT NULL UNIQUE,
                username     TEXT    NOT NULL DEFAULT '',
                note         TEXT    NOT NULL DEFAULT '',
                issued_at    TEXT,
                expiry       TEXT,
                license_code TEXT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                contact     TEXT    NOT NULL DEFAULT '',
                company     TEXT    NOT NULL DEFAULT '',
                note        TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            );
            """
        )
        self._flush()

    # -- CRUD：设备 --
    def list_devices(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM devices ORDER BY created_at DESC, id DESC"
        ).fetchall()

    def upsert_device(self, fingerprint: str, username: str, note: str) -> None:
        self._conn.execute(
            "INSERT INTO devices (fingerprint, username, note) VALUES (?,?,?) "
            "ON CONFLICT(fingerprint) DO UPDATE SET username=excluded.username, note=excluded.note",
            (fingerprint.strip().upper(), username.strip(), note.strip()),
        )
        # 登记设备使用人时，自动收录为已授权用户（不覆盖已有资料）。
        self._ensure_user(username)
        self._flush()

    def set_license(self, fingerprint: str, issued_at: str, expiry: str, code: str) -> None:
        self._conn.execute(
            "UPDATE devices SET issued_at=?, expiry=?, license_code=? WHERE fingerprint=?",
            (issued_at, expiry, code, fingerprint.strip().upper()),
        )
        self._flush()

    def delete_device(self, fingerprint: str) -> None:
        self._conn.execute("DELETE FROM devices WHERE fingerprint=?", (fingerprint.strip().upper(),))
        self._flush()

    # -- CRUD：用户 --
    def list_users(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT u.*, "
            "(SELECT COUNT(*) FROM devices d WHERE d.username = u.name) AS device_count "
            "FROM users u ORDER BY u.created_at DESC, u.id DESC"
        ).fetchall()

    def upsert_user(self, name: str, contact: str, company: str, note: str) -> None:
        self._conn.execute(
            "INSERT INTO users (name, contact, company, note) VALUES (?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET contact=excluded.contact, "
            "company=excluded.company, note=excluded.note",
            (name.strip(), contact.strip(), company.strip(), note.strip()),
        )
        self._flush()

    def delete_user(self, name: str) -> None:
        self._conn.execute("DELETE FROM users WHERE name=?", (name.strip(),))
        self._flush()

    def _ensure_user(self, name: str) -> None:
        """若使用人非空且尚未登记，则插入一条最简用户记录（不提交，由调用方 flush）。"""
        if name and name.strip():
            self._conn.execute(
                "INSERT OR IGNORE INTO users (name) VALUES (?)", (name.strip(),)
            )

    def close(self) -> None:
        try:
            self._conn.close()
        finally:
            try:
                os.remove(self._plain_path)
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────────────────
# 授权码签发（复用现有 RSA 私钥）
# ──────────────────────────────────────────────────────────────────────────
def _load_signing_tool():
    if not TOOL_PATH.is_file():
        raise FileNotFoundError(f"未找到签发工具: {TOOL_PATH}")
    spec = importlib.util.spec_from_file_location("wtcmd_license_tool", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载签发工具模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def issue_license(fingerprint: str, days: int) -> tuple[str, str]:
    """返回 (授权码, 到期日期 YYYY-MM-DD)。"""
    tool = _load_signing_tool()
    private_key = tool._load_private_key()  # noqa: SLF001
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    payload = tool._make_license_payload(fingerprint.strip().upper(), expiry)  # noqa: SLF001
    code = tool._sign_payload(payload, private_key)  # noqa: SLF001
    return code, expiry


# ──────────────────────────────────────────────────────────────────────────
# 图形界面
# ──────────────────────────────────────────────────────────────────────────
class AdminApp(tk.Tk):
    def __init__(self, store: EncryptedDeviceStore):
        super().__init__()
        self.store = store
        self.title("WTCMD 授权管理系统")
        self.geometry("960x560")
        self.minsize(820, 480)
        self._build_ui()
        self.refresh()
        self.refresh_users()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        device_tab = ttk.Frame(notebook)
        user_tab = ttk.Frame(notebook)
        notebook.add(device_tab, text="设备授权")
        notebook.add(user_tab, text="用户管理")

        self._build_device_tab(device_tab)
        self._build_user_tab(user_tab)

    def _build_device_tab(self, parent: ttk.Frame) -> None:
        # 顶部表单
        form = ttk.LabelFrame(parent, text="设备登记 / 签发")
        form.pack(fill="x", padx=12, pady=10)

        ttk.Label(form, text="设备指纹").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.fp_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.fp_var, width=70).grid(
            row=0, column=1, columnspan=3, sticky="we", padx=6, pady=6
        )

        ttk.Label(form, text="使用人").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.user_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.user_var, width=24).grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(form, text="有效天数").grid(row=1, column=2, sticky="w", padx=6)
        self.days_var = tk.StringVar(value="365")
        ttk.Entry(form, textvariable=self.days_var, width=10).grid(row=1, column=3, sticky="w", padx=6)

        ttk.Label(form, text="备注").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self.note_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.note_var, width=70).grid(
            row=2, column=1, columnspan=3, sticky="we", padx=6, pady=6
        )

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=4, sticky="w", padx=4, pady=6)
        ttk.Button(btns, text="保存设备", command=self.on_save).pack(side="left", padx=4)
        ttk.Button(btns, text="签发授权码", command=self.on_issue).pack(side="left", padx=4)
        ttk.Button(btns, text="复制授权码", command=self.on_copy_code).pack(side="left", padx=4)
        ttk.Button(btns, text="删除设备", command=self.on_delete).pack(side="left", padx=4)
        ttk.Button(btns, text="刷新", command=self.refresh).pack(side="left", padx=4)

        form.columnconfigure(1, weight=1)

        # 设备列表
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        columns = ("fingerprint", "username", "issued_at", "expiry", "note")
        headers = {
            "fingerprint": "设备指纹",
            "username": "使用人",
            "issued_at": "签发日期",
            "expiry": "到期日期",
            "note": "备注",
        }
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=160 if col == "fingerprint" else 110, anchor="w")
        self.tree.column("fingerprint", width=320)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # 授权码显示
        code_frame = ttk.LabelFrame(parent, text="授权码")
        code_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.code_text = tk.Text(code_frame, height=3, wrap="char")
        self.code_text.pack(fill="x", padx=6, pady=6)

    def _build_user_tab(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="授权用户登记")
        form.pack(fill="x", padx=12, pady=10)

        ttk.Label(form, text="姓名").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.u_name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.u_name_var, width=24).grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(form, text="联系方式").grid(row=0, column=2, sticky="w", padx=6)
        self.u_contact_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.u_contact_var, width=24).grid(row=0, column=3, sticky="w", padx=6)

        ttk.Label(form, text="单位").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.u_company_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.u_company_var, width=24).grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(form, text="备注").grid(row=1, column=2, sticky="w", padx=6)
        self.u_note_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.u_note_var, width=24).grid(row=1, column=3, sticky="w", padx=6)

        ubtns = ttk.Frame(form)
        ubtns.grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=6)
        ttk.Button(ubtns, text="保存用户", command=self.on_user_save).pack(side="left", padx=4)
        ttk.Button(ubtns, text="删除用户", command=self.on_user_delete).pack(side="left", padx=4)
        ttk.Button(ubtns, text="刷新", command=self.refresh_users).pack(side="left", padx=4)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        columns = ("name", "contact", "company", "devices", "note", "created_at")
        headers = {
            "name": "姓名",
            "contact": "联系方式",
            "company": "单位",
            "devices": "已授权设备数",
            "note": "备注",
            "created_at": "登记时间",
        }
        widths = {
            "name": 120,
            "contact": 150,
            "company": 160,
            "devices": 100,
            "note": 140,
            "created_at": 150,
        }
        self.user_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.user_tree.heading(col, text=headers[col])
            anchor = "center" if col == "devices" else "w"
            self.user_tree.column(col, width=widths[col], anchor=anchor)
        self.user_tree.pack(side="left", fill="both", expand=True)
        uscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.user_tree.yview)
        uscroll.pack(side="right", fill="y")
        self.user_tree.configure(yscrollcommand=uscroll.set)
        self.user_tree.bind("<<TreeviewSelect>>", self.on_user_select)

    # -- 数据操作 --
    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.store.list_devices():
            self.tree.insert(
                "",
                "end",
                iid=row["fingerprint"],
                values=(
                    row["fingerprint"],
                    row["username"],
                    row["issued_at"] or "-",
                    row["expiry"] or "-",
                    row["note"],
                ),
            )

    def on_select(self, _event=None) -> None:
        fp = self._selected_fp()
        if not fp:
            return
        for row in self.store.list_devices():
            if row["fingerprint"] == fp:
                self.fp_var.set(row["fingerprint"])
                self.user_var.set(row["username"])
                self.note_var.set(row["note"])
                self._show_code(row["license_code"] or "")
                break

    def _selected_fp(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def on_save(self) -> None:
        fp = self.fp_var.get().strip()
        if len(fp) < 16:
            messagebox.showwarning("提示", "设备指纹至少 16 个字符")
            return
        self.store.upsert_device(fp, self.user_var.get(), self.note_var.get())
        self.refresh()
        self.refresh_users()
        messagebox.showinfo("成功", "设备已保存")

    def on_issue(self) -> None:
        fp = self.fp_var.get().strip()
        if len(fp) < 16:
            messagebox.showwarning("提示", "请先填写有效的设备指纹")
            return
        try:
            days = int(self.days_var.get().strip() or "365")
        except ValueError:
            messagebox.showwarning("提示", "有效天数必须为整数")
            return
        try:
            self.store.upsert_device(fp, self.user_var.get(), self.note_var.get())
            code, expiry = issue_license(fp, days)
            self.store.set_license(fp, datetime.now().strftime("%Y-%m-%d"), expiry, code)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("签发失败", str(exc))
            return
        self.refresh()
        self.refresh_users()
        self.tree.selection_set(fp.upper())
        self._show_code(code)
        messagebox.showinfo("签发成功", f"授权码已生成，到期日期 {expiry}")

    def on_copy_code(self) -> None:
        code = self.code_text.get("1.0", "end").strip()
        if not code:
            messagebox.showwarning("提示", "当前没有可复制的授权码")
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo("已复制", "授权码已复制到剪贴板")

    def on_delete(self) -> None:
        fp = self._selected_fp() or self.fp_var.get().strip()
        if not fp:
            messagebox.showwarning("提示", "请先选择要删除的设备")
            return
        if not messagebox.askyesno("确认", f"确定删除设备 {fp[:24]}... 吗？"):
            return
        self.store.delete_device(fp)
        self.refresh()
        self._show_code("")

    def _show_code(self, code: str) -> None:
        self.code_text.delete("1.0", "end")
        if code:
            self.code_text.insert("1.0", code)

    # -- 用户管理 --
    def refresh_users(self) -> None:
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        for row in self.store.list_users():
            self.user_tree.insert(
                "",
                "end",
                iid=row["name"],
                values=(
                    row["name"],
                    row["contact"],
                    row["company"],
                    row["device_count"],
                    row["note"],
                    row["created_at"],
                ),
            )

    def on_user_select(self, _event=None) -> None:
        sel = self.user_tree.selection()
        if not sel:
            return
        name = sel[0]
        for row in self.store.list_users():
            if row["name"] == name:
                self.u_name_var.set(row["name"])
                self.u_contact_var.set(row["contact"])
                self.u_company_var.set(row["company"])
                self.u_note_var.set(row["note"])
                break

    def on_user_save(self) -> None:
        name = self.u_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请填写用户姓名")
            return
        self.store.upsert_user(
            name,
            self.u_contact_var.get(),
            self.u_company_var.get(),
            self.u_note_var.get(),
        )
        self.refresh_users()
        messagebox.showinfo("成功", "用户信息已保存")

    def on_user_delete(self) -> None:
        sel = self.user_tree.selection()
        name = sel[0] if sel else self.u_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请先选择要删除的用户")
            return
        if not messagebox.askyesno("确认", f"确定删除用户「{name}」吗？\n（不会删除其已签发的设备授权）"):
            return
        self.store.delete_user(name)
        self.refresh_users()

    def _on_close(self) -> None:
        self.store.close()
        self.destroy()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    salt = _load_or_create_salt()
    first_run = not ENC_DB_PATH.exists()
    prompt = "设置主口令（用于加密设备库）" if first_run else "请输入主口令"
    password = simpledialog.askstring("授权管理系统", prompt, show="*", parent=root)
    if not password:
        root.destroy()
        return
    try:
        store = EncryptedDeviceStore(_derive_key(password, salt))
    except ValueError as exc:
        messagebox.showerror("打开失败", str(exc), parent=root)
        root.destroy()
        return
    root.destroy()

    app = AdminApp(store)
    app.mainloop()


if __name__ == "__main__":
    main()
