"""UI 工作流（nodes/links）与 API prompt 互转。"""
import copy
from typing import Any

WIDGET_TYPES = frozenset({"INT", "FLOAT", "STRING", "BOOLEAN"})


def _build_link_sources(links: list) -> dict[int, tuple[int, int]]:
    out = {}
    for row in links:
        if len(row) < 5:
            continue
        link_id, from_node, from_slot = row[0], row[1], row[2]
        out[link_id] = (from_node, from_slot)
    return out


def _is_widget_spec(spec: list | tuple) -> bool:
    if not spec:
        return False
    t = spec[0]
    if isinstance(t, list):
        return True
    if isinstance(t, str):
        return t in WIDGET_TYPES
    return False


def _get_input_config(spec: list | tuple) -> dict:
    if len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1]
    return {}


def get_ordered_input_specs(class_type: str, object_info: dict) -> list[dict]:
    """按 object_info 的 input_order 返回输入定义。"""
    node_info = object_info.get(class_type)
    if not node_info:
        return []

    specs = []
    input_data = node_info.get("input", {})
    input_order = node_info.get("input_order", {})

    for category in ("required", "optional", "hidden"):
        names = input_order.get(category, list(input_data.get(category, {}).keys()))
        category_inputs = input_data.get(category, {})
        for name in names:
            if name not in category_inputs:
                continue
            spec = category_inputs[name]
            config = _get_input_config(spec)
            specs.append({
                "name": name,
                "is_widget": _is_widget_spec(spec),
                "control_after_generate": bool(config.get("control_after_generate")),
            })
    return specs


def iter_widget_slots(node: dict, object_info: dict) -> list[dict]:
    """
    将 widgets_values 与输入名一一对应。
    control_after_generate（如 seed 后的 randomize）仅占位，不进入 API。
    """
    class_type = node.get("type", "")
    specs = get_ordered_input_specs(class_type, object_info)
    if not specs:
        return _iter_widget_slots_fallback(node)

    ui_by_name = {inp["name"]: inp for inp in node.get("inputs", [])}
    widgets_values = list(node.get("widgets_values") or [])
    widget_idx = 0
    slots = []

    for spec in specs:
        name = spec["name"]
        inp = ui_by_name.get(name)

        if spec["is_widget"]:
            if widget_idx >= len(widgets_values):
                break
            slots.append({
                "name": name,
                "widget_index": widget_idx,
                "value": widgets_values[widget_idx],
            })
            widget_idx += 1
            if spec["control_after_generate"] and widget_idx < len(widgets_values):
                widget_idx += 1
        elif inp and inp.get("link") is not None:
            continue

    return slots


def _iter_widget_slots_fallback(node: dict) -> list[dict]:
    slots = []
    widget_idx = 0
    widgets_values = list(node.get("widgets_values") or [])
    for inp in node.get("inputs", []):
        if inp.get("link") is not None:
            continue
        name = inp["name"]
        if widget_idx >= len(widgets_values):
            break
        slots.append({
            "name": name,
            "widget_index": widget_idx,
            "value": widgets_values[widget_idx],
        })
        widget_idx += 1
    return slots


def ui_to_api(ui_data: dict, object_info: dict | None = None) -> dict:
    if object_info is None:
        from comfy_client import get_object_info
        object_info = get_object_info()

    link_sources = _build_link_sources(ui_data.get("links", []))
    api: dict[str, Any] = {}

    for node in ui_data.get("nodes", []):
        if node.get("mode", 0) == 4:
            continue

        node_id = str(node["id"])
        class_type = node["type"]
        specs = get_ordered_input_specs(class_type, object_info)
        ui_by_name = {inp["name"]: inp for inp in node.get("inputs", [])}
        widgets_values = list(node.get("widgets_values") or [])
        api_inputs: dict[str, Any] = {}

        if specs:
            widget_idx = 0
            for spec in specs:
                name = spec["name"]
                inp = ui_by_name.get(name)

                if inp and inp.get("link") is not None:
                    src = link_sources.get(inp["link"])
                    if src is not None:
                        api_inputs[name] = [str(src[0]), src[1]]
                elif spec["is_widget"]:
                    if widget_idx < len(widgets_values):
                        api_inputs[name] = widgets_values[widget_idx]
                    widget_idx += 1
                    if spec["control_after_generate"] and widget_idx < len(widgets_values):
                        widget_idx += 1
        else:
            widget_idx = 0
            for inp in node.get("inputs", []):
                name = inp["name"]
                link_id = inp.get("link")
                if link_id is not None:
                    src = link_sources.get(link_id)
                    if src is not None:
                        api_inputs[name] = [str(src[0]), src[1]]
                else:
                    if widget_idx < len(widgets_values):
                        api_inputs[name] = widgets_values[widget_idx]
                    widget_idx += 1

        api[node_id] = {
            "class_type": class_type,
            "inputs": api_inputs,
        }

    return api


def apply_overrides_ui(ui_data: dict, overrides: dict[str, dict[str, Any]], object_info: dict | None = None) -> dict:
    if object_info is None:
        from comfy_client import get_object_info
        object_info = get_object_info()

    result = copy.deepcopy(ui_data)
    for node in result.get("nodes", []):
        sid = str(node["id"])
        if sid not in overrides:
            continue
        patch = overrides[sid]
        wv = list(node.get("widgets_values") or [])
        for slot in iter_widget_slots(node, object_info):
            name = slot["name"]
            if name not in patch:
                continue
            idx = slot["widget_index"]
            while len(wv) <= idx:
                wv.append(None)
            wv[idx] = patch[name]
        node["widgets_values"] = wv
    return result
