/**
 * calc/index.ts
 * =============
 * 集中式前端计算引擎统一出口。
 *
 * 本目录将原后端 services/ 中的全部计算逻辑迁移到前端，按业务模块拆分，
 * 保持与服务端逐字段一致的口径与舍入。页面/Store 只需从这里同步调用，
 * 不再依赖服务端计算接口（服务端仅用于数据持久化）。
 *
 * 计算顺序（HPC 主流程）：
 *   水胶比 -> 砂率确认 -> 骨料 -> 胶凝材料 -> 水与外加剂
 *   -> 试配(工作性 -> 强度实验 -> 配合比校正/适配 -> 实验室配合比)
 */
export * from './rounding'
export * from './waterBinder'
export * from './aggregate'
export * from './binder'
export * from './waterAdmixture'
export * from './regression'
export * from './adapt'
export * from './hpcTrial'
export * from './uhpc'
export * from './uhpcTrial'
