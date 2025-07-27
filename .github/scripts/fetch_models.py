#!/usr/bin/env python3
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
        comp_raw   = pricing.get("completion", "0")

        # 重新计算：
        # prompt: 原始数值 * 1,000,000 / 2
        prompt_ratio = float(prompt_raw) * 1_000_000 / 2
        # completion: 原始数值 * 1,000,000 / (prompt原始数值 * 1,000,000)
        numerator   = float(comp_raw) * 1_000_000
        denominator = float(prompt_raw) * 1_000_000
        comp_ratio  = numerator / denominator if denominator != 0 else 0

        # 日志输出
        print(f"[PROMPT]    {model_id}: raw={prompt_raw} → ratio={format_number(prompt_ratio)}")
        print(f"[COMPLETION]{model_id}: raw={comp_raw}   → ratio={format_number(comp_ratio)}")

        # 默认 id
        prompt_map_default[model_id]     = prompt_ratio
        completion_map_default[model_id] = comp_ratio

        # flexible id: 去除第一个 provider/
        flex_id = model_id.split('/', 1)[1] if '/' in model_id else model_id
        prompt_map_flex[flex_id]     = prompt_ratio
        completion_map_flex[flex_id] = comp_ratio

    return {
        "default": {
            "prompt": prompt_map_default,
            "completion": completion_map_default,
        },
        "flexible": {
            "prompt": prompt_map_flex,
            "completion": completion_map_flex,
        }
    }

def write_json_map(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["{"]
    for key, val in data.items():
        num = format_number(val)
        lines.append(f'  "{key}": {num},')
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(',')
    lines.append("}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    models = fetch_models()
    maps = build_maps(models)

    # 写入四个文件
    write_json_map(maps["default"]["prompt"],      "defaults/model-ratios/openrouter/prompt.json")
    write_json_map(maps["default"]["completion"],  "defaults/model-ratios/openrouter/completion.json")
    write_json_map(maps["flexible"]["prompt"],     "defaults/model-ratios/flexible/prompt.json")
    write_json_map(maps["flexible"]["completion"], "defaults/model-ratios/flexible/completion.json")

if __name__ == "__main__":
    main()
