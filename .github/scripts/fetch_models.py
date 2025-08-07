#!/usr/bin/env python3
#
# Copyright (C) 2025 Veloera
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import json
import requests

API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/models")

def fetch_models():
    resp = requests.get(API_URL)
    resp.raise_for_status()
    return resp.json().get("data", [])

def format_number(value: float) -> str:
    # 用 12 位小数输出，去掉末尾多余的 0 和小数点
    s = f"{value:.12f}".rstrip('0').rstrip('.')
    return s if not s.startswith('.') else '0' + s

def build_maps(models):
    prompt_map_default = {}
    completion_map_default = {}
    prompt_map_flex = {}
    completion_map_flex = {}

    for item in models:
        model_id = item.get("id", "")
        pricing = item.get("pricing", {})
        prompt_raw = pricing.get("prompt", "0")
        comp_raw = pricing.get("completion", "0")

        prompt_ratio = float(prompt_raw) * 1_000_000 / 2
        numerator = float(comp_raw) * 1_000_000
        denominator = float(prompt_raw) * 1_000_000
        comp_ratio = numerator / denominator if denominator != 0 else 0

        if prompt_ratio < 0 or comp_ratio < 0:
            continue

        prompt_map_default[model_id] = prompt_ratio
        completion_map_default[model_id] = comp_ratio

        flex_id = model_id.split('/', 1)[1] if '/' in model_id else model_id

        if not (prompt_ratio == 0 and comp_ratio == 0) and flex_id not in ("auto", "router"):
            prompt_map_flex[flex_id] = prompt_ratio
            completion_map_flex[flex_id] = comp_ratio

    return {
        "default": {"prompt": prompt_map_default, "completion": completion_map_default},
        "flexible": {"prompt": prompt_map_flex, "completion": completion_map_flex}
    }

def build_mixed_map(default_map: dict, flex_map: dict):
    # flexible 映射将覆盖 default 中的同名键
    mixed_map = default_map.copy()
    mixed_map.update(flex_map)
    return mixed_map

def write_json_map(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keys = sorted(data.keys())
    lines = ["{"]
    for key in keys:
        num = format_number(data[key])
        lines.append(f'  "{key}": {num},')
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(',')
    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    models = fetch_models()
    maps = build_maps(models)

    # 写入默认映射
    write_json_map(maps["default"]["prompt"],     "defaults/model-ratios/openrouter/prompt.json")
    write_json_map(maps["default"]["completion"], "defaults/model-ratios/openrouter/completion.json")

    # 写入 flexible 映射
    write_json_map(maps["flexible"]["prompt"],    "defaults/model-ratios/flexible/prompt.json")
    write_json_map(maps["flexible"]["completion"],"defaults/model-ratios/flexible/completion.json")

    # 构建 mixed 映射（flexible 覆盖 default 同名 key）
    mixed_prompt = build_mixed_map(maps["default"]["prompt"], maps["flexible"]["prompt"])
    mixed_completion = build_mixed_map(maps["default"]["completion"], maps["flexible"]["completion"])

    # 写入 mixed 映射
    write_json_map(mixed_prompt,     "defaults/model-ratios/mixed/prompt.json")
    write_json_map(mixed_completion, "defaults/model-ratios/mixed/completion.json")

if __name__ == "__main__":
    main()
