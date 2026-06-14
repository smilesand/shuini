import sys

filepath = 'd:/Code/shuini_calculator/backend/services/uhpc_trial.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

marker = """    # ── Tab 3: 校正配合比 ──────────────────────────────────────────
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

repl = """    # ── Tab 3: 校正配合比 ──────────────────────────────────────────
    if corr_base == "wbRec" and rec_wb is not None:
        # 提取各自实际掺量(%)
        alpha_base = trial_mix["admixture"] / trial_mix["binder"] * 100.0 if trial_mix["binder"] > 0 else trial_alpha
        alpha_plus = variant_wb_plus["admixture"] / variant_wb_plus["binder"] * 100.0 if variant_wb_plus["binder"] > 0 else trial_alpha
        alpha_minus = variant_wb_minus["admixture"] / variant_wb_minus["binder"] * 100.0 if variant_wb_minus["binder"] > 0 else trial_alpha
        
        fitted_alpha = _linear_predict(
            wb, alpha_base,
            wb + 0.01, alpha_plus,
            wb - 0.01, alpha_minus,
            rec_wb
        )
        fitted_alpha = max(0.0, fitted_alpha)
        corr_mix = _calc_mix(rec_wb, trial_sb, fitted_alpha, sf_mass, total,
                             cement_pct, silica_fume_pct, fly_ash_pct, micro_bead_pct)
    elif corr_base == "sfRec" and rec_sf is not None:
        binder = trial_mix["binder"]
        if binder > 0:
            new_sf_pct = rec_sf / binder * 100.0
            orig_sf_pct = silica_fume_pct
            adjusted_ce_pct = cement_pct - (new_sf_pct - orig_sf_pct)
            
            base_sf = trial_mix["silica_fume"]
            alpha_base = trial_mix["admixture"] / trial_mix["binder"] * 100.0
            alpha_plus = variant_sf_plus["admixture"] / variant_sf_plus["binder"] * 100.0 if variant_sf_plus["binder"] > 0 else trial_alpha
            alpha_minus = variant_sf_minus["admixture"] / variant_sf_minus["binder"] * 100.0 if variant_sf_minus["binder"] > 0 else trial_alpha

            fitted_alpha = _linear_predict(
                base_sf, alpha_base,
                variant_sf_plus["silica_fume"], alpha_plus,
                variant_sf_minus["silica_fume"], alpha_minus,
                rec_sf
            )
            fitted_alpha = max(0.0, fitted_alpha)

            corr_mix = _calc_mix(wb, trial_sb, fitted_alpha, sf_mass, total,
                                 adjusted_ce_pct, new_sf_pct, fly_ash_pct, micro_bead_pct)
        else:
            corr_mix = _empty_mix()
    else:
        corr_mix = trial_mix"""

text = text.replace(marker, repl)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch applied for alpha interpolation")
