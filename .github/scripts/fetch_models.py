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

        # 重新计算:
        prompt_ratio = float(prompt_raw) * 1_000_000 / 2
        numerator = float(comp_raw) * 1_000_000
        denominator = float(prompt_raw) * 1_000_000
        comp_ratio = numerator / denominator if denominator != 0 else 0

        # 跳过负值模型
        if prompt_ratio < 0 or comp_ratio < 0:
            continue

        # 默认 mapping
        prompt_map_default[model_id] = prompt_ratio
        completion_map_default[model_id] = comp_ratio

        # flexible id: 去除 provider/
        flex_id = model_id.split('/', 1)[1] if '/' in model_id else model_id

        # 在 flexible 中忽略 prompt/completion 均为0, 及名称 auto 和 router
        if not (prompt_ratio == 0 and comp_ratio == 0) and flex_id not in ("auto", "router"):
            prompt_map_flex[flex_id] = prompt_ratio
            completion_map_flex[flex_id] = comp_ratio

    return {
        "default": {"prompt": prompt_map_default, "completion": completion_map_default},
        "flexible": {"prompt": prompt_map_flex, "completion": completion_map_flex}
    }

def write_json_map(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 按字母表顺序排序 key
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

    # 写入四个文件，JSON 输出均按键排序
    write_json_map(maps["default"]["prompt"],     "defaults/model-ratios/openrouter/prompt.json")
    write_json_map(maps["default"]["completion"], "defaults/model-ratios/openrouter/completion.json")
    write_json_map(maps["flexible"]["prompt"],    "defaults/model-ratios/flexible/prompt.json")
    write_json_map(maps["flexible"]["completion"],"defaults/model-ratios/flexible/completion.json")

if __name__ == "__main__":
    main()
