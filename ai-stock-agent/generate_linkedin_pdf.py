"""
Enhanced LinkedIn project showcase PDF - v2.
Run: python generate_linkedin_pdf.py
Output: paper_results/LinkedIn_AI_Stock_Trading_Project.pdf
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

OUT_DIR = Path(__file__).parent / "paper_results"
OUT_DIR.mkdir(exist_ok=True)
OUT_FILE = OUT_DIR / "LinkedIn_AI_Stock_Trading_Project.pdf"

# ── Colour palette ──────────────────────────────────────────────────────────────
DARK_BLUE    = colors.HexColor('#0F172A')
NAVY         = colors.HexColor('#1B2A4A')
ACCENT_BLUE  = colors.HexColor('#2563EB')
SKY          = colors.HexColor('#0EA5E9')
LIGHT_BLUE   = colors.HexColor('#EFF6FF')
GREEN        = colors.HexColor('#16A34A')
GREEN_LIGHT  = colors.HexColor('#DCFCE7')
AMBER        = colors.HexColor('#D97706')
AMBER_LIGHT  = colors.HexColor('#FEF3C7')
PURPLE       = colors.HexColor('#7C3AED')
PURPLE_LIGHT = colors.HexColor('#F5F3FF')
TEAL         = colors.HexColor('#0D9488')
RED          = colors.HexColor('#DC2626')
SLATE_50     = colors.HexColor('#F8FAFC')
SLATE_100    = colors.HexColor('#F1F5F9')
SLATE_200    = colors.HexColor('#E2E8F0')
SLATE_400    = colors.HexColor('#94A3B8')
SLATE_600    = colors.HexColor('#475569')
SLATE_800    = colors.HexColor('#1E293B')
WHITE        = colors.white

PAGE_W = 17 * cm   # usable width (A4 minus 2cm margins each side)


# ── Styles ──────────────────────────────────────────────────────────────────────
def S(name, **kw):
    defaults = dict(fontName='Helvetica', fontSize=10, leading=14,
                    textColor=SLATE_800, spaceAfter=4)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


def build_styles():
    return {
        'title':        S('title',   fontName='Helvetica-Bold', fontSize=22,
                          textColor=WHITE, alignment=TA_CENTER, spaceAfter=3),
        'subtitle':     S('subtitle', fontSize=12,
                          textColor=colors.HexColor('#BFDBFE'),
                          alignment=TA_CENTER, spaceAfter=2),
        'author':       S('author',  fontName='Helvetica-Oblique', fontSize=11,
                          textColor=colors.HexColor('#93C5FD'), alignment=TA_CENTER),
        'section':      S('section', fontName='Helvetica-Bold', fontSize=12,
                          textColor=NAVY, spaceBefore=12, spaceAfter=5),
        'body':         S('body',    fontSize=10, alignment=TA_JUSTIFY,
                          leading=15, spaceAfter=5),
        'bullet':       S('bullet',  fontSize=10, leftIndent=12,
                          spaceAfter=4, leading=14),
        'caption':      S('caption', fontName='Helvetica-Oblique', fontSize=8.5,
                          textColor=SLATE_600, alignment=TA_CENTER, spaceAfter=3),
        'small':        S('small',   fontSize=8.5, textColor=SLATE_600,
                          leading=12, spaceAfter=3),
        'metric_val':   S('mv',      fontName='Helvetica-Bold', fontSize=20,
                          textColor=ACCENT_BLUE, alignment=TA_CENTER, spaceAfter=1),
        'metric_lbl':   S('ml',      fontName='Helvetica-Bold', fontSize=8.5,
                          textColor=NAVY, alignment=TA_CENTER, spaceAfter=0),
        'metric_sub':   S('ms',      fontSize=7.5, textColor=SLATE_600,
                          alignment=TA_CENTER, spaceAfter=0),
        'tag':          S('tag',     fontName='Helvetica-Bold', fontSize=8.5,
                          textColor=WHITE, alignment=TA_CENTER),
        'tag_dark':     S('tag_dark', fontName='Helvetica-Bold', fontSize=8.5,
                          textColor=SLATE_800, alignment=TA_CENTER),
        'step_num':     S('snum',    fontName='Helvetica-Bold', fontSize=16,
                          textColor=WHITE, alignment=TA_CENTER),
        'step_title':   S('stitle',  fontName='Helvetica-Bold', fontSize=10,
                          textColor=DARK_BLUE, spaceAfter=2),
        'step_body':    S('sbody',   fontSize=9.5, textColor=SLATE_600,
                          alignment=TA_JUSTIFY, leading=13, spaceAfter=0),
        'discord_mono': S('disc',    fontName='Helvetica', fontSize=8.5,
                          textColor=colors.HexColor('#DCDDDE'), leading=13),
        'discord_title':S('dtitle',  fontName='Helvetica-Bold', fontSize=9,
                          textColor=WHITE, leading=13),
        'tl_phase':     S('tlp',     fontName='Helvetica-Bold', fontSize=9,
                          textColor=WHITE, alignment=TA_CENTER),
        'tl_body':      S('tlb',     fontSize=9, textColor=SLATE_600,
                          leading=13, spaceAfter=0),
    }


# ── Helpers ─────────────────────────────────────────────────────────────────────
def section_header(text, styles, color=NAVY):
    hr = HRFlowable(width='100%', thickness=0.5, color=SLATE_200,
                    spaceAfter=3, spaceBefore=8)
    p  = Paragraph(f'<b>▌ {text}</b>',
                   ParagraphStyle('sh', fontName='Helvetica-Bold', fontSize=12,
                                  textColor=color, spaceAfter=5))
    return [hr, p]


def colored_box(content_rows, bg_color, col_widths, padding=8,
                radius=4, border_color=None, border_width=0.5):
    t = Table(content_rows, colWidths=col_widths)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('TOPPADDING',    (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
        ('LEFTPADDING',   (0, 0), (-1, -1), padding),
        ('RIGHTPADDING',  (0, 0), (-1, -1), padding),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    if border_color:
        cmds += [('BOX', (0, 0), (-1, -1), border_width, border_color)]
    t.setStyle(TableStyle(cmds))
    return t


# ── HEADER ──────────────────────────────────────────────────────────────────────
def header_block(styles):
    accent_bar = Table([['']], colWidths=[PAGE_W])
    accent_bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SKY),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    title_t = Table(
        [[Paragraph('AI-Powered Automated Stock Trading System', styles['title'])],
         [Paragraph('Multi-Agent LLM Pipeline  ·  Real-Time Signals  ·  Automated Risk Management', styles['subtitle'])],
         [Spacer(1, 3)],
         [Paragraph('Pradeep Somasundaram  ·  Independent AI &amp; FinTech Developer', styles['author'])]],
        colWidths=[PAGE_W],
    )
    title_t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 18),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ('LEFTPADDING',   (0, 0), (-1, -1), 18),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 18),
    ]))

    return KeepTogether([accent_bar, title_t])


# ── METRICS ROW ─────────────────────────────────────────────────────────────────
def metrics_row(styles):
    metrics = [
        ('493',       'Stocks Scanned',   'Full S&P 500'),
        ('7',         'AI Agent Nodes',   'LangGraph DAG'),
        ('19',        'Accuracy Filters', 'Signal validation'),
        ('6',         'Data Sources',     'Per decision'),
        ('65–72%',    'Signal Accuracy',  'vs 50% baseline'),
        ('<30 min',   'Alert Latency',    'Realtime Discord'),
    ]
    vals = [Paragraph(m[0], styles['metric_val']) for m in metrics]
    lbls = [Paragraph(m[1], styles['metric_lbl']) for m in metrics]
    subs = [Paragraph(m[2], styles['metric_sub']) for m in metrics]

    t = Table([vals, lbls, subs], colWidths=[PAGE_W / 6] * 6)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('BACKGROUND', (4, 0), (4, -1), GREEN_LIGHT),   # accuracy metric highlight
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBEFORE', (1, 0), (-1, -1), 0.5, SLATE_200),
    ]))
    return t


# ── PIPELINE DIAGRAM ────────────────────────────────────────────────────────────
def pipeline_diagram():
    """7-node LangGraph architecture as a 2-row flow diagram."""
    DW, DH = PAGE_W, 4.6 * cm
    d = Drawing(DW, DH)

    # Background
    d.add(Rect(0, 0, DW, DH, rx=6, ry=6,
               fillColor=SLATE_50, strokeColor=SLATE_200, strokeWidth=0.5))

    # Title
    d.add(String(DW / 2, DH - 11,
                 'LangGraph Multi-Agent Decision Pipeline  (7 nodes, parallel execution)',
                 fontName='Helvetica-Bold', fontSize=8.5,
                 fillColor=NAVY, textAnchor='middle'))

    NW, NH = 102, 36
    H_GAP  = 12

    # Row positions (y = bottom edge of box, coords from drawing bottom)
    top_total = 4 * NW + 3 * H_GAP
    top_x0    = (DW - top_total) / 2
    top_y     = DH - 18 - NH          # bottom edge of top-row boxes

    bot_total = 3 * NW + 2 * H_GAP
    bot_x0    = (DW - bot_total) / 2
    bot_y     = top_y - 18 - NH       # bottom edge of bottom-row boxes

    TOP_NODES = [
        ('1. Data Fetch',     '#3B82F6'),
        ('2. Tech Features',  '#7C3AED'),
        ('3. Fundamentals',   '#059669'),
        ('4. News Sentiment', '#D97706'),
    ]
    BOT_NODES = [
        ('5. Mkt Context',    '#DC2626'),
        ('6. RAG Memory',     '#0D9488'),
        ('7. LLM Decision',   '#0F172A'),
    ]

    def draw_node(x, y, label, hex_col, is_final=False):
        stroke  = colors.HexColor('#F59E0B') if is_final else None
        sw      = 2 if is_final else 0
        d.add(Rect(x, y, NW, NH, rx=5, ry=5,
                   fillColor=colors.HexColor(hex_col),
                   strokeColor=stroke, strokeWidth=sw))
        # Split label: "N. Text" → number line + name line
        num, name = label.split('. ', 1)
        d.add(String(x + NW / 2, y + NH / 2 + 3, num + '.',
                     fontName='Helvetica-Bold', fontSize=7.5,
                     fillColor=WHITE, textAnchor='middle'))
        d.add(String(x + NW / 2, y + NH / 2 - 9, name,
                     fontName='Helvetica', fontSize=8,
                     fillColor=WHITE, textAnchor='middle'))

    def h_arrow(x1, y_center):
        x2 = x1 + H_GAP
        d.add(Line(x1, y_center, x2 - 4, y_center,
                   strokeColor=SLATE_400, strokeWidth=1.3))
        d.add(Polygon([x2 - 4, y_center + 3, x2, y_center, x2 - 4, y_center - 3],
                      fillColor=SLATE_400, strokeColor=None))

    # Draw top row
    for i, (lbl, col) in enumerate(TOP_NODES):
        x = top_x0 + i * (NW + H_GAP)
        draw_node(x, top_y, lbl, col)
        if i < 3:
            h_arrow(x + NW, top_y + NH / 2)

    # L-shaped connector: bottom of News Sentiment → top of Mkt Context
    news_cx = top_x0 + 3 * (NW + H_GAP) + NW / 2
    mkt_cx  = bot_x0 + NW / 2
    mid_y   = (top_y + bot_y + NH) / 2   # midpoint between the two rows

    for seg in [
        (news_cx, top_y,    news_cx, mid_y),
        (news_cx, mid_y,    mkt_cx,  mid_y),
        (mkt_cx,  mid_y,    mkt_cx,  bot_y + NH + 4),
    ]:
        d.add(Line(*seg, strokeColor=SLATE_400, strokeWidth=1,
                   strokeDashArray=[3, 2]))
    # Arrowhead pointing down into Mkt Context top
    ay = bot_y + NH + 4
    d.add(Polygon([mkt_cx, ay, mkt_cx - 3, ay + 6, mkt_cx + 3, ay + 6],
                  fillColor=SLATE_400, strokeColor=None))

    # Draw bottom row
    for i, (lbl, col) in enumerate(BOT_NODES):
        x = bot_x0 + i * (NW + H_GAP)
        draw_node(x, bot_y, lbl, col, is_final=(i == 2))
        if i < 2:
            h_arrow(x + NW, bot_y + NH / 2)

    # OUTPUT label after LLM Decision
    out_x = bot_x0 + 2 * (NW + H_GAP) + NW + 6
    out_y  = bot_y + NH / 2
    d.add(String(out_x, out_y + 5,  '→ BUY / SELL / HOLD',
                 fontName='Helvetica-Bold', fontSize=7.5,
                 fillColor=colors.HexColor('#D97706'), textAnchor='start'))
    d.add(String(out_x, out_y - 6, '+ Price Target  + Stop Loss  + Confidence %',
                 fontName='Helvetica', fontSize=7,
                 fillColor=SLATE_600, textAnchor='start'))

    return d


# ── ACCURACY VISUAL ─────────────────────────────────────────────────────────────
def accuracy_visual():
    """Before / After accuracy as horizontal bar chart."""
    DW, DH = PAGE_W, 2.4 * cm
    d = Drawing(DW, DH)

    d.add(Rect(0, 0, DW, DH, rx=5, ry=5,
               fillColor=SLATE_50, strokeColor=SLATE_200, strokeWidth=0.5))

    d.add(String(DW / 2, DH - 11, 'Signal Accuracy — Before vs After Engineering',
                 fontName='Helvetica-Bold', fontSize=8.5,
                 fillColor=NAVY, textAnchor='middle'))

    label_w  = 52
    bar_x0   = label_w + 12
    max_bar  = DW - bar_x0 - 60   # room for % label

    BH = 14    # bar height
    BEFORE_PCT = 0.50
    AFTER_PCT  = 0.70

    # Before bar
    by1 = DH / 2 + 3
    d.add(String(label_w, by1 + 3, 'Before (50%):',
                 fontName='Helvetica', fontSize=8, fillColor=SLATE_600, textAnchor='end'))
    d.add(Rect(bar_x0, by1, max_bar, BH, rx=3, ry=3,
               fillColor=SLATE_200, strokeColor=None))
    d.add(Rect(bar_x0, by1, max_bar * BEFORE_PCT, BH, rx=3, ry=3,
               fillColor=RED, strokeColor=None))
    d.add(String(bar_x0 + max_bar * BEFORE_PCT + 5, by1 + 3,
                 'Coin flip', fontName='Helvetica-Oblique', fontSize=7.5,
                 fillColor=RED, textAnchor='start'))

    # After bar
    by2 = DH / 2 - BH - 5
    d.add(String(label_w, by2 + 3, 'After (70%+):',
                 fontName='Helvetica-Bold', fontSize=8, fillColor=SLATE_800, textAnchor='end'))
    d.add(Rect(bar_x0, by2, max_bar, BH, rx=3, ry=3,
               fillColor=SLATE_200, strokeColor=None))
    d.add(Rect(bar_x0, by2, max_bar * AFTER_PCT, BH, rx=3, ry=3,
               fillColor=GREEN, strokeColor=None))
    d.add(String(bar_x0 + max_bar * AFTER_PCT + 5, by2 + 3,
                 '65–72% target', fontName='Helvetica-Bold', fontSize=7.5,
                 fillColor=GREEN, textAnchor='start'))

    return d


# ── WORKFLOW CARDS ───────────────────────────────────────────────────────────────
def workflow_cards(styles):
    STEP_COLORS = [ACCENT_BLUE, PURPLE, GREEN, AMBER, TEAL]
    steps = [
        ('Pre-Screen — 493 Stocks in Parallel',
         'Every market hour, hourly OHLCV data is downloaded for every S&P 500 stock. '
         'RSI, ATR, VWAP, volume ratio, momentum, and daily RSI are computed in parallel '
         'using 30 threads. Only stocks with extreme signals advance (RSI < 35 or > 70, '
         'unusual volume, or large price moves).'),
        ('Deep AI Analysis — LangGraph 7-Node DAG',
         'The 40–50 most interesting stocks pass through the 7-node pipeline: '
         'data → tech features → fundamentals → news sentiment → market context → '
         'RAG retrieval → LLM reasoning. The LLM synthesises all six data sources '
         'and returns a structured JSON with BUY/SELL/HOLD, price target, stop loss, '
         'and a confidence score (0–100%).'),
        ('Signal Filtering — 19 Accuracy Layers',
         'Raw LLM signals pass through 19 engineered filters: market regime check '
         '(no SELL in bull markets), sector alignment, RSI gate, time-of-day gate, '
         'earnings proximity block, Bollinger Band proximity, MACD crossover, VWAP '
         'position, historical win rate per ticker, minimum volume, and more.'),
        ('Real-Time Discord Alerts',
         'Qualifying signals are instantly sent to Discord with exact entry price, '
         'stop loss, price target, position size (2% risk rule), confidence %, '
         'and plain-English reasoning. Stop-loss alerts fire within 30 minutes of '
         'being triggered. End-of-day recap shows every signal\'s outcome.'),
        ('Swing Trading Engine — Paper Trades',
         'A parallel engine scans 90-day daily charts targeting 8–15% moves over '
         '5–10 days. It auto-enters paper trades, monitors positions twice daily, '
         'and exits on target hit, stop hit, or 10-day expiry. Position sizing '
         'uses 2% portfolio risk per trade with ATR-based stops.'),
    ]

    rows = []
    for i, (title, body) in enumerate(steps):
        num_cell = colored_box(
            [[Paragraph(str(i + 1), styles['step_num'])]],
            bg_color=STEP_COLORS[i], col_widths=[0.9 * cm], padding=6,
        )
        text_cell = Table([
            [Paragraph(f'<b>{title}</b>', styles['step_title'])],
            [Paragraph(body, styles['step_body'])],
        ], colWidths=[PAGE_W - 1.6 * cm])
        text_cell.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('LINEBEFORE', (0, 0), (0, -1), 3, STEP_COLORS[i]),
        ]))
        row_t = Table([[num_cell, text_cell]],
                      colWidths=[1.1 * cm, PAGE_W - 1.1 * cm])
        row_t.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        rows.append(row_t)
        rows.append(Spacer(1, 0.25 * cm))

    return rows


# ── DISCORD PREVIEW ─────────────────────────────────────────────────────────────
def discord_preview(styles):
    BG    = colors.HexColor('#36393F')
    EMBED = colors.HexColor('#2F3136')
    LINE  = colors.HexColor('#2563EB')
    GREEN_D = colors.HexColor('#57F287')

    header = Table(
        [[Paragraph('🤖  AI Stock Scanner  —  LIVE TRADE SIGNAL', styles['discord_title'])]],
        colWidths=[PAGE_W],
    )
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
    ]))

    msg_style = ParagraphStyle('ds', fontName='Helvetica', fontSize=8.5,
                               textColor=colors.HexColor('#DCDDDE'), leading=13)
    grn_style = ParagraphStyle('dg', fontName='Helvetica-Bold', fontSize=8.5,
                               textColor=GREEN_D, leading=13)
    gry_style = ParagraphStyle('dgr', fontName='Helvetica-Oblique', fontSize=8,
                               textColor=colors.HexColor('#B9BBBE'), leading=13)

    lines = [
        [Paragraph('📈  <b>BUY   FORD (F)   @ $12.34</b>', grn_style)],
        [Paragraph('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', gry_style)],
        [Paragraph('🎯  Target Price :  <b>$13.57</b>  <font color="#57F287">(+10.0%)</font>', msg_style)],
        [Paragraph('🛑  Stop Loss    :  <b>$11.85</b>  <font color="#ED4245">(−4.0%)</font>', msg_style)],
        [Paragraph('💯  Confidence   :  <b>72%</b>', msg_style)],
        [Paragraph('📊  RSI: 28 (Oversold)  |  Trend: UPTREND  |  Vol: 2.1× avg', msg_style)],
        [Paragraph('📦  Suggested Size: 81 shares  ($1,000 / $12.34)', msg_style)],
        [Paragraph('', msg_style)],
        [Paragraph('💡  <i>F is deeply oversold with RSI=28, volume spike 2.1× average, '
                   'MACD bullish crossover, and price touching lower Bollinger Band. '
                   'Fundamentals healthy, no earnings for 23 days.</i>', gry_style)],
        [Paragraph('', msg_style)],
        [Paragraph('⏰  2026-07-01 10:05 AM ET  |  Scanned 493 stocks', gry_style)],
    ]
    embed = Table(lines, colWidths=[PAGE_W - 0.35 * cm])
    embed.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), EMBED),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('LINEBEFORE', (0, 0), (0, -1), 4, LINE),
    ]))

    wrapper = Table([[embed]], colWidths=[PAGE_W])
    wrapper.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]))

    return KeepTogether([header, wrapper])


# ── RISK MANAGEMENT CALLOUT ──────────────────────────────────────────────────────
def risk_callout(styles):
    label_s = ParagraphStyle('rl', fontName='Helvetica-Bold', fontSize=9,
                             textColor=AMBER, spaceAfter=1)
    val_s   = ParagraphStyle('rv', fontName='Helvetica-Bold', fontSize=14,
                             textColor=DARK_BLUE, spaceAfter=0)
    sub_s   = ParagraphStyle('rs', fontName='Helvetica', fontSize=8,
                             textColor=SLATE_600, spaceAfter=0)

    items = [
        ('2%',          'Risk per trade',    'Portfolio risk cap'),
        ('10%',         'Profit target',     'Exit long positions'),
        ('4%',          'Stop loss',         'Auto-exit on breach'),
        ('10 days',     'Max hold period',   'Time-based exit'),
        ('5 max',       'Open positions',    'Concentration limit'),
        ('$10,000',     'Paper portfolio',   'Starting capital'),
    ]

    vals_row = [Paragraph(x[0], val_s)   for x in items]
    lbl_row  = [Paragraph(x[1], label_s) for x in items]
    sub_row  = [Paragraph(x[2], sub_s)   for x in items]

    inner = Table([vals_row, lbl_row, sub_row],
                  colWidths=[PAGE_W / 6] * 6)
    inner.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEAFTER', (0, 0), (-2, -1), 0.5, SLATE_200),
    ]))

    header_p = Paragraph('⚖  Risk Management Rules', styles['section'])

    outer = Table([[inner]], colWidths=[PAGE_W])
    outer.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), AMBER_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, AMBER),
    ]))
    return [header_p, outer]


# ── DATA SOURCES GRID ────────────────────────────────────────────────────────────
def data_sources_grid(styles):
    sources = [
        ('📈 Technical Indicators', '#2563EB',
         'RSI-14, ATR-14, MACD + histogram, Bollinger Bands, SMA-20/50, VWAP, '
         'volume ratio, daily RSI, 5h and 20h momentum, support/resistance levels.'),
        ('🏢 Fundamentals', '#7C3AED',
         'P/E ratio, revenue growth, earnings growth, debt/equity, return on equity, '
         'analyst consensus price target, health score, valuation score.'),
        ('📰 News Sentiment', '#D97706',
         'Real-time headlines scored by LLM. Key topics extracted. '
         'Bad news downgrades BUY confidence; positive catalysts boost it.'),
        ('🧠 RAG Memory', '#059669',
         'Vector DB of past analyses. Before deciding, the AI retrieves '
         'relevant historical context for the same stock — it learns from its own history.'),
        ('🌐 Market Context', '#DC2626',
         'SPY / QQQ / IWM returns today, VIX fear index, broad market mood. '
         'High VIX or broad selloff triggers automatic caution mode.'),
        ('📊 Sector Performance', '#0D9488',
         'All 11 GICS sectors via ETFs (XLK, XLF, XLE…). A BUY in a sector down 2% '
         'is penalised; a SELL in a sector up 2.6% is blocked entirely.'),
    ]

    th_s = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=9.5,
                           textColor=DARK_BLUE, spaceAfter=3)
    bd_s = ParagraphStyle('bd', fontName='Helvetica', fontSize=9,
                           textColor=SLATE_600, leading=13)

    rows = []
    for i in range(0, 6, 2):
        cells = []
        for j in range(2):
            icon_title, hex_col, body = sources[i + j]
            # Top color bar + content
            bar  = Table([['']], colWidths=[8.2 * cm])
            bar.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor(hex_col)),
                ('TOPPADDING',    (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            content = Table([
                [Paragraph(icon_title, th_s)],
                [Paragraph(body, bd_s)],
            ], colWidths=[8.2 * cm])
            content.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_BLUE),
                ('TOPPADDING',    (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ('LEFTPADDING',   (0, 0), (-1, -1), 9),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 9),
            ]))
            cell = Table([[bar], [content]], colWidths=[8.2 * cm])
            cell.setStyle(TableStyle([
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ]))
            cells.append(cell)

        row_t = Table([cells], colWidths=[8.5 * cm, 8.5 * cm])
        row_t.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]))
        rows.append(row_t)
        rows.append(Spacer(1, 0.2 * cm))

    return rows


# ── TECH STACK ───────────────────────────────────────────────────────────────────
def tech_stack(styles):
    groups = [
        ('AI & Language Models', ACCENT_BLUE,
         ['Python 3.12', 'LangGraph', 'LangChain', 'OpenAI GPT-4o-mini', 'Claude 3.5 Sonnet']),
        ('Data & Storage', PURPLE,
         ['yfinance / Yahoo Finance', 'SEC EDGAR (free)', 'FAISS Vector DB', 'SQLite', 'ChromaDB (RAG)']),
        ('Infrastructure', TEAL,
         ['AWS EC2 (Ubuntu 24)', 'systemd service', 'Cron scheduler', 'Discord Webhooks', 'GitHub']),
        ('Output & Research', GREEN,
         ['ReportLab PDF', 'python-docx (IEEE paper)', 'Paper Trading Engine', 'SQLite backtest DB']),
    ]
    rows = []
    for group_name, group_color, tags in groups:
        cat_label = Table(
            [[Paragraph(group_name, ParagraphStyle(
                'gl', fontName='Helvetica-Bold', fontSize=9,
                textColor=group_color))]],
            colWidths=[PAGE_W],
        )
        cat_label.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        rows.append(cat_label)

        tag_w = PAGE_W / len(tags)
        tag_cells = [[
            Paragraph(t, styles['tag']) for t in tags
        ]]
        t = Table(tag_cells, colWidths=[tag_w] * len(tags))
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), group_color),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('INNERGRID',     (0, 0), (-1, -1), 0.5, WHITE),
        ]))
        rows.append(t)
        rows.append(Spacer(1, 0.25 * cm))

    return rows


# ── IMPROVEMENT TABLE ────────────────────────────────────────────────────────────
def improvement_table(styles):
    hdrs = ['#', 'Accuracy Improvement', 'Impact on Signals']
    rows = [
        ['1',  'Market regime filter (SPY direction)',      'No SELL in bull markets'],
        ['2',  'Sector alignment gate',                    'Blocks sector-fighting trades'],
        ['3',  'RSI > 50 caps BUY confidence to 52%',      'Removes weak MACD-only signals'],
        ['4',  'After 2:30 PM ET: 75% threshold',          'Eliminates late-day bad entries'],
        ['5',  'Downtrend + RSI > 20 capped at 50%',       'No catching falling knives'],
        ['6',  'Daily RSI dual-timeframe confirm',          '±7% confidence adjustment'],
        ['7',  'Earnings within 1 day → skip entirely',    'Eliminates earnings gambles'],
        ['8',  'Gap-up > 8% BUY blocked at 45%',           'No chasing gap-up moves'],
        ['9',  'Minimum display confidence 55%',            'Removes noise from Discord'],
        ['10', 'VWAP alignment (2% above = −6%)',           'Penalises buying above VWAP'],
        ['11', 'Bollinger Band proximity +8%',              'Boosts boundary signals'],
        ['12', 'MACD crossover boost +6%',                  'Momentum confirmation'],
        ['13', 'Support/resistance proximity +7%',          'Key price-level alignment'],
        ['14', 'Historical win rate per ticker (DB)',        'Bad tickers −12%, good +6%'],
        ['15', 'Minimum avg volume 50K/hr',                 'Illiquid stocks skipped'],
        ['16', 'Relative strength vs SPY ±7%',              'Rewards outperformers'],
        ['17', 'Volume < 0.5× average −10%',               'Filters thin-volume entries'],
        ['18', 'Options flow ±5%',                          'Unusual call/put activity'],
        ['19', 'Price cap ≤ $50 (env-configurable)',        'Affordable trades only'],
    ]

    th_s = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8.5, textColor=WHITE)
    n_s  = ParagraphStyle('tn', fontName='Helvetica-Bold', fontSize=8.5,
                           textColor=ACCENT_BLUE, alignment=TA_CENTER)
    td_s = ParagraphStyle('td', fontName='Helvetica', fontSize=8.5, textColor=DARK_BLUE)
    ti_s = ParagraphStyle('ti', fontName='Helvetica-Oblique', fontSize=8.5, textColor=SLATE_600)

    data = [[Paragraph(h, th_s) for h in hdrs]]
    for r in rows:
        data.append([Paragraph(r[0], n_s),
                     Paragraph(r[1], td_s),
                     Paragraph(r[2], ti_s)])

    t = Table(data, colWidths=[0.8 * cm, 8.4 * cm, 7.8 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  NAVY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SLATE_50]),
        ('TOPPADDING',     (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 5),
        ('LEFTPADDING',    (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 6),
        ('GRID',           (0, 0), (-1, -1), 0.3, SLATE_200),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


# ── DEVELOPMENT TIMELINE ─────────────────────────────────────────────────────────
def timeline_table(styles):
    phases = [
        ('#1', ACCENT_BLUE, 'RSI Scanner + Discord',
         'Basic hourly RSI alerts via Discord webhook. Scanned top 20 stocks.'),
        ('#2', PURPLE, '7-Node LLM Pipeline',
         'LangGraph DAG with 6 data sources. GPT-4o-mini reasoning. Structured JSON output.'),
        ('#3', AMBER, '19 Accuracy Filters',
         '50% → 65–72% win rate. Market regime, sector, RSI gate, time-of-day, VWAP.'),
        ('#4', GREEN, 'Swing Trading Engine',
         'Paper trading with 2% risk rule, ATR stops, 10-day max hold, Discord P&L alerts.'),
        ('#5', TEAL, 'AWS Deployment',
         'EC2 Ubuntu 24, systemd service, auto-restart, log rotation, 24/7 operation.'),
        ('#6', RED, 'Full S&P 500 Universe',
         'Expanded from 20 → 493 stocks. Price filter moved to recommendation stage only.'),
    ]

    ph_s = ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=9,
                           textColor=WHITE, alignment=TA_CENTER)
    bd_s = ParagraphStyle('bd', fontName='Helvetica', fontSize=8.5,
                           textColor=SLATE_600, leading=12)
    ti_s = ParagraphStyle('ti', fontName='Helvetica-Bold', fontSize=9,
                           textColor=DARK_BLUE, spaceAfter=2)

    cells_row1 = []
    cells_row2 = []
    for phase_num, col, title, body in phases:
        ph = Table([[Paragraph(phase_num, ph_s)]],
                   colWidths=[PAGE_W / 6 - 4])
        ph.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), col),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        cells_row1.append(ph)
        text = Table([
            [Paragraph(title, ti_s)],
            [Paragraph(body, bd_s)],
        ], colWidths=[PAGE_W / 6 - 4])
        text.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), SLATE_50),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
            ('LINEBEFORE', (0, 0), (0, -1), 2, col),
        ]))
        cells_row2.append(text)

    cw = [PAGE_W / 6] * 6
    t1 = Table([cells_row1], colWidths=cw)
    t1.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                             ('LEFTPADDING', (0, 0), (-1, -1), 2),
                             ('RIGHTPADDING', (0, 0), (-1, -1), 2)]))
    t2 = Table([cells_row2], colWidths=cw)
    t2.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 0),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                             ('LEFTPADDING', (0, 0), (-1, -1), 2),
                             ('RIGHTPADDING', (0, 0), (-1, -1), 2)]))
    return [t1, Spacer(1, 0.1 * cm), t2]


# ── FOOTER ───────────────────────────────────────────────────────────────────────
def footer_block(styles):
    items = [
        ('🔗 GitHub', 'github.com/Pradeep1501'),
        ('📧 Contact', 'aadhi1501@gmail.com'),
        ('📄 Paper', 'IEEE Access (in submission)'),
        ('⚠ Disclaimer', 'Paper trading only — not financial advice'),
    ]
    vals = [Paragraph(f'<b>{k}</b><br/><font size=8 color="#475569">{v}</font>',
                      ParagraphStyle('fp', fontName='Helvetica', fontSize=9,
                                     textColor=DARK_BLUE, alignment=TA_CENTER,
                                     leading=13))
            for k, v in items]
    t = Table([vals], colWidths=[PAGE_W / 4] * 4)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), SLATE_100),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEABOVE',     (0, 0), (-1, 0), 1.5, ACCENT_BLUE),
        ('LINEAFTER',     (0, 0), (-2, -1), 0.5, SLATE_200),
    ]))
    return t


# ── BUILD PDF ────────────────────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        str(OUT_FILE), pagesize=A4,
        topMargin=1.2 * cm, bottomMargin=1.5 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title='AI-Powered Automated Stock Trading System',
        author='Pradeep Somasundaram',
    )
    styles = build_styles()
    story  = []

    # ── HEADER ────────────────────────────────────────────────────────────────────
    story.append(header_block(styles))
    story.append(Spacer(1, 0.3 * cm))

    # ── 6-METRIC BAR ─────────────────────────────────────────────────────────────
    story.append(metrics_row(styles))
    story.append(Spacer(1, 0.4 * cm))

    # ── PROJECT OVERVIEW ─────────────────────────────────────────────────────────
    for el in section_header('Project Overview', styles):
        story.append(el)
    story.append(Paragraph(
        'I built an end-to-end AI-powered stock trading system that scans all 493 S&amp;P 500 '
        'stocks every hour during market hours, identifies high-probability trade setups through '
        'a 7-node multi-agent LLM pipeline, and delivers real-time alerts to Discord — '
        'running autonomously 24/7 on AWS EC2. The system goes far beyond simple RSI alerts: '
        'it combines six independent data sources to make nuanced, context-aware decisions '
        'the way an experienced trader would. Started as a personal learning project, '
        'it is now being prepared for publication as an IEEE research paper.',
        styles['body']))

    # ── PIPELINE DIAGRAM ─────────────────────────────────────────────────────────
    for el in section_header('LangGraph Pipeline Architecture', styles, ACCENT_BLUE):
        story.append(el)
    story.append(pipeline_diagram())
    story.append(Spacer(1, 0.35 * cm))

    # ── DEVELOPMENT TIMELINE ─────────────────────────────────────────────────────
    for el in section_header('Development Journey — 6 Phases', styles):
        story.append(el)
    for el in timeline_table(styles):
        story.append(el)
    story.append(Spacer(1, 0.35 * cm))

    # ── HOW IT WORKS ─────────────────────────────────────────────────────────────
    for el in section_header('How It Works — System Workflow', styles, PURPLE):
        story.append(el)
    for el in workflow_cards(styles):
        story.append(el)

    # ── DISCORD ALERT PREVIEW ────────────────────────────────────────────────────
    for el in section_header('Sample Discord Alert (Live Output)', styles, colors.HexColor('#5865F2')):
        story.append(el)
    story.append(discord_preview(styles))
    story.append(Spacer(1, 0.35 * cm))

    # ── SIX DATA SOURCES ─────────────────────────────────────────────────────────
    for el in section_header('Six Data Sources Combined in Every Decision', styles):
        story.append(el)
    for el in data_sources_grid(styles):
        story.append(el)

    # ── RISK MANAGEMENT ──────────────────────────────────────────────────────────
    for el in risk_callout(styles):
        story.append(el)
    story.append(Spacer(1, 0.35 * cm))

    # ── ACCURACY JOURNEY ─────────────────────────────────────────────────────────
    for el in section_header('Signal Accuracy — Engineered from 50% → 65–72%', styles, GREEN):
        story.append(el)
    story.append(accuracy_visual())
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        'The system started at ~50% accuracy (coin-flip level). Through systematic post-mortem '
        'analysis of every losing trade, I identified root causes and engineered specific filters. '
        'Each of the 19 improvements below was built in response to a real observed failure.',
        styles['body']))

    # ── 19 ACCURACY IMPROVEMENTS ─────────────────────────────────────────────────
    for el in section_header('19 Accuracy Improvements — Engineered From Real Losses', styles, RED):
        story.append(el)
    story.append(improvement_table(styles))
    story.append(Spacer(1, 0.35 * cm))

    # ── TECHNOLOGY STACK ─────────────────────────────────────────────────────────
    for el in section_header('Technology Stack', styles):
        story.append(el)
    for el in tech_stack(styles):
        story.append(el)

    # ── KEY LEARNINGS ────────────────────────────────────────────────────────────
    for el in section_header('Key Engineering Learnings', styles, TEAL):
        story.append(el)
    learnings = [
        '<b>LLMs alone are not enough.</b> A 58% LLM confidence signal is meaningless if SPY '
        'is up +1% and the sector is surging — regime-awareness is the single highest-impact layer.',
        '<b>Data freshness beats data quantity.</b> A stale 10-day-old cached price made every '
        'recommendation wrong. Adding a 15-minute TTL fixed it immediately.',
        '<b>Multi-agent state management is non-trivial.</b> LangGraph\'s typed state objects '
        'prevented silent data corruption between nodes when running 5 parallel analyses.',
        '<b>Paper trading reveals what backtests hide.</b> 3 PM signals were technically valid '
        'but never had time to reach targets — discovered only through live paper trading.',
        '<b>Signal quality beats signal quantity.</b> Showing 3 high-confidence signals outperforms '
        '10 medium-confidence ones. The 55% minimum display threshold was the simplest win.',
    ]
    for l in learnings:
        story.append(Paragraph(f'• {l}', styles['bullet']))
    story.append(Spacer(1, 0.25 * cm))

    # ── WHAT'S NEXT ──────────────────────────────────────────────────────────────
    for el in section_header("What's Next", styles):
        story.append(el)
    nexts = [
        ('Alpaca / Robinhood API', 'Live automated order placement with real capital'),
        ('Fine-tuned FinGPT',      'Compare vs GPT-4o-mini on financial reasoning tasks'),
        ('Options flow primary',   'Unusual options activity as the main signal trigger'),
        ('Reinforcement learning', 'Dynamic position sizing based on rolling confidence'),
        ('IEEE Access paper',      'Full academic publication with 30-stock backtest results'),
    ]
    nxt_s1 = ParagraphStyle('ns1', fontName='Helvetica-Bold', fontSize=9.5,
                             textColor=ACCENT_BLUE)
    nxt_s2 = ParagraphStyle('ns2', fontName='Helvetica', fontSize=9.5,
                             textColor=SLATE_600, leading=13)
    for title, body in nexts:
        story.append(Paragraph(
            f'→  <b><font color="#2563EB">{title}:</font></b>  {body}',
            ParagraphStyle('nx', fontName='Helvetica', fontSize=9.5,
                           textColor=SLATE_600, leading=13, leftIndent=6, spaceAfter=4)))

    story.append(Spacer(1, 0.5 * cm))

    # ── FOOTER ───────────────────────────────────────────────────────────────────
    story.append(footer_block(styles))

    doc.build(story)
    print(f'\n✅  Enhanced LinkedIn PDF saved:\n    {OUT_FILE}\n')


if __name__ == '__main__':
    try:
        import reportlab  # noqa
        build_pdf()
    except ImportError:
        import subprocess
        subprocess.run(['pip', 'install', 'reportlab', '-q'])
        build_pdf()
