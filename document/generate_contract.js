/**
 * 生成项目合同 DOCX
 * 运行: node document/generate_contract.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak,
} = require("docx");

const OUT_DIR = path.resolve(__dirname, "..");
const OUTPUT = path.join(OUT_DIR, "document", "项目合同_水泥配比计算系统.docx");

// ── 样式 ──
const DARK_BLUE = "1E3C72";
const MID_BLUE = "2A5298";
const LIGHT_BLUE = "E8F0FB";
const WHITE = "FFFFFF";
const GRAY = "888888";

const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function p(text, opts = {}) {
  const { bold, size = 22, align, color, spacing, indent } = opts;
  const safeText = text || " ";
  const runs = Array.isArray(safeText)
    ? safeText.map(t => typeof t === "string" ? new TextRun({ text: t || " ", font: "微软雅黑", size, bold, color }) : new TextRun({ font: "微软雅黑", size, bold, color, ...t }))
    : [new TextRun({ text: safeText, font: "微软雅黑", size, bold, color })];
  return new Paragraph({
    alignment: align || AlignmentType.LEFT,
    spacing: spacing || { before: 60, after: 60 },
    indent,
    children: runs,
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    children: [new TextRun({ text, bold: true, size: 32, font: "微软雅黑", color: DARK_BLUE })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 100 },
    children: [new TextRun({ text, bold: true, size: 26, font: "微软雅黑", color: MID_BLUE })],
  });
}

function empty(n = 1) {
  return Array.from({ length: n }, () => p(" ", { spacing: { before: 40, after: 40 } }));
}

function hdrCell(text, w) {
  return new TableCell({
    borders, width: { size: w, type: WidthType.DXA },
    shading: { fill: DARK_BLUE, type: ShadingType.CLEAR },
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    children: [p(text, { bold: true, color: WHITE, size: 19, align: AlignmentType.CENTER })],
  });
}
function cell(text, w, opts = {}) {
  const cellOpts = {
    borders, width: { size: w, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [p(text || " ", { size: 19, align: opts.center ? AlignmentType.CENTER : undefined, bold: opts.bold, color: opts.color })],
  };
  if (opts.fill) {
    cellOpts.shading = { fill: opts.fill, type: ShadingType.CLEAR };
  }
  return new TableCell(cellOpts);
}
function tbl(colWidths, rows) {
  return new Table({
    width: { size: 9026, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: rows.map(r => new TableRow({ children: r })),
  });
}

// ═══════════════════════════════════════
// 封 面
// ═══════════════════════════════════════
function cover() {
  return [
    ...empty(6),
    p("项  目  合  同", { bold: true, size: 48, align: AlignmentType.CENTER, color: DARK_BLUE }),
    p(" ", { spacing: { after: 200 } }),
    p("水泥配比计算系统", { bold: true, size: 36, align: AlignmentType.CENTER, color: MID_BLUE }),
    p(" ", { spacing: { after: 300 } }),
    p("混凝土配合比设计与试配调整平台", { size: 24, align: AlignmentType.CENTER, color: GRAY }),
    p(" ", { spacing: { after: 400 } }),
    p(`合同编号：SC-2026-0602`, { size: 20, align: AlignmentType.CENTER, color: GRAY }),
    p(`签订日期：________ 年 ________ 月 ________ 日`, { size: 20, align: AlignmentType.CENTER, color: GRAY }),
    p(`签订地点：____________________`, { size: 20, align: AlignmentType.CENTER, color: GRAY }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ═══════════════════════════════════════
// 主 文 档
// ═══════════════════════════════════════
function mainBody() {
  const items = [];

  // ── 第一条 合同双方 ──
  items.push(h1("第一条  合同双方"));
  items.push(p(" "));
  items.push(tbl([2000, 7026], [
    [cell("甲方（委托方）", 2000, { bold: true, fill: LIGHT_BLUE }), cell("公司名称：________________________\n联系人：________________________\n联系电话：________________________\n电子邮箱：________________________", 7026)],
    [cell("乙方（开发方）", 2000, { bold: true, fill: LIGHT_BLUE }), cell("姓名/公司：________________________\n联系人：________________________\n联系电话：________________________\n电子邮箱：________________________", 7026)],
  ]));
  items.push(empty(2));

  // ── 第二条 项目概述 ──
  items.push(h1("第二条  项目概述"));
  items.push(p("2.1  项目名称：水泥配比计算系统（混凝土配合比设计与试配调整平台）"));
  items.push(p("2.2  项目定位：面向中国中车风电混塔项目的高性能混凝土（HPC）与超高性能混凝土（UHPC）配合比全流程数字化设计与试配调整系统。"));
  items.push(p("2.3  技术路线：前后端分离 Web 应用，前端基于 Vue 3 + Element Plus，后端基于 Python FastAPI + SQLite，支持 Windows/Linux 跨平台部署。"));
  items.push(empty(1));

  // ── 第三条 功能范围 ──
  items.push(h1("第三条  功能范围与交付清单"));
  items.push(p("乙方按照以下功能清单完成全部软件功能的设计、开发、测试与交付："));
  items.push(empty(1));

  const featureTable = [
    [hdrCell("序号", 500), hdrCell("功能模块", 1600), hdrCell("功能名称", 2200), hdrCell("功能说明", 4726)],
  ];
  const features = [
    ["1", "系统基础", "用户认证与鉴权", "JWT Token 登录认证，过期自动跳转；前端路由守卫 + 后端二次鉴权"],
    ["2", "系统基础", "角色与权限控制", "管理员/普通用户双角色，菜单级权限隔离，API 层二次校验"],
    ["3", "系统基础", "密码安全策略", "SHA-256 加盐哈希存储；首次登录强制提示改密；管理员可重置用户密码"],
    ["4", "首页总览", "首页仪表盘", "统计卡片(项目/HPC/UHPC/试配总数) + 快捷操作面板(5格) + 最近项目5条 + 最近记录10条"],
    ["5", "项目管理", "项目 CRUD", "项目列表分页搜索；新建/编辑/删除项目；软删除进入回收站"],
    ["6", "项目管理", "项目详情", "项目信息展示 + 关联配比记录表格(12列材料参数) + 新建/载入/删除记录"],
    ["7", "HPC 配比计算", "水胶比页签", "鲍罗米公式自动计算 fcu,0 和 W/B；fb 自动估算；试验数据文件上传回归拟合 αa/αb"],
    ["8", "HPC 配比计算", "砂率选取页签", "标准砂率参考表(强度等级×粒径)，行列交叉高亮推荐范围，手动输入确认"],
    ["9", "HPC 配比计算", "骨料用量页签", "体积法计算 mg/ms；Vg 参考表；粗细骨料密度输入"],
    ["10", "HPC 配比计算", "胶凝材料页签", "浆体体积法；4种掺合料(粉煤灰/矿粉/微珠/硅灰)质量分数与密度输入，计算各组分用量"],
    ["11", "HPC 配比计算", "水与外加剂页签", "mb×W/B 计算 mw；掺量百分比计算 ma；最终配比汇总表"],
    ["12", "UHPC 配比计算", "水胶比页签", "推荐强度等级-W/B 对照表，点击自动带入；外加剂默认值自动补入"],
    ["13", "UHPC 配比计算", "砂胶比与钢纤维", "砂胶比体积参数计算；钢纤维体积掺量与质量计算"],
    ["14", "UHPC 配比计算", "胶凝材料比例", "修正安德森模型粒径堆积计算(D10/D50/D90)；体积比例→质量比例→每方用量"],
    ["15", "HPC 试配调整", "工作性-强度-校正", "三阶段试配流程：Δmb/Δβs/Δα 调整→强度回归分析→表观密度校正→实验室配合比"],
    ["16", "UHPC 试配调整", "工作性-强度-校正", "三阶段试配：S/B与α调整→+Δ/-Δ试验组回归→三种基准校正→实验室配合比"],
    ["17", "计算书", "计算书生成", "项目选择→记录浏览→HTML计算书生成(项目信息+全部参数键值表)→浏览器打印/导出PDF"],
    ["18", "全部记录", "记录管理", "12列数据表格；按名称/项目搜索；按HPC/UHPC筛选；载入历史记录"],
    ["19", "回收站", "数据恢复与清空", "软删除数据管理；按类型筛选/搜索；项目-记录关联恢复；物理删除二次确认"],
    ["20", "用户管理", "用户 CRUD", "管理员专属；用户列表搜索；新增(默认密码)；密码重置；删除(管理员不可删)"],
    ["21", "个人中心", "资料与密码", "邮箱/手机号修改；原密码验证→新密码确认→自动退出重新登录"],
    ["22", "系统部署", "前后端打包部署", "Vite 生产构建+Nginx 部署；PyInstaller 后端打包为独立可执行文件；数据库自动初始化"],
    ["23", "系统部署", "数据库与日志", "SQLite 自动建表；默认管理员初始化；文件+控制台日志按日轮转"],
  ];
  let alt = false;
  for (const f of features) {
    const fill = alt ? LIGHT_BLUE : undefined;
    alt = !alt;
    featureTable.push([
      cell(f[0], 500, { center: true, fill }), cell(f[1], 1600, { fill }), cell(f[2], 2200, { bold: true, fill }), cell(f[3], 4726, { fill }),
    ]);
  }
  items.push(tbl([500, 1600, 2200, 4726], featureTable.map(r => r)));
  items.push(p("以上共计 23 项功能模块，覆盖全部业务场景。", { size: 20, color: GRAY, spacing: { before: 120 } }));
  items.push(empty(2));

  // ── 第四条 项目报价 ──
  items.push(h1("第四条  项目报价"));
  items.push(p("4.1  项目总报价：人民币 ________________ 元整（¥________________）。"));
  items.push(p("4.2  报价包含以下内容："));
  items.push(p("    （1）全部功能模块的设计、编码、联调与测试；"));
  items.push(p("    （2）前端生产构建与 Nginx 部署配置；"));
  items.push(p("    （3）后端 PyInstaller 打包与运行环境配置；"));
  items.push(p("    （4）数据库初始化与管理员账号预置；"));
  items.push(p("    （5）部署上线支持与基础使用培训；"));
  items.push(p("    （6）验收交付后 ________ 个月内的免费 Bug 修复与维护支持。"));
  items.push(p("4.3  报价不包含：服务器/域名/SSL证书等第三方资源费用、超出约定范围的定制开发。"));
  items.push(empty(1));

  // 费用明细表
  items.push(tbl([2000, 2400, 2400, 2226], [
    [hdrCell("费用项目", 2000), hdrCell("内容说明", 2400), hdrCell("金额（元）", 2400), hdrCell("备注", 2226)],
    [cell("软件开发费", 2000), cell("全部功能模块的设计、开发与测试", 2400), cell("____________", 2400, { center: true }), cell("核心交付", 2226)],
    [cell("部署实施费", 2000, { fill: LIGHT_BLUE }), cell("前端 Nginx 部署 + 后端打包 + 环境配置", 2400, { fill: LIGHT_BLUE }), cell("____________", 2400, { center: true, fill: LIGHT_BLUE }), cell("一次性", 2226, { fill: LIGHT_BLUE })],
    [cell("培训与文档费", 2000), cell("操作说明书 + 验收清单 + 使用培训", 2400), cell("____________", 2400, { center: true }), cell("交付物", 2226)],
    [cell("首年维护费", 2000, { fill: LIGHT_BLUE }), cell("Bug修复 + 小版本更新 + 技术支持", 2400, { fill: LIGHT_BLUE }), cell("____________", 2400, { center: true, fill: LIGHT_BLUE }), cell("每年", 2226, { fill: LIGHT_BLUE })],
    [cell("合计", 2000, { bold: true }), cell("", 2400), cell("____________", 2400, { center: true, bold: true, color: DARK_BLUE }), cell("含税", 2226)],
  ]));
  items.push(empty(2));

  // ── 第五条 开发周期 ──
  items.push(h1("第五条  开发周期与交付计划"));
  items.push(p("5.1  项目总工期：自合同签订之日起 ________ 个工作日。"));
  items.push(p("5.2  里程碑节点："));
  items.push(empty(1));
  items.push(tbl([3000, 3000, 3026], [
    [hdrCell("阶段", 3000), hdrCell("交付物", 3000), hdrCell("完成时间", 3026)],
    [cell("第一阶段：基础框架搭建", 3000), cell("登录认证、项目管理、数据库与API基础", 3000), cell("____年____月____日", 3026, { center: true })],
    [cell("第二阶段：核心计算模块", 3000, { fill: LIGHT_BLUE }), cell("HPC/UHPC配比计算与试配调整", 3000, { fill: LIGHT_BLUE }), cell("____年____月____日", 3026, { center: true, fill: LIGHT_BLUE })],
    [cell("第三阶段：辅助功能与联调", 3000), cell("计算书、回收站、用户管理、全部记录", 3000), cell("____年____月____日", 3026, { center: true })],
    [cell("第四阶段：部署上线与验收", 3000, { fill: LIGHT_BLUE }), cell("生产构建、部署配置、验收测试、文档交付", 3000, { fill: LIGHT_BLUE }), cell("____年____月____日", 3026, { center: true, fill: LIGHT_BLUE })],
  ]));
  items.push(empty(2));

  // ── 第六条 部署与交付 ──
  items.push(h1("第六条  部署与交付"));
  items.push(p("6.1  乙方负责完成以下部署工作："));
  items.push(p("    （1）前端资源构建（npm run build:prod）并部署至甲方指定的 Nginx 服务器；"));
  items.push(p("    （2）后端使用 PyInstaller 打包为独立可执行文件，配置为系统服务或开机自启；"));
  items.push(p("    （3）数据库首次启动自动初始化，创建全部表结构及默认管理员账号；"));
  items.push(p("    （4）配置 Nginx 反向代理规则，实现前后端统一入口与 API 代理。"));
  items.push(p("6.2  交付物清单："));
  items.push(p("    （1）前端构建产物（dist 目录）；"));
  items.push(p("    （2）后端可执行文件（main）及配置文件；"));
  items.push(p("    （3）《软件操作说明书》一份（电子版）；"));
  items.push(p("    （4）《功能清单及验收清单》一份（电子版）；"));
  items.push(p("    （5）本项目合同一份。"));
  items.push(empty(1));

  // ── 第七条 维护与技术支持 ──
  items.push(h1("第七条  维护与技术支持"));
  items.push(p("7.1  免费维护期：自项目验收合格之日起 ________ 个月。"));
  items.push(p("7.2  免费维护期内，乙方提供以下服务："));
  items.push(p("    （1）修复影响正常使用的程序 Bug（乙方在收到通知后 ________ 个工作日内响应）；"));
  items.push(p("    （2）提供远程技术支持（电话/即时通讯/远程桌面）；"));
  items.push(p("    （3）因操作系统或浏览器大版本升级导致的兼容性问题修复。"));
  items.push(p("7.3  免费维护期后，双方可另行签订年度维护合同。"));
  items.push(p("7.4  以下情况不在免费维护范围内："));
  items.push(p("    （1）甲方自行修改代码或数据库导致的故障；"));
  items.push(p("    （2）超出原定功能范围的新需求开发；"));
  items.push(p("    （3）因硬件故障、网络攻击等不可抗力导致的问题。"));
  items.push(empty(1));

  // ── 第八条 付款方式 ──
  items.push(h1("第八条  付款方式"));
  items.push(empty(1));
  items.push(tbl([3000, 3000, 3026], [
    [hdrCell("付款节点", 3000), hdrCell("付款比例", 3000), hdrCell("金额（元）", 3026)],
    [cell("合同签订后 5 个工作日内（预付款）", 3000), cell("____%", 3000, { center: true }), cell("____________", 3026, { center: true })],
    [cell("核心功能开发完成并演示通过", 3000, { fill: LIGHT_BLUE }), cell("____%", 3000, { center: true, fill: LIGHT_BLUE }), cell("____________", 3026, { center: true, fill: LIGHT_BLUE })],
    [cell("全部功能验收合格后 5 个工作日内", 3000), cell("____%", 3000, { center: true }), cell("____________", 3026, { center: true })],
  ]));
  items.push(p("甲方通过银行转账方式支付至乙方指定账户。", { size: 20, color: GRAY, spacing: { before: 120 } }));
  items.push(empty(2));

  // ── 第九条 验收 ──
  items.push(h1("第九条  验收标准与方式"));
  items.push(p("9.1  验收依据：本合同第三条所列功能清单及双方确认的《功能清单及验收清单》。"));
  items.push(p("9.2  验收方式：甲方逐项测试全部 46 项验收指标，填写验收结论并签字确认。"));
  items.push(p("9.3  验收不合格的处理：如部分功能不符合约定，乙方应在 ________ 个工作日内完成整改并提请复验。"));
  items.push(p("9.4  验收合格后，双方签署《项目验收确认书》，进入免费维护期。"));
  items.push(empty(1));

  // ── 第十条 知识产权 ──
  items.push(h1("第十条  知识产权"));
  items.push(p("10.1  本项目产生的全部源代码、文档、设计成果的知识产权归双方协商确定（□ 甲方所有 / □ 乙方所有 / □ 双方共有）。"));
  items.push(p("10.2  乙方保证所使用的第三方库和工具均为开源或已获得合法授权，不侵犯第三方知识产权。"));
  items.push(empty(1));

  // ── 第十一条 违约责任 ──
  items.push(h1("第十一条  违约责任"));
  items.push(p("11.1  任何一方违反本合同约定，应承担相应的违约责任，并赔偿对方因此遭受的直接经济损失。"));
  items.push(p("11.2  因不可抗力导致合同无法履行的，双方互不承担违约责任。"));
  items.push(empty(1));

  // ── 第十二条 其他 ──
  items.push(h1("第十二条  其他约定"));
  items.push(p("12.1  本合同一式两份，甲乙双方各执一份，具有同等法律效力。"));
  items.push(p("12.2  本合同未尽事宜，由双方协商后签订补充协议。"));
  items.push(p("12.3  本合同自双方签字（或盖章）之日起生效。"));
  items.push(empty(4));

  // ── 签章区 ──
  items.push(tbl([4513, 4513], [
    [
      cell("甲方（委托方）签字/盖章：\n\n\n\n\n日期：________ 年 ________ 月 ________ 日", 4513),
      cell("乙方（开发方）签字/盖章：\n\n\n\n\n日期：________ 年 ________ 月 ________ 日", 4513),
    ],
  ]));

  return items;
}

// ═══════════════════════════════════════
// 生成 DOCX
// ═══════════════════════════════════════
async function main() {
  const doc = new Document({
    styles: {
      default: { document: { run: { font: "微软雅黑", size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 32, bold: true, font: "微软雅黑", color: DARK_BLUE },
          paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 26, bold: true, font: "微软雅黑", color: MID_BLUE },
          paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4
          margin: { top: 1200, right: 1440, bottom: 1200, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: MID_BLUE, space: 1 } },
            children: [new TextRun({ text: "项目合同 · 水泥配比计算系统", font: "微软雅黑", size: 16, color: GRAY })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            border: { top: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC", space: 1 } },
            children: [
              new TextRun({ text: "— ", font: "微软雅黑", size: 16, color: "AAAAAA" }),
              new TextRun({ children: [PageNumber.CURRENT], font: "微软雅黑", size: 16, color: "AAAAAA" }),
              new TextRun({ text: " —", font: "微软雅黑", size: 16, color: "AAAAAA" }),
            ],
          })],
        }),
      },
      children: [...cover(), ...mainBody()],
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(OUTPUT, buffer);
  console.log(`✅ 合同已生成: ${OUTPUT}`);
  console.log(`   文件大小: ${(buffer.length / 1024).toFixed(1)} KB`);
}

main();
