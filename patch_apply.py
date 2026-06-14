import sys

filepath = 'd:/Code/shuini_calculator/backend/services/uhpc_trial.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

marker = """def _apply_correction(mix: dict, factor: Optional[float]) -> dict:
    \"\"\"对配合比各组分按统一校正系数缩放。\"\"\"
    if factor is None or factor <= 0:
        return _empty_mix()

    return {
        key: _round_js(mix[key] * factor, 1) if mix.get(key) is not None else 0.0
        for key in _empty_mix()
    }"""

repl = """def _apply_correction(mix: dict, factor: Optional[float]) -> dict:
    \"\"\"对配合比各组分按统一校正系数缩放。\"\"\"
    if factor is None or factor <= 0:
        return _empty_mix()

    res = {
        key: _round_js(mix[key] * factor, 1) if mix.get(key) is not None else 0.0
        for key in _empty_mix() if key != "admixture_pct"
    }
    # 百分比不应该乘系数
    res["admixture_pct"] = mix.get("admixture_pct", 0.0)
    return res"""

if marker in text:
    text = text.replace(marker, repl)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    print("applied")
else:
    print("not found")
