import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/api/calc.ts'
text = Path(path).read_text(encoding='utf-8')

marker = """export interface UhpcTrialMixRowRes {
  cement: number
  fly_ash: number
  micro_bead: number
  silica_fume: number
  sand: number
  steel_fiber: number
  water: number
  admixture: number
  binder: number
  total: number
}"""

insert = """export interface UhpcTrialMixRowRes {
  cement: number
  fly_ash: number
  micro_bead: number
  silica_fume: number
  sand: number
  steel_fiber: number
  water: number
  admixture: number
  admixture_pct?: number
  binder: number
  total: number
}"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("calc.ts patched")