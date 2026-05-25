"""登录、管理员、邀请码：config/auth_store.json。"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

log = logging.getLogger("custom_project.auth")

STORE_FILE = PROJECT_ROOT / "config" / "auth_store.json"
LEGACY_CODES_FILE = PROJECT_ROOT / "config" / "auth_codes.json"
_PASSWORD_PEPPER = "comfy_console"
DEFAULT_SINGLE_QUOTA_PER_LOGIN = 5
_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _hash_password(password: str) -> str:
    raw = f"{_PASSWORD_PEPPER}:{password or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    import secrets as sec

    return sec.compare_digest(_hash_password(password), (password_hash or "").strip())


def _empty_store() -> dict:
    return {"admins": [], "invites": []}


def _migrate_legacy(data: dict) -> dict:
    """从 auth_codes.json 的 codes 迁移到 invites。"""
    if not LEGACY_CODES_FILE.is_file():
        return data
    try:
        legacy = json.loads(LEGACY_CODES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return data
    if data.get("invites"):
        return data
    invites = []
    for item in legacy.get("codes") or []:
        used = bool(item.get("used"))
        invites.append({
            "id": str(item.get("id") or uuid.uuid4().hex[:8]),
            "code": item.get("code", ""),
            "note": item.get("note", ""),
            "expires_at": item.get("expires_at"),
            "max_uses": int(item.get("max_uses") or 1),
            "single_quota_per_login": _invite_single_quota_per_login(item),
            "used_count": int(item.get("used_count") or (1 if used else 0)),
            "enabled": item.get("enabled", True) is not False,
            "created_at": item.get("created_at") or _now_iso(),
            "last_used_at": item.get("used_at"),
        })
    data["invites"] = invites
    return data


def _load_store() -> dict:
    if not STORE_FILE.is_file():
        data = _empty_store()
        return _migrate_legacy(data)
    raw = STORE_FILE.read_text(encoding="utf-8")
    data = json.loads(raw) if raw.strip() else _empty_store()
    if not isinstance(data.get("admins"), list):
        data["admins"] = []
    if not isinstance(data.get("invites"), list):
        data["invites"] = []
    return _migrate_legacy(data)


def _save_store(data: dict) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _normalize_code(code: str) -> str:
    return (code or "").strip().upper()


def _find_invite(data: dict, code: str) -> dict | None:
    norm = _normalize_code(code)
    for item in data.get("invites") or []:
        if _normalize_code(item.get("code", "")) == norm:
            return item
    return None


def _invite_max_uses(entry: dict) -> int:
    """1=单次；0 或负数=不限次数；N=最多 N 次。"""
    try:
        return int(entry.get("max_uses", 1))
    except (TypeError, ValueError):
        return 1


def _invite_single_quota_per_login(entry: dict) -> int:
    try:
        return max(0, int(entry.get("single_quota_per_login", DEFAULT_SINGLE_QUOTA_PER_LOGIN)))
    except (TypeError, ValueError):
        return DEFAULT_SINGLE_QUOTA_PER_LOGIN


def _invite_remaining(entry: dict) -> int | None:
    max_u = _invite_max_uses(entry)
    if max_u <= 0:
        return None
    used = int(entry.get("used_count") or 0)
    return max(0, max_u - used)


def _validate_invite_entry(entry: dict) -> str | None:
    if entry.get("enabled") is False:
        return "邀请码已禁用"
    exp = _parse_iso(entry.get("expires_at"))
    if exp and _now() > exp:
        return "邀请码已过期"
    max_u = _invite_max_uses(entry)
    if max_u > 0 and int(entry.get("used_count") or 0) >= max_u:
        return "邀请码使用次数已用尽"
    return None


def _issue_token(role: str, extra: dict | None = None) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "role": role,
        "created_at": _now_iso(),
        **(extra or {}),
    }
    return token


def get_session(token: str | None) -> dict | None:
    if not token or not str(token).strip():
        return None
    return _sessions.get(str(token).strip())


def validate_session(token: str | None) -> bool:
    return get_session(token) is not None


def is_admin(token: str | None) -> bool:
    sess = get_session(token)
    return bool(sess and sess.get("role") == "admin")


def quota_info_for_session(token: str | None) -> dict[str, Any]:
    sess = get_session(token)
    if not sess:
        return {}
    if sess.get("role") == "admin":
        return {
            "allow_batch": True,
            "single_quota": None,
            "single_used": None,
            "single_remaining": None,
        }
    quota = max(0, int(sess.get("single_quota", 0)))
    used = max(0, int(sess.get("single_used", 0)))
    return {
        "allow_batch": False,
        "single_quota": quota,
        "single_used": used,
        "single_remaining": max(0, quota - used),
    }


def can_queue_single(token: str | None) -> tuple[bool, str | None]:
    sess = get_session(token)
    if not sess:
        return False, "未登录或会话已失效"
    if sess.get("role") == "admin":
        return True, None
    quota = max(0, int(sess.get("single_quota", 0)))
    used = max(0, int(sess.get("single_used", 0)))
    if used >= quota:
        return False, f"本次登录单图额度已用尽（{quota} 张），请重新登录或联系管理员"
    return True, None


def consume_single_quota(token: str | None) -> dict[str, Any] | None:
    if not token or is_admin(token):
        return None
    with _lock:
        sess = get_session(token)
        if not sess or sess.get("role") == "admin":
            return None
        sess["single_used"] = max(0, int(sess.get("single_used", 0))) + 1
        return quota_info_for_session(token)


def assert_batch_allowed(token: str | None) -> None:
    if is_admin(token):
        return
    sess = get_session(token)
    if sess and sess.get("role") == "user":
        raise PermissionError("邀请码用户仅可使用单张生成，无法使用批量生成或任务计划")


def assert_workflow_config_allowed(token: str | None) -> None:
    if is_admin(token):
        return
    sess = get_session(token)
    if sess and sess.get("role") == "user":
        raise PermissionError("邀请码用户无法查看或修改工作流配置")


def assert_lora_chain_edit_allowed(token: str | None) -> None:
    """生成页 / 运行时可调整 LoRA 链（邀请码用户可用，母版只读由业务层拦截）。"""
    if is_admin(token):
        return
    if get_session(token):
        return
    raise PermissionError("未登录或会话已失效")


def session_info(token: str | None) -> dict:
    sess = get_session(token)
    if not sess:
        return {"ok": False}
    return {
        "ok": True,
        "role": sess.get("role") or "user",
        "username": sess.get("username"),
        "invite_code": sess.get("invite_code"),
        **quota_info_for_session(token),
    }


def logout_session(token: str | None) -> None:
    if token:
        _sessions.pop(str(token).strip(), None)


def login_admin(username: str, password: str) -> dict:
    uname = (username or "").strip()
    if not uname:
        return {"ok": False, "error": "请输入管理员账号"}
    with _lock:
        data = _load_store()
        admin = None
        for a in data.get("admins") or []:
            if str(a.get("username", "")).strip() == uname:
                admin = a
                break
        if not admin or admin.get("enabled") is False:
            return {"ok": False, "error": "账号或密码错误"}
        if not _verify_password(password, admin.get("password_hash", "")):
            return {"ok": False, "error": "账号或密码错误"}
        token = _issue_token(
            "admin",
            {"username": uname, "admin_id": admin.get("id")},
        )
        log.info("admin login %s", uname)
        return {
            "ok": True,
            "token": token,
            "role": "admin",
            "username": uname,
            **quota_info_for_session(token),
        }


def login_with_code(code: str) -> dict:
    normalized = _normalize_code(code)
    if not normalized:
        return {"ok": False, "error": "请输入邀请码"}

    with _lock:
        data = _load_store()
        entry = _find_invite(data, normalized)
        if not entry:
            return {"ok": False, "error": "邀请码无效"}
        err = _validate_invite_entry(entry)
        if err:
            return {"ok": False, "error": err}

        entry["used_count"] = int(entry.get("used_count") or 0) + 1
        entry["last_used_at"] = _now_iso()
        _save_store(data)

        single_quota = _invite_single_quota_per_login(entry)
        token = _issue_token(
            "user",
            {
                "invite_id": entry.get("id"),
                "invite_code": entry.get("code"),
                "single_quota": single_quota,
                "single_used": 0,
            },
        )
        log.info(
            "invite login code_id=%s count=%s single_quota=%s",
            entry.get("id"),
            entry["used_count"],
            single_quota,
        )
        return {
            "ok": True,
            "token": token,
            "role": "user",
            "invite_code": entry.get("code"),
            **quota_info_for_session(token),
        }


def list_invites() -> list[dict]:
    with _lock:
        data = _load_store()
        out = []
        for item in data.get("invites") or []:
            row = dict(item)
            row["remaining"] = _invite_remaining(item)
            out.append(row)
        return out


def create_invite(payload: dict) -> dict:
    with _lock:
        data = _load_store()
        code = _normalize_code(payload.get("code", ""))
        if not code:
            raise ValueError("邀请码不能为空")
        if _find_invite(data, code):
            raise ValueError("邀请码已存在")
        entry = {
            "id": str(uuid.uuid4().hex[:10]),
            "code": code,
            "note": str(payload.get("note") or ""),
            "expires_at": payload.get("expires_at") or None,
            "max_uses": int(payload.get("max_uses", 1)),
            "single_quota_per_login": _invite_single_quota_per_login(
                {"single_quota_per_login": payload.get("single_quota_per_login")}
            ),
            "used_count": 0,
            "enabled": payload.get("enabled", True) is not False,
            "created_at": _now_iso(),
            "last_used_at": None,
        }
        data.setdefault("invites", []).append(entry)
        _save_store(data)
        row = dict(entry)
        row["remaining"] = _invite_remaining(entry)
        return row


def update_invite(invite_id: str, payload: dict) -> dict:
    with _lock:
        data = _load_store()
        entry = None
        for item in data.get("invites") or []:
            if str(item.get("id")) == str(invite_id):
                entry = item
                break
        if not entry:
            raise FileNotFoundError("邀请码不存在")
        if "code" in payload and payload["code"] is not None:
            new_code = _normalize_code(payload["code"])
            other = _find_invite(data, new_code)
            if other and str(other.get("id")) != str(invite_id):
                raise ValueError("邀请码已被占用")
            entry["code"] = new_code
        for key in ("note", "expires_at", "enabled", "last_used_at"):
            if key in payload:
                entry[key] = payload[key]
        if "max_uses" in payload and payload["max_uses"] is not None:
            entry["max_uses"] = int(payload["max_uses"])
        if "single_quota_per_login" in payload and payload["single_quota_per_login"] is not None:
            entry["single_quota_per_login"] = _invite_single_quota_per_login(
                {"single_quota_per_login": payload["single_quota_per_login"]}
            )
        if "used_count" in payload and payload["used_count"] is not None:
            entry["used_count"] = max(0, int(payload["used_count"]))
        _save_store(data)
        row = dict(entry)
        row["remaining"] = _invite_remaining(entry)
        return row


def delete_invite(invite_id: str) -> None:
    with _lock:
        data = _load_store()
        invites = data.get("invites") or []
        new_list = [i for i in invites if str(i.get("id")) != str(invite_id)]
        if len(new_list) == len(invites):
            raise FileNotFoundError("邀请码不存在")
        data["invites"] = new_list
        _save_store(data)


def hash_password_for_config(password: str) -> str:
    """供脚本生成 admins.json 中的 password_hash。"""
    return _hash_password(password)
