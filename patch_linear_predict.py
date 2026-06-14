import sys

filepath = 'd:/Code/shuini_calculator/backend/services/uhpc_trial.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Insert _linear_predict after _linear_fit
marker1 = """    lo, hi = min(xs), max(xs)
    return max(min(result, hi), lo)"""

insert1 = """

def _linear_predict(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, t_x: float) -> float:
    \"\"\"三点最小二乘线性回归，供已知 x 预测 y 使用（如预测外加剂用量）。\"\"\"
    xs = [x1, x2, x3]
    ys = [y1, y2, y3]
    n = 3
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-9:
        return (y1 + y2 + y3) / 3.0
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    return a * t_x + b"""

if marker1 in text:
    text = text.replace(marker1, marker1 + insert1)

# 2. Update Tab 3
marker2 = """    # ── Tab 3: 校正配合比 ──────────────────────────────────────────
    if corr_base == "wbRec" and rec_wb is not None:
        corr_mix = _calc_mix(rec_wb, trial_sb, trial_alpha, sf_mass, total,
                             cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct)
    elif corr_base == "sfRec" and rec_sf is not None:
        binder = trial_mix["binder"]
        if binder > 0:
            new_sf_pct = rec_sf / binder * 100.0
            orig_sf_pct = silica_fume_pct
            adjusted_ce_pct = cement_pct - (new_sf_pct - orig_sf_pct)
            corr_mix = _calc_mix(wb, trial_sb, trial_alpha, sf_mass, total,
                                 adjusted_ce_pct, new_sf_pct, fly_ash_pct, micro_bead_pct)
        else:
            corr_mix = _empty_mix()
    else:
        corr_mix = trial_mix"""

repl2 = """    # ── Tab 3: 校正配合比 ──────────────────────────────────────────
    if corr_base == "wbRec" and rec_wb is not None:
        fitted_admix = _linear_predict(
            wb, trial_mix["admixture"],
            wb + 0.01, variant_wb_plus["admixture"],
            wb - 0.01, variant_wb_minus["admixture"],
            rec_wb
        )
        fitted_admix = max(0.0, fitted_admix)
        corr_mix = _calc_mix(rec_wb, trial_sb, trial_alpha, sf_mass, total,
                             cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct,
                             admix_override=fitted_admix)
    elif corr_base == "sfRec" and rec_sf is not None:
        binder = trial_mix["binder"]
        if binder > 0:
            new_sf_pct = rec_sf / binder * 100.0
            orig_sf_pct = silica_fume_pct
            adjusted_ce_pct = cement_pct - (new_sf_pct - orig_sf_pct)
            
            base_sf = trial_mix["silica_fume"]
            fitted_admix = _linear_predict(
                base_sf, trial_mix["admixture"],
                variant_sf_plus["silica_fume"], variant_sf_plus["admixture"],
                variant_sf_minus["silica_fume"], variant_sf_minus["admixture"],
                rec_sf
            )
            fitted_admix = max(0.0, fitted_admix)

            corr_mix = _calc_mix(wb, trial_sb, trial_alpha, sf_mass, total,
                                 adjusted_ce_pct, new_sf_pct, fly_ash_pct, micro_bead_pct,
                                 admix_override=fitted_admix)
        else:
            corr_mix = _empty_mix()
    else:
        corr_mix = trial_mix"""

text = text.replace(marker2, repl2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch applied")
