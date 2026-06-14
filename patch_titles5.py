import sys
import shutil

filepath = 'd:/Code/shuini_calculator/frontend/src/components/uhpc-trial/UhpcTrialStrengthTab.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

marker = """                  <div v-else class="mix-cell__val">{{ fmt(v.mix ? v.mix[k as keyof typeof v.mix] : null) }}</div>
                </div>
              </div>
            </div>
            <div class="vrow-input">
              <el-input-number"""

repl = """                  <div v-else class="mix-cell__val">{{ fmt(v.mix ? v.mix[k as keyof typeof v.mix] : null) }}</div>
                </div>
                <div class="mix-cell mix-cell--sm mix-cell--total">
                  <div class="mix-cell__head">合计</div>
                  <div class="mix-cell__val">{{ fmt(v.mix ? v.mix.total : null) }}</div>
                </div>
              </div>
            </div>
            <div class="vrow-input">
              <el-input-number"""

new_text = text.replace(marker, repl)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_text)

print(f"Replaced {text.count(marker)} instances.")
