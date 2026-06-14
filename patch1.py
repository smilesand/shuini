import sys

filepath = 'd:/Code/shuini_calculator/backend/services/uhpc_trial.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. empty_mix
marker1 = """        "binder": 0.0,
        "total": 0.0,
    }"""
repl1 = """        "binder": 0.0,
        "total": 0.0,
        "admixture_pct": 0.0,
    }"""
content = content.replace(marker1, repl1)

# 2. calc_mix
marker2 = """    admixture = admix_override if admix_override is not None else binder * alpha / 100.0
    result_total = binder * (1.0 + sb + wb) + sf_mass + admixture

    return {
        "cement": _round_js(cement, 1),
        "fly_ash": _round_js(fly_ash, 1),
        "micro_bead": _round_js(micro_bead, 1),
        "silica_fume": _round_js(silica_fume, 1),
        "sand": _round_js(sand, 1),
        "steel_fiber": _round_js(sf_mass, 1),
        "water": _round_js(water_mass, 1),
        "admixture": _round_js(admixture, 1),
        "binder": _round_js(binder, 1),
        "total": _round_js(result_total, 1),
    }"""

repl2 = """    admixture = admix_override if admix_override is not None else binder * alpha / 100.0
    result_total = binder * (1.0 + sb + wb) + sf_mass + admixture
    admixture_pct = admixture / binder * 100.0 if binder > 0 else 0.0

    return {
        "cement": _round_js(cement, 1),
        "fly_ash": _round_js(fly_ash, 1),
        "micro_bead": _round_js(micro_bead, 1),
        "silica_fume": _round_js(silica_fume, 1),
        "sand": _round_js(sand, 1),
        "steel_fiber": _round_js(sf_mass, 1),
        "water": _round_js(water_mass, 1),
        "admixture": _round_js(admixture, 1),
        "binder": _round_js(binder, 1),
        "total": _round_js(result_total, 1),
        "admixture_pct": _round_js(admixture_pct, 2),
    }"""

content = content.replace(marker2, repl2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
