from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Literal


def ok(data: Any = None) -> dict:
    return {'code': 0, 'message': 'ok', 'data': data}


class WaterBinderRequest(BaseModel):
    fcuk: float = Field(..., gt=0)
    fb:   float = Field(..., gt=0)
    aa:   float = Field(0.33)
    ab:   float = Field(1.09)
    ac:   float = Field(-49.54)

class WaterBinderResponse(BaseModel):
    fcu0: float
    wb:   float

class FitCoefficientsRequest(BaseModel):
    csv_text: str = Field(...)

class FitCoefficientsResponse(BaseModel):
    aa: float; ab: float; ac: float; r2: float

class AggregateRequest(BaseModel):
    vg: float = Field(..., gt=0)
    rhog: float = Field(..., gt=0)
    beta_s: float = Field(..., gt=0, lt=1)
    rhos: float = Field(..., gt=0)

class AggregateResponse(BaseModel):
    mg: float; ms: float

class BinderRequest(BaseModel):
    b1p: float = Field(0, ge=0); rho1: float = Field(2200, gt=0)
    b2p: float = Field(0, ge=0); rho2: float = Field(2900, gt=0)
    b3p: float = Field(0, ge=0); rho3: float = Field(2600, gt=0)
    b4p: float = Field(0, ge=0); rho4: float = Field(2200, gt=0)
    rhoc: float = Field(..., gt=0); va: float = Field(0.01, ge=0)
    mg: float = Field(..., gt=0); ms: float = Field(..., gt=0)
    rhog: float = Field(..., gt=0); rhos: float = Field(..., gt=0)
    wb: float = Field(..., gt=0)

class BinderResponse(BaseModel):
    bc: float; rhob: float; vp: float; mb: float
    m1: float; m2: float; m3: float; m4: float; mc: float

class WaterAdmixtureRequest(BaseModel):
    mb: float = Field(..., gt=0); wb: float = Field(..., gt=0)
    alpha: float = Field(..., gt=0, le=100)

class WaterAdmixtureResponse(BaseModel):
    mw: float; ma: float


class UhpcMixRequest(BaseModel):
    strength_grade: float = Field(..., gt=0)
    water_binder_ratio: float = Field(..., gt=0)
    admixture_ratio: float = Field(..., ge=0, lt=100)
    sand_binder_ratio: float = Field(..., gt=0)
    steel_fiber_volume_ratio: float = Field(..., ge=0, lt=100)

    max_particle_size: float = Field(..., gt=0)
    min_particle_size: float = Field(1, gt=0)
    distribution_index: float = Field(0.22, gt=0)
    fly_ash_peak_size: float = Field(..., gt=0)
    fly_ash_accumulation_size: float = Field(..., gt=0)
    micro_bead_peak_size: float = Field(..., gt=0)
    micro_bead_silica_fume_ratio: float = Field(..., gt=0, lt=1)

    cement_density: float = Field(..., gt=0)
    fly_ash_density: float = Field(..., gt=0)
    micro_bead_density: float = Field(..., gt=0)
    silica_fume_density: float = Field(..., gt=0)
    micro_powder_coefficient: float = Field(..., gt=0)

    assumed_mix_mass: float = Field(2500, gt=0)
    steel_fiber_density: float = Field(7850, gt=0)


class UhpcRatioResponse(BaseModel):
    cement: float
    fly_ash: float
    micro_bead: float
    silica_fume: float


class UhpcMassRatioSetResponse(BaseModel):
    initial: UhpcRatioResponse
    corrected: UhpcRatioResponse


class UhpcMaterialMassesResponse(BaseModel):
    binder: float
    cement: float
    fly_ash: float
    micro_bead: float
    silica_fume: float
    sand: float
    steel_fiber: float
    water: float
    admixture: float
    total: float


class UhpcMixResponse(BaseModel):
    design_strength: float
    assumed_mix_mass: float
    steel_fiber_density: float
    binder_volume_ratios: UhpcRatioResponse
    binder_mass_ratios: UhpcMassRatioSetResponse
    material_masses: UhpcMaterialMassesResponse

class AdaptRequest(BaseModel):
    mb_adj: float = Field(..., gt=0)
    beta_s_adj: float = Field(..., gt=0, lt=1)
    alpha_adj: float = Field(..., ge=0, le=100)
    wb: float = Field(..., gt=0)
    bc: float = Field(..., ge=0, le=1)
    b1: float = Field(0, ge=0, le=1)
    b2: float = Field(0, ge=0, le=1)
    b3: float = Field(0, ge=0, le=1)
    b4: float = Field(0, ge=0, le=1)
    mg: float = Field(..., gt=0)

class AdaptResponse(BaseModel):
    mb: float; mc: float; m1: float; m2: float; m3: float; m4: float
    mg: float; ms: float; mw: float; ma: float


