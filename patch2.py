import sys

filepath = 'd:/Code/shuini_calculator/backend/models/schemas.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

marker = """class UhpcTrialMixRowResponse(BaseModel):
    cement: float
    fly_ash: float
    micro_bead: float
    silica_fume: float
    sand: float
    steel_fiber: float
    water: float
    admixture: float
    binder: float
    total: float"""

repl = """class UhpcTrialMixRowResponse(BaseModel):
    cement: float
    fly_ash: float
    micro_bead: float
    silica_fume: float
    sand: float
    steel_fiber: float
    water: float
    admixture: float
    binder: float
    total: float
    admixture_pct: Optional[float] = None"""

text = text.replace(marker, repl)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)
print("patch2 done")
