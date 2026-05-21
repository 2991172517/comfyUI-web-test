import copy
import json
import re
from pathlib import Path
from typing import Any

from config import (
    EDITABLE_CONFIG,
    WORKFLOW_TEMPLATE_ID,
    WORKFLOW_VARIANTS_DIR,
    WORKFLOWS_DIR,
    WORKFLOWS_REL,
)
from comfy_client import get_object_info
from ui_workflow import apply_overrides_ui, iter_widget_slots, ui_to_api

LORA_CLASS_TYPES = frozenset({"LoraLoader", "LoraLoaderModelOnly"})


def _load_editable_rules() -> list[dict]:
    with open(EDITABLE_CONFIG, encoding="utf-8") as f:
        return json.load(f)["rules"]


def _is_api_prompt(data: dict) -> bool:
    if "nodes" in data and isinstance(data.get("nodes"), list):
        return False
    if not data:
        return False
    for value in data.values():
        if isinstance(value, dict) and "class_type" in value:
            return True
    return False


VARIANT_PREFIX = "variants/"


def _workflow_path(workflow_id: str) -> Path:
    from workflow_meta_service import normalize_variant_workflow_id

    workflow_id = normalize_variant_workflow_id(workflow_id)
    if workflow_id.startswith(VARIANT_PREFIX):
        name = workflow_id.split("/", 1)[1]
        return WORKFLOW_VARIANTS_DIR / f"{name}.json"
    return WORKFLOWS_DIR / f"{workflow_id}.json"


def is_master_workflow(workflow_id: str) -> bool:
    return workflow_id == WORKFLOW_TEMPLATE_ID


def _fields_for_class(class_type: str, rules: list[dict]) -> tuple[str | None, list[str]]:
    for rule in rules:
        if class_type in rule["class_types"]:
            return rule.get("group"), list(rule["fields"])
    return None, []


def _infer_field_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return "readonly"


# ComfyUI /models/{folder} 文件夹名
_MODEL_SELECT_FIELDS = {
    "ckpt_name": ("checkpoints", "Checkpoint"),
    "lora_name": ("loras", "LoRA"),
}


def _build_field_dict(key: str, value: Any, label: str | None = None) -> dict:
    field = {
        "key": key,
        "label": label or key,
        "value": value,
        "type": _infer_field_type(value),
    }
    if key in _MODEL_SELECT_FIELDS:
        folder, default_label = _MODEL_SELECT_FIELDS[key]
        field["type"] = "model_select"
        field["model_folder"] = folder
        field["label"] = default_label
    return field


def _sort_node_id(node_id: str):
    return int(node_id) if str(node_id).isdigit() else node_id


def discover_lora_nodes(prompt: dict) -> list[dict]:
    loras = []
    for node_id, node in prompt.items():
        if node.get("class_type") not in LORA_CLASS_TYPES:
            continue
        inputs = node.get("inputs", {})
        meta = node.get("_meta") or {}
        name = inputs.get("lora_name", "")
        short = re.sub(r"\.(safetensors|ckpt|pt)$", "", str(name), flags=re.I)
        loras.append({
            "node_id": str(node_id),
            "class_type": node.get("class_type"),
            "title": meta.get("title") or node.get("class_type"),
            "lora_name": name,
            "short_name": short or str(node_id),
            "strength_model": float(inputs.get("strength_model", 1)),
            "strength_clip": float(inputs.get("strength_clip", 1)),
        })
    loras.sort(key=lambda x: _sort_node_id(x["node_id"]))
    for i, item in enumerate(loras):
        item["chain_order"] = i + 1
    return loras


def discover_workflow_targets(prompt: dict) -> dict:
    save_nodes = []
    seed_nodes = []
    for node_id, node in prompt.items():
        ct = node.get("class_type", "")
        meta = node.get("_meta") or {}
        title = meta.get("title") or ct
        if ct == "SaveImage":
            save_nodes.append({"node_id": str(node_id), "title": title})
        if ct == "KSampler":
            seed_nodes.append({
                "node_id": str(node_id),
                "title": title,
                "seed": node.get("inputs", {}).get("seed"),
            })
    save_nodes.sort(key=lambda x: _sort_node_id(x["node_id"]))
    seed_nodes.sort(key=lambda x: _sort_node_id(x["node_id"]))
    return {
        "save_node_id": save_nodes[0]["node_id"] if save_nodes else None,
        "save_nodes": save_nodes,
        "seed_node_id": seed_nodes[0]["node_id"] if seed_nodes else None,
        "seed_nodes": seed_nodes,
    }


def list_workflows() -> list[dict]:
    import workflow_meta_service as wms

    if not WORKFLOWS_DIR.is_dir():
        return []
    items = []
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        if path.stem.endswith(".meta"):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            fmt = "api" if _is_api_prompt(data) else "ui"
        except (json.JSONDecodeError, OSError):
            fmt = "unknown"
        wid = path.stem
        meta = wms.load_meta(wid)
        items.append({
            "id": wid,
            "name": wid,
            "filename": path.name,
            "format": fmt,
            "path": f"{WORKFLOWS_REL}/{path.name}",
            "is_master": wid == WORKFLOW_TEMPLATE_ID,
            "is_variant": False,
            "display_name": (meta or {}).get("display_name", wid),
        })
    WORKFLOW_VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(WORKFLOW_VARIANTS_DIR.glob("*.json")):
        if path.stem.endswith(".meta"):
            continue
        vid = path.stem
        wid = f"{VARIANT_PREFIX}{vid}"
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            fmt = "api" if _is_api_prompt(data) else "ui"
        except (json.JSONDecodeError, OSError):
            fmt = "unknown"
        meta = wms.load_meta(wid) or {}
        items.append({
            "id": wid,
            "name": vid,
            "filename": path.name,
            "format": fmt,
            "path": f"{WORKFLOWS_REL}/variants/{path.name}",
            "is_master": False,
            "is_variant": True,
            "display_name": meta.get("display_name", vid),
            "template_id": meta.get("template_id", WORKFLOW_TEMPLATE_ID),
        })
    return items


