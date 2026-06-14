/**
 * 将《软件操作说明书》Markdown 转换为 DOCX
 * 运行方式：node document/convert_to_docx.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat, ImageRun,
  TableOfContents,
} = require("docx");

// ── 路径 ──
const ROOT = path.resolve(__dirname, "..");
const MD_PATH = path.join(
  ROOT,
  "document",
  "软件操作说明书_v2_2026-06-02.md",
);
const SCREENSHOTS_DIR = path.join(ROOT, "document", "manual_screenshots");
const OUTPUT_PATH = path.join(
  ROOT,
  "document",
  "软件操作说明书_v2_2026-06-02.docx",
);

// ── 工具函数 ──
function p(content, options = {}) {
  const { bold, size = 22, alignment, spacing, indent, color } = options;
  const runs = [];
  if (typeof content === "string") {
    runs.push(
      new TextRun({ text: content, bold, size, font: "微软雅黑", color }),
    );
  } else if (Array.isArray(content)) {
    content.forEach((r) => {
      if (typeof r === "string") {
        runs.push(new TextRun({ text: r, font: "微软雅黑", size, ...options }));
      } else {
        runs.push(
          new TextRun({
            font: "微软雅黑",
            size,
            ...options,
            ...r,
          }),
        );
      }
    });
  }
  return new Paragraph({
    alignment: alignment || AlignmentType.LEFT,
    spacing: spacing || { before: 60, after: 60 },
    indent,
    children: runs,
  });
}

function heading(text, level) {
  const sizes = { 1: 36, 2: 30, 3: 26, 4: 24 };
  return new Paragraph({
    heading: level === 1
      ? HeadingLevel.HEADING_1
      : level === 2
      ? HeadingLevel.HEADING_2
      : level === 3
      ? HeadingLevel.HEADING_3
      : HeadingLevel.HEADING_4,
    spacing: { before: level <= 2 ? 360 : 240, after: 120 },
    children: [
      new TextRun({
        text,
        bold: true,
        size: sizes[level] || 24,
        font: "微软雅黑",
      }),
    ],
  });
}

function bullet(text, options = {}) {
  return p(`•  ${text}`, {
    indent: { left: 720, hanging: 360 },
    ...options,
  });
}

function numberBullet(num, text, options = {}) {
  return p(`${num}.  ${text}`, {
    indent: { left: 720, hanging: 360 },
    ...options,
  });
}

function imageBlock(imgPath, label) {
  const fullPath = path.resolve(SCREENSHOTS_DIR, imgPath);
  if (!fs.existsSync(fullPath)) {
    console.warn(`   ⚠ 图片不存在，跳过: ${imgPath}`);
    return p(`[图片缺失: ${imgPath}]`, { color: "999999", size: 20 });
  }
  const imgData = fs.readFileSync(fullPath);
  // 最大宽度约 14cm (A4 可用区约 16cm)
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 80 },
    children: [
      new ImageRun({
        type: "png",
        data: imgData,
        transformation: { width: 480, height: 320 },
        altText: { title: label, description: label, name: label },
      }),
    ],
  });
}

function caption(text) {
  return p(text, {
    size: 18,
    color: "666666",
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 200 },
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

// ── 表格辅助 ──
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = {
  top: thinBorder,
  bottom: thinBorder,
  left: thinBorder,
  right: thinBorder,
};

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "1E3C72", type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [
      p(text, { bold: true, color: "FFFFFF", size: 20, alignment: AlignmentType.CENTER }),
    ],
  });
}

function dataCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [p(text, { size: 20 })],
  });
}

// ── 封面 ──
function buildCover() {
  return [
    p("", { spacing: { after: 2400 } }),
    p("水泥配比计算系统", {
      bold: true,
      size: 52,
      alignment: AlignmentType.CENTER,
      color: "1E3C72",
    }),
    p("软件操作说明书", {
      bold: true,
      size: 44,
      alignment: AlignmentType.CENTER,
      color: "2A5298",
      spacing: { after: 300 },
    }),
    p("V2 — 全功能详尽版", {
      size: 22,
      alignment: AlignmentType.CENTER,
      color: "888888",
      spacing: { after: 400 },
    }),
    p("", { spacing: { after: 1200 } }),
    p("CRRC · Wind Tower Concrete Platform", {
      size: 24,
      alignment: AlignmentType.CENTER,
      color: "888888",
    }),
    p("中国中车风电混塔用高 / 超高性能混凝土配合比设计系统", {
      size: 22,
      alignment: AlignmentType.CENTER,
      color: "888888",
      spacing: { after: 1600 },
    }),
    p(`文档版本：2026-06-02`, {
      size: 20,
      alignment: AlignmentType.CENTER,
      color: "AAAAAA",
    }),
    p(`生成日期：${new Date().toLocaleDateString("zh-CN")}`, {
      size: 20,
      alignment: AlignmentType.CENTER,
      color: "AAAAAA",
    }),
    pageBreak(),
  ];
}

// ── Markdown 解析（简易状态机） ──
function parseMarkdown(mdText) {
  const lines = mdText.split("\n");
  const blocks = []; // { type, content, level?, items? }
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 空行
    if (!line.trim()) {
      // 累积段落到 blocks
      i++;
      continue;
    }

    // 标题
    const headingMatch = line.match(/^(#{1,4})\s+(.+)/);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        content: headingMatch[2].trim(),
      });
      i++;
      continue;
    }

    // 图片 ![alt](path)
    const imgMatch = line.match(/^!\[(.*?)\]\((.+)\)/);
    if (imgMatch) {
      const alt = imgMatch[1];
      const url = imgMatch[2];
      const filename = path.basename(url);
      blocks.push({ type: "image", content: filename, alt });
      i++;
      continue;
    }

    // 分割线
    if (line.match(/^---+$/)) {
      i++;
      continue;
    }

    // 有序列表项
    const olMatch = line.match(/^(\d+)\.\s+(.+)/);
    if (olMatch) {
      const items = [];
      while (i < lines.length) {
        const olm = lines[i].match(/^(\d+)\.\s+(.+)/);
        if (!olm) break;
        items.push({ num: olm[1], text: olm[2].trim() });
        i++;
      }
      blocks.push({ type: "ordered_list", items });
      continue;
    }

    // 无序列表项
    if (line.match(/^[-*]\s+/)) {
      const items = [];
      while (i < lines.length) {
        const ulm = lines[i].match(/^[-*]\s+(.+)/);
        if (!ulm) break;
        items.push(ulm[1].trim());
        i++;
      }
      blocks.push({ type: "unordered_list", items });
      continue;
    }

    // 普通段落：收集连续非空行
    const paraLines = [];
    while (i < lines.length) {
      const l = lines[i];
      if (
        !l.trim() ||
        l.match(/^(#{1,4})\s+/) ||
        l.match(/^!\[/) ||
        l.match(/^(-{3,})$/) ||
        l.match(/^(\d+)\.\s+/) ||
        l.match(/^[-*]\s+/)
      ) {
        break;
      }
      paraLines.push(l.trim());
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: "paragraph", content: paraLines.join(" ") });
    }
  }

  return blocks;
}

// ── 块 → docx 段落 ──
function blocksToDocx(blocks) {
  const result = [];

  for (const b of blocks) {
    switch (b.type) {
      case "heading":
        result.push(heading(b.content, b.level));
        break;

      case "image":
        result.push(imageBlock(b.content, b.alt));
        result.push(caption(b.alt));
        break;

      case "paragraph":
        result.push(p(b.content));
        break;

      case "ordered_list":
        for (const item of b.items) {
          result.push(numberBullet(item.num, item.text));
        }
        break;

      case "unordered_list":
        for (const item of b.items) {
          result.push(bullet(item));
        }
        break;
    }
  }

  return result;
}

// ── 主流程 ──
function main() {
  console.log("📄 读取 Markdown 文件...");
  const mdText = fs.readFileSync(MD_PATH, "utf-8");

  // 按 --- 分割各章节
  const sections = mdText.split(/\n---+\n/);

  console.log(`  共解析到 ${sections.length} 个章节块`);

  const allChildren = [];

  // 第一个块是封面内容 (标题)，手动构建封面
  allChildren.push(...buildCover());

  for (const section of sections) {
    const trimmed = section.trim();
    if (!trimmed) continue;

    const blocks = parseMarkdown(trimmed);
    allChildren.push(...blocksToDocx(blocks));
  }

  console.log("🔧 构建 DOCX 文档对象...");

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: "微软雅黑", size: 22 },
        },
      },
      paragraphStyles: [
        {
          id: "Heading1",
          name: "Heading 1",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { size: 36, bold: true, font: "微软雅黑", color: "1E3C72" },
          paragraph: {
            spacing: { before: 360, after: 120 },
            outlineLevel: 0,
          },
        },
        {
          id: "Heading2",
          name: "Heading 2",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { size: 30, bold: true, font: "微软雅黑", color: "2A5298" },
          paragraph: {
            spacing: { before: 280, after: 120 },
            outlineLevel: 1,
          },
        },
        {
          id: "Heading3",
          name: "Heading 3",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { size: 26, bold: true, font: "微软雅黑", color: "333333" },
          paragraph: {
            spacing: { before: 200, after: 100 },
            outlineLevel: 2,
          },
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 }, // A4
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        },
        headers: {
          default: new Header({
            children: [
              new Paragraph({
                alignment: AlignmentType.RIGHT,
                border: {
                  bottom: {
                    style: BorderStyle.SINGLE,
                    size: 4,
                    color: "2A5298",
                    space: 1,
                  },
                },
                children: [
                  new TextRun({
                    text: "水泥配比计算系统 · 软件操作说明书",
                    font: "微软雅黑",
                    size: 16,
                    color: "888888",
                  }),
                ],
              }),
            ],
          }),
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                border: {
                  top: {
                    style: BorderStyle.SINGLE,
                    size: 2,
                    color: "CCCCCC",
                    space: 1,
                  },
                },
                children: [
                  new TextRun({
                    text: "— ",
                    font: "微软雅黑",
                    size: 16,
                    color: "AAAAAA",
                  }),
                  new TextRun({
                    children: [PageNumber.CURRENT],
                    font: "微软雅黑",
                    size: 16,
                    color: "AAAAAA",
                  }),
                  new TextRun({
                    text: " —",
                    font: "微软雅黑",
                    size: 16,
                    color: "AAAAAA",
                  }),
                ],
              }),
            ],
          }),
        },
        children: allChildren,
      },
    ],
  });

  console.log("💾 写入 DOCX 文件...");
  Packer.toBuffer(doc).then((buffer) => {
    fs.writeFileSync(OUTPUT_PATH, buffer);
    console.log(`✅ 生成完成: ${OUTPUT_PATH}`);
    console.log(`   文件大小: ${(buffer.length / 1024).toFixed(1)} KB`);
  });
}

main();
