/**
 * 生成个人项目技术服务合同 DOCX
 * 运行: node document/generate_personal_contract.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, LevelFormat
} = require("docx");

const OUT_DIR = path.dirname(__filename);
const OUTPUT = path.join(OUT_DIR, "个人项目技术服务合同_水泥配比计算系统.docx");

// ── 常量 ──
const DARK_BLUE = "1E3C72";
const MID_BLUE = "2A5298";
const LIGHT_BLUE = "E8F0FB";
const GRAY = "888888";
const BORDER_GRAY = "CCCCCC";
const WHITE = "FFFFFF";
const DXA_PER_CM = 567; // 约 567 DXA = 1 cm

// A4: 21cm × 29.7cm
const PAGE_WIDTH = 21 * DXA_PER_CM;   // 11907
const PAGE_HEIGHT = 29.7 * DXA_PER_CM; // 16839
const MARGIN_TOP = 2 * DXA_PER_CM;
const MARGIN_BOTTOM = 2 * DXA_PER_CM;
const MARGIN_LEFT = 2.54 * DXA_PER_CM;
const MARGIN_RIGHT = 2.54 * DXA_PER_CM;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT;

// ── 工具函数 ──
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: BORDER_GRAY };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function p(text, options = {}) {
  const { bold = false, size = 21, align = AlignmentType.LEFT, color = "333333",
    spacing = { before: 60, after: 60 }, indent = undefined } = options;
  return new Paragraph({
    alignment: align,
    spacing,
    indent,
    children: [
      new TextRun({ text, bold, size, color, font: { name: "微软雅黑", eastAsia: "微软雅黑" } })
    ]
  });
}

function bulletP(text, options = {}) {
  const { size = 21, indentLeft = 720, hanging = 360 } = options;
  return new Paragraph({
    spacing: { before: 40, after: 40 },
    indent: { left: indentLeft, hanging },
    children: [
      new TextRun({ text: "● ", size: 16, color: DARK_BLUE, font: { name: "微软雅黑" } }),
      new TextRun({ text, size, color: "333333", font: { name: "微软雅黑", eastAsia: "微软雅黑" } })
    ]
  });
}

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 300, after: 160 },
    children: [new TextRun({ text, bold: true, size: 32, color: DARK_BLUE, font: { name: "微软雅黑", eastAsia: "微软雅黑" } })]
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, bold: true, size: 26, color: MID_BLUE, font: { name: "微软雅黑", eastAsia: "微软雅黑" } })]
  });
}

function emptyP(count = 1) {
  return Array.from({ length: count }, () =>
    new Paragraph({ spacing: { before: 30, after: 30 }, children: [] })
  );
}

function pageBreak() {
  return new Paragraph({ children: [new TextRun({ break: 1 })] });
}

function divider() {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: LIGHT_BLUE, space: 1 } },
    children: []
  });
}

function cell(text, options = {}) {
  const {
    bold = false, size = 18, align = AlignmentType.LEFT, color = "333333",
    fill = undefined, colSpan = 1, rowSpan = undefined
  } = options;
  const cellOpts = {
    borders: cellBorders,
    width: { size: 0, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [
      new Paragraph({
        alignment: align,
        children: [
          new TextRun({ text, bold, size, color, font: { name: "微软雅黑", eastAsia: "微软雅黑" } })
        ]
      })
    ]
  };
  if (fill) cellOpts.shading = { fill, type: ShadingType.CLEAR };
  if (colSpan > 1) cellOpts.columnSpan = colSpan;
  if (rowSpan) cellOpts.rowSpan = rowSpan;
  return new TableCell(cellOpts);
}

function multiLineCell(lines, options = {}) {
  const {
    bold = false, size = 18, align = AlignmentType.LEFT, color = "333333",
    fill = undefined, colSpan = 1
  } = options;
  const cellOpts = {
    borders: cellBorders,
    width: { size: 0, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: lines.map(line =>
      new Paragraph({
        alignment: align,
        spacing: { before: 20, after: 20 },
        children: [
          new TextRun({ text: line, bold, size, color, font: { name: "微软雅黑", eastAsia: "微软雅黑" } })
        ]
      })
    )
  };
  if (fill) cellOpts.shading = { fill, type: ShadingType.CLEAR };
  if (colSpan > 1) cellOpts.columnSpan = colSpan;
  return new TableCell(cellOpts);
}

// ═══════════════════════════════════════
// 文档内容
// ═══════════════════════════════════════

// ── 封面 ──
const coverChildren = [
  ...emptyP(10),
  p("个人项目技术服务合同", { bold: true, size: 40, align: AlignmentType.CENTER, color: DARK_BLUE, spacing: { before: 60, after: 200 } }),
  p("水泥配比计算系统", { bold: true, size: 32, align: AlignmentType.CENTER, color: MID_BLUE, spacing: { before: 60, after: 200 } }),
  p("混凝土配合比设计与试配调整平台", { size: 22, align: AlignmentType.CENTER, color: GRAY, spacing: { before: 60, after: 300 } }),
  divider(),
  p("合同编号：SC-P-2026-0604", { size: 20, align: AlignmentType.CENTER, color: GRAY, spacing: { before: 200, after: 100 } }),
  p("签订日期：________ 年 ________ 月 ________ 日", { size: 20, align: AlignmentType.CENTER, color: GRAY, spacing: { before: 60, after: 100 } }),
  p("签订地点：____________________", { size: 20, align: AlignmentType.CENTER, color: GRAY, spacing: { before: 60, after: 80 } }),
  pageBreak(),
];

// ── 第一条 合同双方 ──
const article1 = [
  heading1("第一条  合同双方"),
  p("本合同由以下双方在平等自愿、协商一致的基础上签订："),
  emptyP(),
  new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH * 0.18, CONTENT_WIDTH * 0.82],
    rows: [
      new TableRow({
        children: [
          cell("甲方（委托方）", { bold: true, fill: LIGHT_BLUE, align: AlignmentType.CENTER }),
          multiLineCell([
            "姓    名：________________________",
            "身份证号：________________________",
            "联系电话：________________________",
            "电子邮箱：________________________",
            "通讯地址：________________________",
          ])
        ]
      }),
      new TableRow({
        children: [
          cell("乙方（开发方）", { bold: true, fill: LIGHT_BLUE, align: AlignmentType.CENTER }),
          multiLineCell([
            "姓    名：________________________",
            "身份证号：________________________",
            "联系电话：________________________",
            "电子邮箱：________________________",
            "通讯地址：________________________",
          ])
        ]
      }),
    ]
  }),
  emptyP(),
  p("双方确认上述信息真实有效，并作为合同履行期间的送达地址。如一方信息变更，应在 3 日内书面通知另一方。", { size: 18, color: GRAY }),
  emptyP(),
];

// ── 第二条 项目概述 ──
const article2 = [
  heading1("第二条  项目概述"),
  heading2("2.1  项目名称"),
  p("水泥配比计算系统（混凝土配合比设计与试配调整平台）。"),
  heading2("2.2  项目定位"),
  p("面向混凝土行业的配合比全流程数字化计算与试配调整工具，支持高性能混凝土（HPC）与超高性能混凝土（UHPC）的配合比设计与优化。"),
  heading2("2.3  技术方案"),
  p("采用前后端分离架构，前端基于 Vue 3 + Element Plus，后端基于 Python FastAPI + SQLite 数据库，支持 Windows / Linux 跨平台部署，并提供 Web 版与桌面版（Electron）两种交付形态。"),
  heading2("2.4  项目现状"),
  p("本项目已完成核心功能开发，当前处于功能完善与部署交付阶段。本合同约定范围为：现有功能的交付部署、使用培训、免费维护期内的技术支持与 Bug 修复。"),
  emptyP(),
];

// ── 第三条 服务内容与交付清单 ──
const featureData = [
  ["系统基础", "用户认证与鉴权、角色权限控制、密码安全策略"],
  ["首页仪表盘", "统计卡片、快捷操作面板、最近项目/记录展示"],
  ["项目管理", "项目 CRUD、项目详情、关联配比记录管理、软删除回收站"],
  ["HPC 配比计算", "水胶比（鲍罗米公式）、砂率选取、骨料用量（体积法）、胶凝材料（浆体体积法）、水与外加剂"],
  ["UHPC 配比计算", "水胶比、砂胶比与钢纤维、胶凝材料比例（修正安德森模型）"],
  ["HPC 试配调整", "工作性调整→强度回归分析→表观密度校正→实验室配合比"],
  ["UHPC 试配调整", "工作性调整→强度回归→基准校正→实验室配合比"],
  ["计算书", "项目选择→记录浏览→HTML 计算书→浏览器打印/导出 PDF"],
  ["全部记录", "12 列数据表格、名称/项目搜索、HPC/UHPC 筛选、历史载入"],
  ["用户管理", "管理员专属：用户 CRUD、密码重置"],
  ["个人中心", "个人资料修改、密码修改（原密码验证）"],
  ["系统部署", "Web 版（Nginx 部署）、桌面版（Electron 壳 + 后端守护进程）、数据库自动初始化"],
];

const featureRows = featureData.map((f, i) => {
  const fill = i % 2 === 0 ? undefined : LIGHT_BLUE;
  return new TableRow({
    children: [
      cell(String(i + 1), { align: AlignmentType.CENTER, fill }),
      cell(f[0], { bold: true, fill }),
      cell(f[1], { fill }),
    ]
  });
});

const article3 = [
  heading1("第三条  服务内容与交付清单"),
  p("乙方按照以下功能清单完成系统的交付、部署与培训服务："),
  emptyP(),
  new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH * 0.08, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.70],
    rows: [
      new TableRow({
        children: [
          cell("序号", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("功能模块", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("功能说明", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
        ]
      }),
      ...featureRows,
    ]
  }),
  emptyP(),
  p("以上共计 12 项功能模块。乙方确保各项功能正常运行并满足甲方使用需求。", { size: 18, color: GRAY }),
  emptyP(),
];

// ── 第四条 交付物 ──
const article4 = [
  heading1("第四条  交付物清单"),
  emptyP(),
  new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH * 0.08, CONTENT_WIDTH * 0.46, CONTENT_WIDTH * 0.23, CONTENT_WIDTH * 0.23],
    rows: [
      new TableRow({
        children: [
          cell("序号", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("交付物名称", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("交付形式", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("交付时间", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
        ]
      }),
      ...[
        ["1", "Web 版部署包（前端 dist + 后端可执行文件 + Nginx 配置）", "电子文件", "____年____月____日"],
        ["2", "桌面版安装包（Windows/Linux）", "安装程序", "____年____月____日"],
        ["3", "《软件操作说明书》", "电子版（PDF）", "____年____月____日"],
        ["4", "《功能验证清单》", "电子版（PDF）", "____年____月____日"],
        ["5", "源代码（如有约定）", "电子文件", "____年____月____日"],
        ["6", "本合同", "纸质/电子各一份", "签订当日"],
      ].map((item, i) => new TableRow({
        children: [
          cell(item[0], { align: AlignmentType.CENTER, fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
          cell(item[1], { fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
          cell(item[2], { align: AlignmentType.CENTER, fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
          cell(item[3], { align: AlignmentType.CENTER, fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
        ]
      }))
    ]
  }),
  emptyP(),
];

// ── 第五条 费用与付款 ──
const article5 = [
  heading1("第五条  费用与付款方式"),
  heading2("5.1  项目总费用"),
  p("本项目总费用为人民币 ________________ 元整（¥_______________）。"),
  p("费用包含：系统交付部署、使用培训、操作手册编写、免费维护期内的技术支持与 Bug 修复。"),
  p("费用不包含：服务器/域名/SSL 证书等第三方资源费用、超出本合同约定范围的定制开发。"),
  heading2("5.2  付款计划"),
  emptyP(),
  new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH * 0.45, CONTENT_WIDTH * 0.2, CONTENT_WIDTH * 0.35],
    rows: [
      new TableRow({
        children: [
          cell("付款节点", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("比例", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
          cell("金额（元）", { bold: true, align: AlignmentType.CENTER, color: WHITE, fill: DARK_BLUE }),
        ]
      }),
      ...[
        ["合同签订后 3 个工作日内（预付款）", "____%", "_______________"],
        ["系统部署完成并通过验收后 5 个工作日内", "____%", "_______________"],
      ].map((item, i) => new TableRow({
        children: [
          cell(item[0], { fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
          cell(item[1], { align: AlignmentType.CENTER, fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
          cell(item[2], { align: AlignmentType.CENTER, fill: i % 2 === 0 ? undefined : LIGHT_BLUE }),
        ]
      }))
    ]
  }),
  emptyP(),
  p("甲方应通过银行转账方式支付至乙方指定账户。乙方收款账户信息以书面（含电子邮件）形式单独提供。", { size: 18, color: GRAY }),
  emptyP(),
];

// ── 第六条 开发与交付周期 ──
const article6 = [
  heading1("第六条  开发与交付周期"),
  p("6.1  本合同签订后，乙方应在 ________ 个工作日内完成系统部署、功能验证、使用培训及全部交付物的移交。"),
  p("6.2  如因甲方原因（如未能及时提供服务器环境、未能及时安排验收等）导致交付延迟的，相应顺延。"),
  p("6.3  如遇不可抗力（自然灾害、政策变化、重大疫情等），双方协商调整交付时间。"),
  emptyP(),
];

// ── 第七条 验收标准 ──
const article7 = [
  heading1("第七条  验收标准与方式"),
  p("7.1  验收依据：本合同第三条所列功能清单及双方确认的《功能验证清单》。"),
  p("7.2  验收方式："),
  bulletP("甲方在乙方部署完成后 5 个工作日内，依据功能清单逐项进行验收测试；"),
  bulletP("甲方填写验收结论并签字（或电子邮件）确认；"),
  bulletP("如发现功能缺陷，乙方应在 ________ 个工作日内完成修复并提请复验。"),
  p("7.3  验收合格后，双方确认《项目验收确认书》，系统进入免费维护期。"),
  p("7.4  甲方无正当理由在部署完成后超过 15 个工作日未组织验收或未提出书面异议的，视为验收通过。", { size: 18, color: GRAY }),
  emptyP(),
];

// ── 第八条 维护与技术支持 ──
const article8 = [
  heading1("第八条  维护与技术支持"),
  p("8.1  免费维护期：自项目验收合格之日起 ________ 个月。"),
  p("8.2  免费维护期内，乙方提供以下服务："),
  bulletP("修复影响正常使用的程序 Bug（乙方在收到通知后 ________ 个工作日内响应）；"),
  bulletP("提供远程技术支持（电话/微信/远程桌面/邮件等）；"),
  bulletP("因操作系统或浏览器大版本升级导致的兼容性问题修复。"),
  p("8.3  免费维护期后，双方可协商签订年度维护合同，年维护费不超过项目总费用的 15%。"),
  p("8.4  以下情况不在免费维护范围内："),
  bulletP("甲方或第三方自行修改源代码、数据库导致的故障；"),
  bulletP("超出原定功能范围的新需求开发；"),
  bulletP("因硬件故障、网络攻击、病毒等不可抗力导致的问题。"),
  emptyP(),
];

// ── 第九条 知识产权 ──
const article9 = [
  heading1("第九条  知识产权"),
  p("9.1  本项目产生的全部源代码及文档的知识产权归属，双方约定如下（勾选一项）："),
  p("    □ 甲方享有全部知识产权，乙方向甲方完整交付全部源代码；"),
  p("    □ 乙方保留知识产权，甲方享有本项目的永久使用权和复制权；"),
  p("    □ 双方共有知识产权，具体权利划分另行约定。"),
  p("9.2  无论知识产权如何归属，乙方均有权在个人作品集中展示本项目（不得泄露甲方商业秘密）。"),
  p("9.3  乙方保证所使用的第三方库和工具均为开源或已获得合法授权，不侵犯第三方知识产权。"),
  emptyP(),
];

// ── 第十条 保密条款 ──
const article10 = [
  heading1("第十条  保密条款"),
  p("10.1  双方应对在合同履行过程中知悉的对方商业秘密、技术秘密及非公开信息承担保密义务。"),
  p("10.2  保密义务不因合同履行完毕或终止而失效，保密期限为合同终止后 ________ 年。"),
  p("10.3  任何一方违反保密义务给对方造成损失的，应承担赔偿责任。"),
  emptyP(),
];

// ── 第十一条 违约责任 ──
const article11 = [
  heading1("第十一条  违约责任"),
  p("11.1  任何一方违反本合同约定，应承担相应的违约责任，并赔偿对方因此遭受的直接经济损失。"),
  p("11.2  因不可抗力导致合同无法履行的，双方互不承担违约责任，但应及时通知对方并协商后续处理方案。"),
  p("11.3  如甲方逾期支付款项，每逾期一日应按未付款项的 0.05% 向乙方支付违约金。"),
  p("11.4  如乙方逾期交付，每逾期一日应按项目总费用的 0.05% 向甲方支付违约金，但违约金总额不超过项目总费用的 10%。"),
  emptyP(),
];

// ── 第十二条 争议解决 ──
const article12 = [
  heading1("第十二条  争议解决"),
  p("12.1  本合同在履行过程中如发生争议，双方应首先友好协商解决。"),
  p("12.2  协商不成的，任何一方可向乙方住所地有管辖权的人民法院提起诉讼。"),
  emptyP(),
];

// ── 第十三条 其他约定 ──
const article13 = [
  heading1("第十三条  其他约定"),
  p("13.1  本合同一式两份，甲乙双方各执一份，具有同等法律效力。"),
  p("13.2  本合同未尽事宜，由双方协商后签订补充协议，补充协议与本合同具有同等法律效力。"),
  p("13.3  本合同自双方签字之日起生效。"),
  emptyP(6),
];

// ── 签章区 ──
const signatureSection = [
  divider(),
  new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
    rows: [
      new TableRow({
        children: [
          multiLineCell([
            "甲方（委托方）",
            "",
            "签字：________________________",
            "",
            "日期：________ 年 ________ 月 ________ 日",
          ], { align: AlignmentType.CENTER }),
          multiLineCell([
            "乙方（开发方）",
            "",
            "签字：________________________",
            "",
            "日期：________ 年 ________ 月 ________ 日",
          ], { align: AlignmentType.CENTER }),
        ]
      }),
    ]
  }),
];

// ═══════════════════════════════════════
// 组装文档
// ═══════════════════════════════════════

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: { name: "微软雅黑", eastAsia: "微软雅黑" }, size: 21, color: "333333" }
      }
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: DARK_BLUE, font: { name: "微软雅黑", eastAsia: "微软雅黑" } },
        paragraph: { spacing: { before: 300, after: 160 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: MID_BLUE, font: { name: "微软雅黑", eastAsia: "微软雅黑" } },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 }
      },
    ]
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_WIDTH, height: PAGE_HEIGHT },
          margin: { top: MARGIN_TOP, bottom: MARGIN_BOTTOM, left: MARGIN_LEFT, right: MARGIN_RIGHT }
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: MID_BLUE, space: 1 } },
              children: [
                new TextRun({ text: "个人项目技术服务合同 · 水泥配比计算系统", size: 15, color: GRAY, font: { name: "微软雅黑", eastAsia: "微软雅黑" } })
              ]
            })
          ]
        })
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              border: { top: { style: BorderStyle.SINGLE, size: 2, color: BORDER_GRAY, space: 1 } },
              children: [
                new TextRun({ text: "— ", size: 15, color: GRAY }),
                new TextRun({ children: [PageNumber.CURRENT], size: 15, color: GRAY }),
                new TextRun({ text: " —", size: 15, color: GRAY }),
              ]
            })
          ]
        })
      },
      children: [
        ...coverChildren,
        ...article1,
        ...article2,
        ...article3,
        ...article4,
        ...article5,
        ...article6,
        ...article7,
        ...article8,
        ...article9,
        ...article10,
        ...article11,
        ...article12,
        ...article13,
        ...signatureSection,
      ]
    }
  ]
});

// ── 生成文件 ──
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT, buffer);
  console.log(`✅ 合同已生成: ${OUTPUT}`);
  console.log(`   文件大小: ${(fs.statSync(OUTPUT).size / 1024).toFixed(1)} KB`);
}).catch(err => {
  console.error("❌ 生成失败:", err.message);
  process.exit(1);
});