def load_workflow_file(workflow_id: str) -> tuple[str, dict]:
    path = _workflow_path(workflow_id)
    if not path.is_file():
        raise FileNotFoundError(f"工作流不存在: {workflow_id}（目录: {WORKFLOWS_DIR}）")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    fmt = "api" if _is_api_prompt(data) else "ui"
    return fmt, data


def save_workflow_file(workflow_id: str, data: dict) -> None:
    path = _workflow_path(workflow_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_editable_view_api(prompt: dict) -> list[dict]:
    rules = _load_editable_rules()
    nodes = []
    for node_id, node in sorted(prompt.items(), key=lambda x: _sort_node_id(x[0])):
        class_type = node.get("class_type", "")
        group, field_names = _fields_for_class(class_type, rules)
        if not field_names:
            continue
        inputs = node.get("inputs", {})
        fields = []
        for key in field_names:
            if key not in inputs:
                continue
            value = inputs[key]
            if isinstance(value, list):
                continue
            fields.append(_build_field_dict(key, value))
        if not fields:
            continue
        meta = node.get("_meta") or {}
        title = meta.get("title") or class_type
        nodes.append({
            "id": node_id,
            "class_type": class_type,
            "title": f"{title} (#{node_id})",
            "group": group or class_type,
            "fields": fields,
        })
    return nodes


def build_editable_view_ui(ui_data: dict) -> list[dict]:
    rules = _load_editable_rules()
    object_info = get_object_info()
    ui_inputs_map = {
        str(n["id"]): {inp["name"]: inp for inp in n.get("inputs", [])}
        for n in ui_data.get("nodes", [])
    }
    nodes_out = []
    for node in ui_data.get("nodes", []):
        class_type = node.get("type", "")
        group, field_names = _fields_for_class(class_type, rules)
        if not field_names:
            continue
        fields = []
        inp_by_name = ui_inputs_map.get(str(node["id"]), {})
        for slot in iter_widget_slots(node, object_info):
            name = slot["name"]
            if name not in field_names:
                continue
            inp = inp_by_name.get(name, {})
            fields.append(
                _build_field_dict(name, slot["value"], inp.get("localized_name") or name)
            )
        if not fields:
            continue
        title = node.get("properties", {}).get("Node name for S&R", class_type)
        nodes_out.append({
            "id": str(node["id"]),
            "class_type": class_type,
            "title": f"{title} (#{node['id']})",
            "group": group or class_type,
            "fields": fields,
        })
    return nodes_out


def get_workflow_detail(workflow_id: str, *, style_enabled: bool | None = None) -> dict:
    import workflow_meta_service as wms

    fmt, data = load_workflow_file(workflow_id)
    if fmt != "api":
        raise ValueError("批量功能目前仅支持 API 格式工作流，请使用 Export (API) 导出。")
    nodes = build_editable_view_api(data)
    targets = discover_workflow_targets(data)
    loras = discover_lora_nodes(data)
    runtime = {"style_enabled": style_enabled} if style_enabled is not None else None
    meta = wms.get_effective_meta(workflow_id, runtime)
    detail = {
        "id": workflow_id,
        "format": "api",
        "prompt": data,
        "workflow": None,
        "nodes": nodes,
        "loras": loras,
        "targets": targets,
        "workflows_dir": str(WORKFLOWS_DIR),
    }
    return wms.enrich_workflow_detail(workflow_id, detail, meta)


def save_with_overrides(workflow_id: str, overrides: dict[str, dict[str, Any]]) -> None:
    if is_master_workflow(workflow_id):
        raise ValueError("母版工作流只读，请另存为子工作流后再修改")
    fmt, data = load_workflow_file(workflow_id)
    object_info = get_object_info()
    if fmt == "api":
        data = apply_overrides(data, overrides)
    else:
        data = apply_overrides_ui(data, overrides, object_info)
    save_workflow_file(workflow_id, data)


def build_api_prompt(
    workflow_id: str,
    overrides: dict[str, dict[str, Any]],
    *,
    style_enabled: bool | None = None,
    apply_defaults: bool = True,
) -> dict:
    import prompt_defaults_service as pds
    import workflow_meta_service as wms

    fmt, data = load_workflow_file(workflow_id)
    object_info = get_object_info()
    if fmt == "api":
        prompt = apply_overrides(data, overrides)
    else:
        patched = apply_overrides_ui(data, overrides, object_info)
        prompt = ui_to_api(patched, object_info)

    runtime = {}
    if style_enabled is not None:
        runtime["style_enabled"] = style_enabled
    meta = wms.get_effective_meta(workflow_id, runtime or None)
    prompt = wms.apply_topology(prompt, meta)
    if apply_defaults:
        prompt = pds.apply_prompt_defaults(prompt)
    return prompt


def apply_overrides(prompt: dict, overrides: dict[str, dict[str, Any]]) -> dict:
    result = copy.deepcopy(prompt)
    for node_id, patch in overrides.items():
        if node_id not in result:
            continue
        inputs = result[node_id].setdefault("inputs", {})
        for key, value in patch.items():
            if key in inputs and isinstance(inputs[key], list):
                continue
            inputs[key] = value
    return result
