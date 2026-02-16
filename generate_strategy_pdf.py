"""
Wine Deal Hunter — 捡漏策略 PDF 生成
生成可转发的专业策略说明文档（排版优化版）
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable

# ── 尺寸 ───────────────────────────────────
PAGE_W, PAGE_H = A4  # 210mm x 297mm
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ── 颜色 ───────────────────────────────────
WINE_DARK = HexColor("#5c1f2e")
WINE_RED  = HexColor("#8b3a4a")
GOLD      = HexColor("#c9a84c")
TEXT_MAIN  = HexColor("#2d2d2d")
TEXT_SEC   = HexColor("#777777")
TBL_HDR   = HexColor("#3d1525")
TBL_ALT   = HexColor("#f9f5ef")
BORDER    = HexColor("#e0d6c8")

# ── 注册中文字体 ─────────────────────────────
FONT = "Helvetica"
FONT_B = "Helvetica-Bold"

for fp in [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont("CN", fp, subfontIndex=0))
            FONT = FONT_B = "CN"
            break
        except Exception:
            continue


# ── 样式工厂 ──────────────────────────────
def _s(name, **kw):
    defaults = dict(fontName=FONT, fontSize=10.5, leading=16, textColor=TEXT_MAIN)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


S_COVER_TITLE = _s("CT", fontName=FONT_B, fontSize=28, leading=40,
                    textColor=WINE_DARK, alignment=TA_CENTER)
S_COVER_SUB   = _s("CS", fontSize=13, leading=20, textColor=TEXT_SEC,
                    alignment=TA_CENTER)
S_H1          = _s("H1", fontName=FONT_B, fontSize=18, leading=26,
                    textColor=WINE_DARK, spaceBefore=10*mm, spaceAfter=4*mm)
S_H2          = _s("H2", fontName=FONT_B, fontSize=13, leading=19,
                    textColor=WINE_RED, spaceBefore=5*mm, spaceAfter=2*mm)
S_BODY        = _s("BD", spaceAfter=2.5*mm)
S_BULLET      = _s("BL", leftIndent=12, spaceAfter=1.5*mm)
S_CAPTION     = _s("CAP", fontSize=8.5, leading=13, textColor=TEXT_SEC,
                    alignment=TA_CENTER, spaceAfter=3*mm)
S_TBL_HDR     = _s("TH", fontName=FONT_B, fontSize=9.5, leading=14,
                    textColor=white, alignment=TA_CENTER)
S_TBL_CELL    = _s("TC", fontSize=9, leading=14, textColor=TEXT_MAIN)
S_TBL_CELL_C  = _s("TCC", fontSize=9, leading=14, textColor=TEXT_MAIN,
                    alignment=TA_CENTER)


# ── 装饰线 ─────────────────────────────────
class GoldLine(Flowable):
    def __init__(self, width=None, thickness=1.2):
        Flowable.__init__(self)
        self._w = width
        self._t = thickness

    def wrap(self, aw, ah):
        w = self._w or aw
        return (w, self._t + 2)

    def draw(self):
        w = self._w or (self.width if hasattr(self, 'width') else CONTENT_W)
        self.canv.setStrokeColor(GOLD)
        self.canv.setLineWidth(self._t)
        self.canv.line(0, 0, w, 0)


# ── 酒杯图标 ────────────────────────────────
class WineGlass(Flowable):
    def __init__(self, size=45):
        Flowable.__init__(self)
        self.size = size

    def wrap(self, aw, ah):
        return (self.size, self.size)

    def draw(self):
        c, s = self.canv, self.size
        cx = s / 2
        c.setStrokeColor(GOLD)
        c.setFillColor(GOLD)
        c.setLineWidth(1.5)
        c.ellipse(cx - s*0.28, s*0.48, cx + s*0.28, s*0.82)
        c.line(cx, s*0.48, cx, s*0.2)
        c.line(cx - s*0.18, s*0.2, cx + s*0.18, s*0.2)


# ── 表格工具 ─────────────────────────────────
def _wrap_cell(text, style=None):
    """将文本包成 Paragraph 以支持自动换行"""
    return Paragraph(str(text), style or S_TBL_CELL)

def _wrap_header(text):
    return Paragraph(str(text), S_TBL_HDR)

def _wrap_center(text):
    return Paragraph(str(text), S_TBL_CELL_C)


def make_table(headers, rows, col_widths, center_cols=None):
    """构建表格，所有单元格都用 Paragraph 以支持自动换行"""
    center_cols = set(center_cols or [])

    hdr_row = [_wrap_header(h) for h in headers]
    data = [hdr_row]

    for row in rows:
        cells = []
        for ci, val in enumerate(row):
            if ci in center_cols:
                cells.append(_wrap_center(val))
            else:
                cells.append(_wrap_cell(val))
        data.append(cells)

    cmds = [
        # 表头
        ("BACKGROUND", (0, 0), (-1, 0), TBL_HDR),
        ("LINEBELOW",  (0, 0), (-1, 0), 1.5, GOLD),
        # 通用
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        # 行间线
        ("LINEBELOW",  (0, 1), (-1, -1), 0.4, BORDER),
    ]
    # 交替行
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), TBL_ALT))

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(cmds))
    return tbl


# ── 页脚 ─────────────────────────────────
def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(TEXT_SEC)
    canvas.drawCentredString(PAGE_W / 2, 10 * mm,
        f"Wine Deal Hunter · 策略白皮书 v1.0  —  第 {doc.page} 页")
    canvas.restoreState()


# ════════════════════════════════════════════
# 构建 PDF
# ════════════════════════════════════════════
def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=18 * mm,
    )
    story = []

    # ━━━ 封面 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(Spacer(1, 50 * mm))
    story.append(WineGlass(48))
    story.append(Spacer(1, 8 * mm))
    story.append(GoldLine())
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Wine Deal Hunter", S_COVER_TITLE))
    story.append(Paragraph("葡萄酒捡漏策略白皮书", S_COVER_TITLE))
    story.append(Spacer(1, 6 * mm))
    story.append(GoldLine(CONTENT_W * 0.35))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("全球比价 · 自动发现 · 精准捡漏", S_COVER_SUB))
    story.append(Paragraph("v1.0 &nbsp;|&nbsp; 2026.02", S_COVER_SUB))
    story.append(Spacer(1, 35 * mm))
    story.append(Paragraph(
        "本文档详细说明 Wine Deal Hunter 捡漏引擎的核心策略、算法模型、"
        "覆盖酒款及风险说明。仅供内部交流参考。", S_CAPTION))
    story.append(PageBreak())

    # ━━━ 一、核心策略 ━━━━━━━━━━━━━━━━━━━━━━
    story.append(Paragraph("一、核心策略：全球低买 → 香港高卖", S_H1))
    story.append(GoldLine())
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "系统自动在全球范围扫描 <b>50 款硬通货酒</b> 的最低售价，"
        "与 <b>香港市场均价</b> 进行对比。扣除运费、保险等全部成本后，"
        "利润率 ≥ 15% 的标记为「捡漏机会」。", S_BODY))

    story.append(Paragraph("策略流程", S_H2))
    story.append(make_table(
        ["步骤", "说明"],
        [
            ["① 数据采集", "爬取 Wine-Searcher 全球最低价 + 香港市场均价"],
            ["② 成本计算", "全入成本 = 买入价 + 运费 + 保险 (2.5%)"],
            ["③ 利润分析", "利润率 = (港卖价 - 全入成本) / 全入成本 × 100%"],
            ["④ 筛选过滤", "利润率 ≥ 15% 标记为「捡漏机会」"],
            ["⑤ 评分排序", "综合利润率 / 酒款档次 / 价格区间，评分 1-10"],
            ["⑥ 推送通知", "Telegram 实时推送 + Web 面板展示"],
        ],
        col_widths=[32*mm, CONTENT_W - 32*mm],
        center_cols={0},
    ))

    # ━━━ 二、成本模型 ━━━━━━━━━━━━━━━━━━━━━━
    story.append(Paragraph("二、成本模型", S_H1))
    story.append(GoldLine())
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("计算公式", S_H2))
    formulas = [
        "<b>全入成本</b> = 全球最低买入价 + 国际运费 + 运输保险 (买入价 × 2.5%)",
        "<b>利润率</b> = (香港卖出价 − 全入成本) ÷ 全入成本 × 100%",
        "<b>利润阈值</b> = 15%（低于此值不触发提醒）",
    ]
    for f in formulas:
        story.append(Paragraph(f, S_BODY))

    story.append(Paragraph("各产区运费 (RMB/瓶)", S_H2))
    story.append(make_table(
        ["产区", "整箱", "散瓶", "备注"],
        [
            ["波尔多 / 勃艮第 / 罗纳河谷", "¥50", "¥85", "欧洲 → 香港"],
            ["意大利 / 香槟 / 西班牙",     "¥50", "¥85", "欧洲 → 香港"],
            ["美国 (加州)",               "¥145", "¥180", "跨太平洋运输"],
            ["澳大利亚",                  "¥145", "¥180", "南半球运输"],
            ["智利",                      "¥130", "¥165", "南美运输"],
        ],
        col_widths=[45*mm, 18*mm, 18*mm, CONTENT_W - 81*mm],
        center_cols={1, 2},
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("* 保险费率：买入价的 2.5%，覆盖运输过程中的破损风险", S_CAPTION))

    # ━━━ 三、评分算法 ━━━━━━━━━━━━━━━━━━━━━━
    story.append(Paragraph("三、机会评分算法 (1-10 分)", S_H1))
    story.append(GoldLine())
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "每条捡漏机会会获得综合评分，方便快速判断优先级。评分 ≥ 7 为强烈推荐，"
        "5-6 值得关注，&lt; 5 仅作参考。", S_BODY))

    story.append(make_table(
        ["维度", "满分", "评分规则"],
        [
            ["利润率",     "4 分", "≥50% → 4 / ≥30% → 3 / ≥20% → 2 / ≥15% → 1"],
            ["酒款档次",   "3 分", "一级庄·DRC → 3 / 超二级·右岸 → 2 / 其他名庄 → 1"],
            ["价格合理性", "2 分", "¥350-¥36000 → 2 / >¥36000 → 1 / <¥350 → 0"],
            ["差价绝对值", "1 分", "卖出价 − 买入价 > ¥700 → 加 1 分"],
        ],
        col_widths=[28*mm, 18*mm, CONTENT_W - 46*mm],
        center_cols={0, 1},
    ))

    story.append(PageBreak())

    # ━━━ 四、硬通货清单 ━━━━━━━━━━━━━━━━━━━━
    story.append(Paragraph("四、覆盖酒款 — 50 款全球硬通货", S_H1))
    story.append(GoldLine())
    story.append(Spacer(1, 3 * mm))

    wines = [
        ("波尔多一级庄",
         "Lafite Rothschild · Latour · Mouton Rothschild · Margaux · Haut-Brion"),
        ("波尔多超二级",
         "Leoville Las Cases · Cos d'Estournel · Ducru-Beaucaillou · Palmer · "
         "Pichon Comtesse · Lynch-Bages · Pontet-Canet"),
        ("波尔多右岸",
         "Angelus · Cheval Blanc · Ausone · Petrus · Le Pin · Pavie"),
        ("勃艮第顶级",
         "DRC · Leroy · Armand Rousseau · Comte de Vogue · "
         "Roumier · Coche-Dury · Leflaive"),
        ("意大利名庄",
         "Sassicaia · Ornellaia · Tignanello · Masseto · Solaia · "
         "Gaja Barbaresco · Conterno Monfortino"),
        ("新世界硬通货",
         "Penfolds Grange · Bin 389 · Bin 407 · Opus One · "
         "Screaming Eagle · Harlan Estate · Almaviva · Vega Sicilia Unico"),
        ("香槟名庄",
         "Dom Perignon · Krug · Cristal · Salon Le Mesnil · "
         "Bollinger Grande Annee"),
        ("罗纳河谷",
         "Guigal La Mouline · La Landonne · La Turque · "
         "Chateau Rayas · Chapoutier Le Pavillon"),
    ]

    # 每个分类一个小卡片
    for cat, names in wines:
        block = KeepTogether([
            Paragraph(f"<b>▎{cat}</b>", _s("WC", fontName=FONT_B, fontSize=11,
                       leading=16, textColor=WINE_RED, spaceBefore=3*mm, spaceAfter=1*mm)),
            Paragraph(names, _s("WN", fontSize=9.5, leading=15,
                       textColor=TEXT_MAIN, leftIndent=8, spaceAfter=2*mm)),
        ])
        story.append(block)

    story.append(PageBreak())

    # ━━━ 五、数据源 ━━━━━━━━━━━━━━━━━━━━━━━
    story.append(Paragraph("五、数据源与扫描机制", S_H1))
    story.append(GoldLine())
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("数据源", S_H2))
    story.append(Paragraph(
        "<b>Wine-Searcher.com</b> — 全球最大的葡萄酒比价平台，"
        "聚合上万家酒商的价格数据。系统通过智能爬虫采集：", S_BODY))
    for item in [
        "全球最低售价（含酒商名称、国家、购买链接）",
        "香港市场均价（用作卖出参考价）",
        "可购买年份列表",
        "酒商库存状态",
    ]:
        story.append(Paragraph(f"•&nbsp; {item}", S_BULLET))

    story.append(Paragraph("扫描频率", S_H2))
    story.append(Paragraph(
        "系统每 <b>30 分钟</b> 自动执行一次全量扫描，覆盖全部 50 款酒。"
        "同时支持手动触发即时扫描和单酒搜索。", S_BODY))

    story.append(Paragraph("反爬策略", S_H2))
    story.append(Paragraph(
        "每次请求间隔 3-6 秒随机延迟，模拟真实浏览器 User-Agent，"
        "带重试机制（最多 3 次），确保稳定采集。", S_BODY))

    story.append(Spacer(1, 8 * mm))

    # ━━━ 六、风险说明 ━━━━━━━━━━━━━━━━━━━━━━
    story.append(Paragraph("六、风险与注意事项", S_H1))
    story.append(GoldLine())
    story.append(Spacer(1, 3 * mm))

    story.append(make_table(
        ["风险类型", "说明"],
        [
            ["价格波动",  "市场价格随供需变动，爬取价格与实际成交价可能存在偏差"],
            ["年份差异",  "当前搜索未锁定年份，同酒款不同年份差价可达数倍"],
            ["真伪风险",  "低价酒商存在假酒可能，建议优先选择知名酒商"],
            ["汇率波动",  "系统以 USD 统一计价，显示时自动折算为 RMB"],
            ["关税政策",  "香港零关税；如目标市场为中国大陆，需额外计入关税"],
            ["数据延迟",  "Wine-Searcher 数据可能有数小时延迟，非实时报价"],
        ],
        col_widths=[28*mm, CONTENT_W - 28*mm],
        center_cols={0},
    ))

    story.append(Spacer(1, 15 * mm))
    story.append(GoldLine())
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Wine Deal Hunter &nbsp;|&nbsp; 捡漏引擎 v1.0 &nbsp;|&nbsp; 2026.02", S_CAPTION))
    story.append(Paragraph(
        "本文档仅供内部学习交流，不构成投资建议。投资有风险，入市需谨慎。", S_CAPTION))

    # ── 构建 ──
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"✅ PDF 已生成: {output_path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "Wine_Deal_Hunter_策略白皮书.pdf")
    build_pdf(out)