class HpcTrialRequest(BaseModel):
    """
    高性能试配统一计算请求。

    请求中同时带上主计算页得到的基准配合比，以及三步试配流程当前的用户输入。
    服务端据此一次性返回工作性、强度、校正三步的全部派生结果，确保所有步骤共用同一套公式来源。
    """
    wb: float = Field(..., gt=0)
    beta_s: float = Field(..., gt=0, lt=100)
    mb: float = Field(..., gt=0)
    mc: float = Field(..., gt=0)
    m1: float = Field(0, ge=0)
    m2: float = Field(0, ge=0)
    m3: float = Field(0, ge=0)
    m4: float = Field(0, ge=0)
    mg: float = Field(..., gt=0)
    ms: float = Field(..., gt=0)
    mw: float = Field(..., gt=0)
    ma: float = Field(0, ge=0)
    alpha: float = Field(..., ge=0, le=100)

    batch_volume: float = Field(20, gt=0)
    workability_binder_delta: float = Field(0)
    workability_sand_ratio_delta: float = Field(0)
    workability_alpha_delta: float = Field(0)

    delta_wb: float = Field(0.02, ge=0)
    delta_bs: float = Field(2, ge=0)
    strength0: Optional[float] = Field(default=None, ge=0)
    strength_p: Optional[float] = Field(default=None, ge=0)
    strength_n: Optional[float] = Field(default=None, ge=0)
    target_strength: Optional[float] = Field(default=None, gt=0)

    wb_adj: Optional[float] = Field(default=None, gt=0)
    mb_adj: Optional[float] = Field(default=None, gt=0)
    sand_ratio_adj: Optional[float] = Field(default=None, gt=0, lt=100)
    alpha_adj: Optional[float] = Field(default=None, ge=0, le=100)
    measured_density: Optional[float] = Field(default=None, gt=0)
    trial_alpha: Optional[float] = Field(default=None, ge=0, le=100)
    trial_ma0: Optional[float] = Field(default=None, ge=0)
    trial_maP: Optional[float] = Field(default=None, ge=0)
    trial_maN: Optional[float] = Field(default=None, ge=0)


class HpcTrialMaterialRowResponse(BaseModel):
    """试拌量换算结果中的单列数据。"""
    key: str
    label: str
    trial_val: Optional[float] = None


class HpcTrialMaterialResultResponse(BaseModel):
    """通用材料结果结构，供校正结果和实验室配合比复用。"""
    mc: Optional[float] = None
    m1: Optional[float] = None
    m2: Optional[float] = None
    m3: Optional[float] = None
    m4: Optional[float] = None
    mg: Optional[float] = None
    ms: Optional[float] = None
    mw: Optional[float] = None
    ma: Optional[float] = None
    total: Optional[float] = None


class HpcTrialWorkabilityResultResponse(HpcTrialMaterialResultResponse):
    """工作性实验每方结果，额外包含胶材总量、水胶比、砂率和外加剂掺量。"""
    mb: Optional[float] = None
    wb: Optional[float] = None
    bs: Optional[float] = None
    alpha: Optional[float] = None


class HpcTrialStrengthMixResponse(HpcTrialMaterialResultResponse):
    """强度实验单组配合比。"""
    label: str = ''
    wb: Optional[float] = None
    bs: Optional[float] = None
    mb: Optional[float] = None


class HpcTrialStrengthRegressionResponse(BaseModel):
    """强度回归分析结果。"""
    a: float
    b: float
    r2: float
    recommend_wb: Optional[float] = None
    predict_strength: Optional[float] = None


class HpcTrialChartDataResponse(BaseModel):
    """强度关系图所需的图表数据与坐标范围。"""
    min_bw: float
    max_bw: float
    range_bw: float
    min_strength: float
    max_strength: float
    range_strength: float
    bw_ratios: list[float]
    strengths: list[float]


class HpcTrialResponse(BaseModel):
    """高性能试配统一计算响应。"""
    base_wb: float
    base_bs: float
    base_alpha: float
    workability_result: HpcTrialWorkabilityResultResponse
    trial_materials: list[HpcTrialMaterialRowResponse]
    strength_mixes: list[HpcTrialStrengthMixResponse]
    strength_regression: Optional[HpcTrialStrengthRegressionResponse] = None
    chart_data: Optional[HpcTrialChartDataResponse] = None
    adapt_result: HpcTrialMaterialResultResponse
    calculated_density: Optional[float] = None
    density_correction_factor: Optional[float] = None
    lab_mix: HpcTrialMaterialResultResponse


# ── UHPC Trial ──────────────────────────────────────────────────────────────

