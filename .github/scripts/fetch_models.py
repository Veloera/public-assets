#!/usr/bin/env python3
import os
import json
import requests

API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/models")

def fetch_models():
    resp = requests.get(API_URL)
    resp.raise_for_status()
    return resp.json().get("data", [])

def compute_ratio(value_str: str) -> float:
    # 注意：不要提前化简，保持 (float * 1,000,000 / 500,000)
    return float(value_str) * 1_000_000 / 500_000

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

        # 默认 id
        prompt_map_default[model_id] = compute_ratio(prompt_raw)
        completion_map_default[model_id] = compute_ratio(comp_raw)

        # flexible id: 去除第一个斜杠之前的 provider/
        if "/" in model_id:
            flex_id = model_id.split("/", 1)[1]
        else:
            flex_id = model_id

        prompt_map_flex[flex_id] = compute_ratio(prompt_raw)
        completion_map_flex[flex_id] = compute_ratio(comp_raw)

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

def write_json(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    models = fetch_models()
    maps = build_maps(models)

    # 写入 four files
    write_json(maps["default"]["prompt"],      "defaults/model-ratios/openrouter/prompt.json")
    write_json(maps["default"]["completion"],  "defaults/model-ratios/openrouter/completion.json")
    write_json(maps["flexible"]["prompt"],     "defaults/model-ratios/flexible/prompt.json")
    write_json(maps["flexible"]["completion"], "defaults/model-ratios/flexible/completion.json")

if __name__ == "__main__":
    main()