class UhpcTrialRequest(BaseModel):
    """超高性能试配统一计算请求。"""
    wb: float = Field(..., gt=0)
    sb: float = Field(..., gt=0)
    alpha: float = Field(..., ge=0, le=100)
    sf_mass: float = Field(0, ge=0)
    total: float = Field(..., gt=0)
    cement_pct: float = Field(..., ge=0, le=100)
    fly_ash_pct: float = Field(0, ge=0, le=100)
    micro_bead_pct: float = Field(0, ge=0, le=100)
    silica_fume_pct: float = Field(0, ge=0, le=100)
    design_strength: float = Field(..., gt=0)

    # Tab 1 – 试拌调整
    adjusted_sb: Optional[float] = Field(default=None, gt=0)
    adjusted_alpha: Optional[float] = Field(default=None, ge=0, le=100)

    # Tab 2 – 强度实测
    s_wb_0: Optional[float] = Field(default=None, ge=0)
    s_wb_plus: Optional[float] = Field(default=None, ge=0)
    s_wb_minus: Optional[float] = Field(default=None, ge=0)
    s_sf_plus: Optional[float] = Field(default=None, ge=0)
    s_sf_minus: Optional[float] = Field(default=None, ge=0)

    # 变体外加剂手动调整 (kg/m³)
    a_wb_plus: Optional[float] = Field(default=None, ge=0)
    a_wb_minus: Optional[float] = Field(default=None, ge=0)
    a_sf_plus: Optional[float] = Field(default=None, ge=0)
    a_sf_minus: Optional[float] = Field(default=None, ge=0)

    # Tab 3 – 校正
    corr_base: str = Field(default='trial', pattern=r'^(trial|wbRec|sfRec)$')
    measured_density: Optional[float] = Field(default=None, gt=0)


class UhpcTrialMixRowResponse(BaseModel):
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
    admixture_pct: Optional[float] = None


class UhpcTrialResponse(BaseModel):
    design_strength: float
    trial_sb: float
    trial_alpha: float
    # Tab 1
    trial_mix: UhpcTrialMixRowResponse
    # Tab 2
    variant_wb_plus: UhpcTrialMixRowResponse
    variant_wb_minus: UhpcTrialMixRowResponse
    variant_sf_plus: UhpcTrialMixRowResponse
    variant_sf_minus: UhpcTrialMixRowResponse
    rec_wb: Optional[float] = None
    rec_sf: Optional[float] = None
    # Tab 3
    corr_base: str
    corr_mix: UhpcTrialMixRowResponse
    calc_density: Optional[float] = None
    corr_factor: Optional[float] = None
    needs_corr: bool = False
    lab_mix: UhpcTrialMixRowResponse


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)

class TokenResponse(BaseModel):
    access_token: str; token_type: str; username: str
    is_admin: bool = False; must_reset: bool = False

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=100)

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: str = Field(default='', max_length=100)
    phone: str = Field(default='', max_length=30)
    is_admin: bool = False

class ProfileUpdateRequest(BaseModel):
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=4, max_length=100)

class UserResponse(BaseModel):
    id: int; username: str; email: str = ''; phone: str = ''
    is_admin: bool; must_reset: bool; created_at: str

class RecordSaveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: Optional[int] = Field(default=None, gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default='hpc', pattern=r'^(hpc|uhpc)$')
    project_id: Optional[int] = Field(default=None, gt=0)
    record_data: Optional[dict[str, Any]] = None

class RecordResponse(BaseModel):
    id: int; name: str; category: str = 'hpc'; created_by: str; created_at: str
    project_id: Optional[int]=None
    record_data: dict[str, Any] = Field(default_factory=dict)

class ProjectCreateRequest(BaseModel):
    project_code: str = Field(..., min_length=1, max_length=50)
    project_name: str = Field(..., min_length=1, max_length=200)
    requirements: str = Field(default='', max_length=2000)

class ProjectUpdateRequest(BaseModel):
    project_code: Optional[str] = Field(default=None, max_length=50)
    project_name: Optional[str] = Field(default=None, max_length=200)
    requirements: Optional[str] = Field(default=None, max_length=2000)

class ProjectResponse(BaseModel):
    id: int; project_code: str; project_name: str; requirements: str = ''
    created_by: str; created_at: str; updated_at: str; record_count: int = 0


class RecycleBinItemResponse(BaseModel):
    item_type: Literal['project', 'record']
    id: int
    name: str
    category: Optional[str] = None
    project_code: str = ''
    project_name: str = ''
    project_id: Optional[int] = None
    created_by: str
    created_at: str
    deleted_at: Optional[str] = None
    deleted_by: str = ''
    deleted_with_project: bool = False


class ClientLogRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    source: str = Field(default='frontend', min_length=1, max_length=50)
    event: Optional[str] = Field(default=None, max_length=100)
    message: str = Field(..., min_length=1, max_length=4000)
    route: Optional[str] = Field(default=None, max_length=500)
    url: Optional[str] = Field(default=None, max_length=1000)
    session_id: Optional[str] = Field(default=None, max_length=100)
    request_id: Optional[str] = Field(default=None, max_length=100)
    user_agent: Optional[str] = Field(default=None, max_length=1000)
    created_at: Optional[str] = Field(default=None, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
