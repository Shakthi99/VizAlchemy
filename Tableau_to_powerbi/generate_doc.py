"""
Generates the Tableau → Power BI Accelerator Code Walkthrough PDF.
Run: python3 tableau_to_pbi/generate_doc.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Preformatted
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.colors import HexColor
import os

OUTPUT = "/Users/bhargavi.s.lv/Documents/Automation/Fabric+DBX/tableau_to_pbi/Tableau_to_PowerBI_Accelerator_Code_Walkthrough.pdf"

# ── Brand colours ──────────────────────────────────────────────────────────────
C_DARK    = HexColor("#1A1A2E")   # deep navy
C_PRIMARY = HexColor("#16213E")   # dark blue header
C_ACCENT  = HexColor("#0F3460")   # section blue
C_HL      = HexColor("#E94560")   # red accent
C_TEAL    = HexColor("#0A7EA4")   # teal for code/links
C_LIGHT   = HexColor("#F5F7FA")   # light bg for tables
C_MID     = HexColor("#DCE3EE")   # table alternating row
C_WHITE   = colors.white
C_GREY    = HexColor("#6B7280")
C_GREEN   = HexColor("#059669")
C_ORANGE  = HexColor("#D97706")
C_RED     = HexColor("#DC2626")

W, H = A4

# ── Styles ─────────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

def make_style(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=ss[parent], **kw)

S = {
    "cover_title": make_style("cover_title", "Title",
        fontSize=32, leading=40, textColor=C_WHITE, alignment=TA_CENTER,
        fontName="Helvetica-Bold"),
    "cover_sub": make_style("cover_sub",
        fontSize=14, leading=20, textColor=HexColor("#A0AEC0"), alignment=TA_CENTER,
        fontName="Helvetica"),
    "cover_meta": make_style("cover_meta",
        fontSize=10, leading=16, textColor=HexColor("#718096"), alignment=TA_CENTER),
    "h1": make_style("h1", fontSize=20, leading=26, textColor=C_PRIMARY,
        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8,
        borderPad=4),
    "h2": make_style("h2", fontSize=14, leading=20, textColor=C_ACCENT,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6),
    "h3": make_style("h3", fontSize=11, leading=16, textColor=C_DARK,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4),
    "body": make_style("body", fontSize=9.5, leading=15, textColor=C_DARK,
        alignment=TA_JUSTIFY, spaceAfter=6),
    "bullet": make_style("bullet", fontSize=9.5, leading=14, textColor=C_DARK,
        leftIndent=16, bulletIndent=6, spaceAfter=3),
    "bullet2": make_style("bullet2", fontSize=9, leading=13, textColor=C_GREY,
        leftIndent=32, bulletIndent=22, spaceAfter=2),
    "code": make_style("code", fontSize=7.8, leading=12, textColor=HexColor("#1E293B"),
        fontName="Courier", backColor=HexColor("#F1F5F9"),
        leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4,
        borderColor=HexColor("#CBD5E1"), borderWidth=0.5, borderPad=6),
    "code_inline": make_style("code_inline", fontSize=9, textColor=C_TEAL,
        fontName="Courier"),
    "caption": make_style("caption", fontSize=8, leading=12, textColor=C_GREY,
        alignment=TA_CENTER, fontName="Helvetica-Oblique", spaceAfter=8),
    "note": make_style("note", fontSize=9, leading=13, textColor=HexColor("#92400E"),
        backColor=HexColor("#FFFBEB"), leftIndent=12, rightIndent=12,
        borderColor=HexColor("#F59E0B"), borderWidth=1, borderPad=6,
        spaceBefore=6, spaceAfter=6),
    "toc": make_style("toc", fontSize=9.5, leading=16, textColor=C_ACCENT,
        leftIndent=0),
    "toc2": make_style("toc2", fontSize=8.5, leading=14, textColor=C_GREY,
        leftIndent=16),
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def H1(text, story):
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT, spaceAfter=4))
    story.append(Paragraph(text, S["h1"]))

def H2(text, story):
    story.append(Paragraph(text, S["h2"]))

def H3(text, story):
    story.append(Paragraph(text, S["h3"]))

def P(text, story, style="body"):
    story.append(Paragraph(text, S[style]))

def B(text, story, level=1):
    sty = "bullet" if level == 1 else "bullet2"
    bullet = "•" if level == 1 else "◦"
    story.append(Paragraph(f"{bullet}  {text}", S[sty]))

def CODE(text, story):
    story.append(Preformatted(text, S["code"]))

def SP(story, n=6):
    story.append(Spacer(1, n))

def HR(story):
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MID, spaceAfter=4))

def simple_table(headers, rows, story, col_widths=None, stripe=True):
    data = [headers] + rows
    style_cmds = [
        ("BACKGROUND",  (0, 0), (-1, 0),  C_PRIMARY),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  8),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUND",(0, 0), (-1, 0), C_PRIMARY),
        ("GRID",        (0, 0), (-1, -1), 0.4, HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1),  4),
    ]
    if stripe:
        for i in range(1, len(data)):
            bg = C_LIGHT if i % 2 == 0 else C_WHITE
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    SP(story, 8)

def note_box(text, story):
    story.append(Paragraph(f"<b>Note:</b> {text}", S["note"]))

# ── Cover page ─────────────────────────────────────────────────────────────────

def cover_page(story):
    # Dark background rectangle simulated with a table
    cover_data = [[""]]
    cover_table = Table(cover_data, colWidths=[W - 4*cm], rowHeights=[3*cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
    ]))

    SP(story, 60)
    story.append(Paragraph("Tableau → Power BI", S["cover_title"]))
    story.append(Paragraph("Migration Accelerator", S["cover_title"]))
    SP(story, 16)
    story.append(HRFlowable(width="60%", thickness=2, color=C_HL,
                             hAlign="CENTER", spaceAfter=16))
    story.append(Paragraph("Complete Code Walkthrough", S["cover_sub"]))
    SP(story, 12)
    story.append(Paragraph(
        "Architecture · Data Models · Stage-by-Stage Guide · Bug Fixes · Deployment",
        S["cover_meta"]))
    SP(story, 30)
    story.append(Paragraph("BI Manager's Technical Reference", S["cover_meta"]))
    story.append(Paragraph("Version 1.0  |  June 2026", S["cover_meta"]))
    story.append(PageBreak())


# ── TOC ────────────────────────────────────────────────────────────────────────

def toc_page(story):
    story.append(Paragraph("Table of Contents", S["h1"]))
    HR(story)
    SP(story, 6)
    sections = [
        ("1",  "Executive Summary"),
        ("2",  "Architecture Overview"),
        ("3",  "File Structure"),
        ("4",  "Data Models — utils/models.py"),
        ("5",  "Stage 1 — Parser Agent — parsers/twb_parser.py"),
        ("6",  "Stage 2 — Power Query M Generator — generators/mquery_generator.py"),
        ("7",  "Stage 3 — DAX Generator — generators/dax_generator.py"),
        ("8",  "Stage 4 — Visual Generator — generators/visual_generator.py"),
        ("9",  "Stage 5 — PBIX Assembler — generators/pbix_assembler.py"),
        ("10", "Stage 6 — Publisher — generators/pbi_publisher.py"),
        ("11", "Validator — validators/coverage_validator.py"),
        ("12", "Report Writer — generators/report_writer.py"),
        ("13", "Pipeline Orchestrator — pipeline.py"),
        ("14", "CLI — cli.py"),
        ("15", "Mapping Tables — utils/mappings.py"),
        ("16", "Bug Fixes — Code Review Findings"),
        ("17", "Enhancement Roadmap"),
        ("18", "End-to-End Example Walkthrough"),
        ("19", "Deployment Guide"),
        ("20", "Glossary"),
    ]
    toc_data = [[Paragraph(f"<b>{n}</b>", S["toc"]),
                 Paragraph(t, S["toc"])] for n, t in sections]
    toc_table = Table(toc_data, colWidths=[1.2*cm, 14*cm])
    toc_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LINEBELOW", (0,0), (-1,-1), 0.3, HexColor("#E2E8F0")),
    ]))
    story.append(toc_table)
    story.append(PageBreak())


# ── Section 1: Executive Summary ───────────────────────────────────────────────

def sec1(story):
    H1("1. Executive Summary", story)
    P("The <b>Tableau to Power BI Migration Accelerator</b> is a standalone Python tool that "
      "automates the conversion of Tableau workbooks (.twb / .twbx) into fully deployable "
      "Power BI assets. It handles data connections, calculated field translation, visual "
      "layout mapping, PBIX file assembly, and direct publishing to the Power BI Service — "
      "all without opening Power BI Desktop.", story)
    SP(story)
    H2("Key Capabilities", story)
    B("<b>75% automation coverage</b> — pattern-based DAX translation handles the majority of Tableau formulas without human input.", story)
    B("<b>LLM fallback</b> — complex LOD expressions and table calculations are sent to Claude Sonnet or GPT-4o when pattern matching fails.", story)
    B("<b>Touchless publish</b> — assembled .pbix files are uploaded directly to Power BI Service via REST API using a Service Principal.", story)
    B("<b>XMLA/Fabric path</b> — for Premium and Fabric capacities, the semantic model (BIM) is deployed via the XMLA endpoint using Tabular Editor CLI.", story)
    B("<b>Batch mode</b> — an entire folder of workbooks can be migrated and published in a single command.", story)
    B("<b>Validation reporting</b> — every migration produces coverage metrics, a manual review checklist, and a full field lineage CSV.", story)
    SP(story)
    H2("Target Audience", story)
    B("<b>BI Managers</b> — understand automation coverage, review flagged items, oversee migration programmes.", story)
    B("<b>Data Engineers</b> — extend the pattern catalog, wire up LLM keys, configure CI/CD pipelines.", story)
    B("<b>Power BI Developers</b> — use generated DAX, M queries, and layout JSON as a starting scaffold.", story)
    SP(story)
    H2("Technology Stack", story)
    simple_table(
        ["Component", "Technology", "Purpose"],
        [
            ["Parsing", "defusedxml / ElementTree", "Safe XML parsing of .twb files"],
            ["Data Models", "Pydantic v2", "Typed IR and output schemas"],
            ["DAX Translation", "Regex + Claude Sonnet / GPT-4o", "Pattern engine + LLM fallback"],
            ["M Query Generation", "String templates", "Power Query source code"],
            ["PBIX Assembly", "zipfile (stdlib)", "Builds deployable PBIX ZIP"],
            ["BIM Generation", "JSON", "Tabular model for XMLA deployment"],
            ["Publishing", "Power BI REST API + MSAL", "Touchless cloud deployment"],
            ["CLI", "Click", "Command-line interface"],
            ["Logging", "Python logging", "Structured progress output"],
        ],
        story,
        col_widths=[3.5*cm, 5.5*cm, 8.5*cm],
    )
    story.append(PageBreak())


# ── Section 2: Architecture ─────────────────────────────────────────────────────

def sec2(story):
    H1("2. Architecture Overview", story)
    H2("6-Stage Pipeline", story)
    CODE("""\
  .twb / .twbx  (Tableau Workbook File)
        |
        v
  +-------------------+
  |  Stage 1: PARSER  |   twb_parser.py
  |  XML -> TableauIR |   Extracts datasources, worksheets,
  +-------------------+   dashboards, calculated fields
        |
        v
  +---------------------+   +---------------------+
  |  Stage 2: M QUERY   |   |  Stage 3: DAX GEN   |
  |  mquery_generator   |   |  dax_generator.py   |
  |  Power Query M code |   |  Pattern + LLM DAX  |
  +---------------------+   +---------------------+
        |                           |
        +----------+  +-------------+
                   |  |
                   v  v
  +---------------------------+
  |  Stage 4: VISUAL MAPPER   |   visual_generator.py
  |  Worksheets -> PBIVisual  |   Tableau marks -> PBI visuals
  |  Layout coordinate xform  |   Dashboard zones -> canvas %
  +---------------------------+
        |
        v
  +---------------------------+
  |  Stage 5: PBIX ASSEMBLER  |   pbix_assembler.py
  |  .pbix ZIP construction   |   DataMashup + Report/Layout
  |  .bim Tabular model JSON  |   + BIM for XMLA deployment
  +---------------------------+
        |
        v
  +---------------------------+
  |  Stage 6: PUBLISHER       |   pbi_publisher.py
  |  REST API PBIX import     |   Optional — needs workspace
  |  XMLA BIM deploy          |   + PBI_TENANT/CLIENT env vars
  |  Dataset refresh trigger  |
  +---------------------------+
        |
        v
  Live Power BI Report URL  ✓
    """, story)
    SP(story)
    H2("Module Dependency Map", story)
    CODE("""\
  cli.py
    └── pipeline.py
          ├── parsers/twb_parser.py
          │     └── utils/models.py
          ├── generators/mquery_generator.py
          │     ├── utils/models.py
          │     └── utils/mappings.py
          ├── generators/dax_generator.py
          │     ├── utils/models.py
          │     └── utils/mappings.py
          ├── generators/visual_generator.py
          │     ├── utils/models.py
          │     └── utils/mappings.py
          ├── generators/pbix_assembler.py
          │     └── utils/models.py
          ├── generators/pbi_publisher.py   (optional)
          ├── generators/report_writer.py
          │     ├── utils/models.py
          │     └── validators/coverage_validator.py
          └── validators/coverage_validator.py
                └── utils/models.py
    """, story)
    story.append(PageBreak())


# ── Section 3: File Structure ──────────────────────────────────────────────────

def sec3(story):
    H1("3. File Structure", story)
    CODE("""\
tableau_to_pbi/
│
├── __init__.py              Package marker
├── __main__.py              Enables: python3 -m tableau_to_pbi
├── cli.py                   Click CLI — migrate / migrate-batch commands
├── pipeline.py              Orchestrates all 6 stages
│
├── parsers/
│   └── twb_parser.py        Parses .twb/.twbx XML -> TableauIR
│
├── generators/
│   ├── mquery_generator.py  Tableau datasources -> Power Query M
│   ├── dax_generator.py     Calculated fields -> DAX measures
│   ├── visual_generator.py  Worksheets + dashboards -> PBI visuals
│   ├── pbix_assembler.py    Assembles .pbix ZIP + .bim JSON
│   ├── pbi_publisher.py     REST API / XMLA publish to PBI Service
│   └── report_writer.py     Writes all output artefacts to disk
│
├── validators/
│   └── coverage_validator.py  Field/visual/layout coverage checks
│
├── utils/
│   ├── models.py            Pydantic data models (IR + PBI output)
│   └── mappings.py          Static mapping tables (visuals, DAX, M)
│
├── input_twb/               Drop .twb / .twbx files here
│   └── sample_sales_dashboard.twb   Bundled sample workbook
│
└── output_pbi/              Generated artefacts (auto-created)
    └── {WorkbookName}/
        ├── {name}.pbix            Deployable Power BI file
        ├── {name}.bim             Tabular model (XMLA)
        ├── powerquery/*.pq        M query files
        ├── dax/measures.dax       DAX measures
        ├── layout/report_pages.json
        ├── ir/{name}.ir.json      Intermediate Representation
        └── migration_report/
            ├── summary.md
            ├── manual_review.md
            └── field_mapping.csv
    """, story)
    story.append(PageBreak())


# ── Section 4: Data Models ─────────────────────────────────────────────────────

def sec4(story):
    H1("4. Data Models — utils/models.py", story)
    P("All data structures are defined as <b>Pydantic v2 BaseModel</b> classes. This gives "
      "automatic validation, type coercion, and JSON serialisation (used for the IR output "
      "and layout files). There are two groups: Tableau IR models (what the parser produces) "
      "and Power BI output models (what the generators produce).", story)
    SP(story)
    H2("Tableau IR Models", story)

    H3("TableauIR  —  Root object", story)
    simple_table(
        ["Field", "Type", "Description"],
        [
            ["workbook_name", "str", "Stem of the source file (no extension)"],
            ["source_file", "str", "Absolute path to the .twb/.twbx"],
            ["datasources", "list[TableauDataSource]", "All data connections in the workbook"],
            ["worksheets", "list[TableauWorksheet]", "All individual chart sheets"],
            ["dashboards", "list[TableauDashboard]", "Dashboard layout definitions"],
            ["parameters", "list[TableauParameter]", "Workbook-level parameters"],
        ],
        story, col_widths=[3.5*cm, 4.5*cm, 9.5*cm])

    H3("TableauDataSource", story)
    simple_table(
        ["Field", "Type", "Description"],
        [
            ["name", "str", "Internal Tableau name (used for field references)"],
            ["caption", "str", "Display name shown in Tableau UI"],
            ["connection_type", "str", "sqlserver / mysql / postgres / csv / excel etc."],
            ["server", "str", "Hostname extracted from connection XML"],
            ["database", "str", "Database name"],
            ["schema_name", "str", "Schema (e.g. dbo)"],
            ["table", "str", "Base table name (empty if custom SQL)"],
            ["custom_sql", "str", "Full SQL text when relation type = text"],
            ["columns", "list[TableauColumn]", "All fields including calculated fields"],
            ["joins", "list[TableauJoin]", "Join definitions between tables"],
        ],
        story, col_widths=[3.5*cm, 4*cm, 10*cm])

    H3("TableauColumn", story)
    simple_table(
        ["Field", "Type", "Description"],
        [
            ["name", "str", "Internal name (brackets stripped)"],
            ["caption", "str", "Display label"],
            ["datatype", "str", "string / integer / real / date / datetime / boolean"],
            ["role", "str", "dimension or measure"],
            ["type", "str", "nominal / ordinal / quantitative / temporal"],
            ["formula", "str", "Tableau expression (empty for raw fields)"],
            ["is_calculated", "bool", "True if formula is non-empty"],
            ["hidden", "bool", "Whether hidden in Tableau UI"],
        ],
        story, col_widths=[3.5*cm, 3*cm, 11*cm])

    H3("TableauWorksheet", story)
    simple_table(
        ["Field", "Type", "Description"],
        [
            ["name", "str", "Sheet tab name"],
            ["datasource", "str", "Datasource name this sheet draws from"],
            ["mark_type", "str", "bar / line / circle / text / pie / map / gantt etc."],
            ["encodings", "list[TableauEncoding]", "Shelf assignments (rows, cols, color, size ...)"],
            ["filters", "list[TableauFilter]", "Filters applied to this worksheet"],
            ["rows / cols", "list[str]", "Field names on Rows and Columns shelves"],
        ],
        story, col_widths=[3.5*cm, 4.5*cm, 9.5*cm])

    H3("TableauEncoding", story)
    P("Represents a single shelf assignment in Tableau's Marks card.", story)
    simple_table(
        ["Field", "Type", "Description"],
        [
            ["shelf", "str", "rows / cols / color / size / label / detail / tooltip / filter"],
            ["field", "str", "Field name (brackets stripped)"],
            ["aggregation", "str", "SUM / AVG / COUNT / COUNTD / MIN / MAX / ATTR / NONE"],
            ["alias", "str", "Optional display alias"],
        ],
        story, col_widths=[3*cm, 3*cm, 11.5*cm])

    H3("Power BI Output Models", story)
    simple_table(
        ["Model", "Key Fields", "Purpose"],
        [
            ["MQueryTable", "table_name, m_expression, connection_type", "One Power Query M file per datasource"],
            ["DAXMeasure", "name, expression, confidence, needs_review", "One DAX measure (calculated or implicit)"],
            ["PBIVisual", "visual_type, x/y/w/h_pct, fields, filters", "One visual on a report page"],
            ["PBIReportPage", "name, visuals, source_dashboard", "One Power BI report page"],
            ["PBIOutput", "m_queries, dax_measures, report_pages", "Root container for all PBI artefacts"],
        ],
        story, col_widths=[3.5*cm, 6.5*cm, 7.5*cm])
    story.append(PageBreak())


# ── Section 5: Parser ──────────────────────────────────────────────────────────

def sec5(story):
    H1("5. Stage 1 — Parser Agent — parsers/twb_parser.py", story)
    P("The parser is the entry point for every migration. It reads a Tableau workbook and "
      "produces a fully validated <b>TableauIR</b> object that all downstream stages consume.", story)

    H2("File Format Handling", story)
    simple_table(
        ["Format", "Extension", "How it is read"],
        [
            [".twb", "Plain XML", "Read as UTF-8 text, parse with ElementTree"],
            [".twbx", "ZIP archive", "Open with zipfile, find the inner .twb, decode UTF-8"],
        ],
        story, col_widths=[2.5*cm, 3.5*cm, 11.5*cm])

    H2("Security — XXE Prevention", story)
    P("The parser imports <b>defusedxml</b> instead of the standard library's ElementTree. "
      "This prevents XML External Entity (XXE) attacks — an attacker could craft a .twb file "
      "that reads local files (e.g. /etc/passwd) through XML entity expansion. defusedxml "
      "disables external entity resolution. If defusedxml is not installed, the parser falls "
      "back gracefully with a logged warning.", story)
    CODE("""\
try:
    from defusedxml import ElementTree as ET  # XXE-safe
except ImportError:
    from xml.etree import ElementTree as ET   # fallback with warning
    """, story)

    H2("Helper Functions", story)
    H3("_attr(elem, *keys, default='')", story)
    P("Tries each key in order and returns the first non-empty attribute value. "
      "Used throughout to handle Tableau's inconsistent attribute naming "
      "(e.g. 'server' vs 'servername').", story)

    H3("_norm_name(name)", story)
    P("Strips Tableau's internal bracket notation. Examples:", story)
    CODE("""\
_norm_name("[Sales]")             -> "Sales"
_norm_name("[Orders].[Order ID]") -> "Order ID"
_norm_name("[Customer Name]")     -> "Customer Name"
    """, story)

    H2("BUG FIX — _split_shelf() — Depth-aware Comma Split", story)
    P("Tableau shelf text like <b>SUM([Sales]),DATEADD('month',-1,[Order Date])</b> "
      "contains commas <i>inside</i> function arguments. The original code used "
      "<font face='Courier'>text.split(',')</font> which would incorrectly split "
      "DATEADD into three tokens. The fix tracks parenthesis depth:", story)
    CODE("""\
def _split_shelf(text: str) -> list[str]:
    parts, depth, buf = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1; buf.append(ch)
        elif ch == ")":
            depth -= 1; buf.append(ch)
        elif ch == "," and depth == 0:   # only split at top level
            parts.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf: parts.append("".join(buf).strip())
    return [p for p in parts if p]
    """, story)

    H2("BUG FIX — _get_field_name() — Nested Expression Unwrapping", story)
    P("The original single-unwrap logic broke on nested aggregations like "
      "<b>SUM(YEAR([Order Date]))</b>. The fix iteratively strips outer "
      "function wrappers until a [FieldName] bracket is reached:", story)
    CODE("""\
def _get_field_name(field_ref: str) -> str:
    inner = field_ref.strip()
    for _ in range(5):                     # max 5 nesting levels
        m = re.match(r"^[A-Za-z_]+\s*\((.+)\)$", inner)
        if not m: break
        inner = m.group(1).strip()
        if inner.startswith("["): break    # reached the field name
    return _norm_name(inner)
    """, story)

    H2("Parsing Flow", story)
    simple_table(
        ["Function", "Input", "Output"],
        [
            ["parse_twb()", "Path to .twb/.twbx", "TableauIR (root object)"],
            ["_parse_datasource()", "datasource XML element", "TableauDataSource"],
            ["_parse_join()", "relation XML element", "list[TableauJoin]"],
            ["_parse_worksheet()", "worksheet XML element", "TableauWorksheet"],
            ["_parse_dashboard()", "dashboard XML element", "TableauDashboard"],
            ["_parse_parameters()", "root XML element", "list[TableauParameter]"],
        ],
        story, col_widths=[4*cm, 4.5*cm, 9*cm])
    story.append(PageBreak())


# ── Section 6: M Query ─────────────────────────────────────────────────────────

def sec6(story):
    H1("6. Stage 2 — Power Query M Generator — generators/mquery_generator.py", story)
    P("Converts each TableauDataSource into a complete Power Query M expression "
      "that can be pasted directly into Power BI Desktop's Advanced Editor "
      "or embedded in the DataMashup of a .pbix file.", story)

    H2("Connector Mapping — CONN_TYPE_MAP", story)
    simple_table(
        ["Tableau Type", "M Source Function", "PBI Mode"],
        [
            ["sqlserver", 'Sql.Database("{server}", "{database}")', "DirectQuery"],
            ["mysql",     'MySQL.Database("{server}", "{database}")', "DirectQuery"],
            ["postgres",  'PostgreSQL.Database("{server}", "{database}")', "DirectQuery"],
            ["oracle",    'Oracle.Database("{server}")', "DirectQuery"],
            ["bigquery",  'GoogleBigQuery.Database()', "Import"],
            ["snowflake", 'Snowflake.Databases("{server}")', "DirectQuery"],
            ["redshift",  'AmazonRedshift.Database("{server}", "{database}")', "Import"],
            ["csv",       'Csv.Document(File.Contents("{table}"))', "Import"],
            ["excel",     'Excel.Workbook(File.Contents("{table}"), null, true)', "Import"],
            ["unknown",   '/* TODO: configure data source */', "Import"],
        ],
        story, col_widths=[3*cm, 8.5*cm, 3.5*cm])

    H2("Custom SQL Handling", story)
    P("When a Tableau datasource uses Custom SQL (relation type='text'), the "
      "generator emits a <b>Value.NativeQuery</b> call with query folding enabled:", story)
    CODE("""\
let
    Source = Sql.Database("server", "SalesDB"),
    Data   = Value.NativeQuery(Source,
                 "SELECT * FROM dbo.Orders WHERE active = 1",
                 null, [EnableFolding=true])
in
    Data
    """, story)

    H2("BUG FIX — Missing ExpandTableColumn", story)
    P("Power BI's <b>Table.NestedJoin</b> does NOT expose joined columns directly. "
      "It creates a new column containing a nested Table object. Without a subsequent "
      "<b>Table.ExpandTableColumn</b> step, users see an unexpanded [Table] column "
      "instead of the joined fields. The fix adds the expand step automatically:", story)
    CODE("""\
# Step 1: Join
Joined_1 = Table.NestedJoin(
    PreviousStep, {"customer_id"},
    Customers,   {"id"},
    "Customers_data", JoinKind.LeftOuter
),

# Step 2: Expand (the missing step, now added)
Expanded_1 = Table.ExpandTableColumn(
    Joined_1, "Customers_data",
    Table.ColumnNames(Customers),
    List.Transform(Table.ColumnNames(Customers), each "Customers." & _)
),
    """, story)
    P("The prefix <font face='Courier'>Customers.</font> is added to each expanded "
      "column name to avoid collisions when multiple tables have identically named columns.", story)
    story.append(PageBreak())


# ── Section 7: DAX Generator ───────────────────────────────────────────────────

def sec7(story):
    H1("7. Stage 3 — DAX Generator — generators/dax_generator.py", story)
    P("The DAX generator is the most complex stage. It translates Tableau's expression "
      "language into DAX using a two-tier strategy: a fast regex pattern engine handles "
      "the majority of formulas; an LLM call handles anything the patterns cannot match.", story)

    H2("Two-Tier Translation Strategy", story)
    CODE("""\
Tableau Formula
      |
      v
  [Tier 1] _apply_pattern()  -- regex direct match
      |
      | No match
      v
  [Tier 1b] _translate_formula() recursive substitution loop
      |         Replaces sub-expressions iteratively (max 10 passes)
      |
      | confidence == 0.0 AND use_llm == True
      v
  [Tier 2] _llm_translate()  -- LLM call (Anthropic -> OpenAI cascade)
      |
      v
  DAXMeasure(name, expression, confidence, needs_review)
    """, story)

    H2("FORMULA_PATTERNS Catalog — 40+ Patterns in 7 Categories", story)
    simple_table(
        ["Category", "Examples", "Confidence"],
        [
            ["Basic aggregates",   "SUM, AVG, COUNT, COUNTD, MIN, MAX, MEDIAN", "0.90–0.95"],
            ["Null handling",      "ISNULL, ZN, IFNULL", "0.85–0.90"],
            ["String functions",   "UPPER, LOWER, TRIM, LEN, LEFT, RIGHT, MID,\nCONTAINS, STARTSWITH, ENDSWITH, REPLACE", "0.80–0.95"],
            ["Date functions",     "TODAY, NOW, YEAR, MONTH, DAY, DATETRUNC,\nDATEADD, DATEDIFF", "0.80–0.95"],
            ["LOD expressions",    "FIXED, INCLUDE, EXCLUDE", "0.55–0.65"],
            ["Table calculations", "RUNNING_SUM, WINDOW_SUM, RANK, RUNNING_AVG", "0.45–0.55"],
            ["Conditional",        "IF/THEN/ELSE/END, IIF, ATTR", "0.75–0.85"],
        ],
        story, col_widths=[3.5*cm, 8.5*cm, 2.5*cm])

    H2("Pattern Tuple Structure", story)
    P("Each entry in FORMULA_PATTERNS is a 4-tuple:", story)
    CODE("""\
(
  r"SUM\(\[(.+?)\]\)",      # regex pattern (capture groups map to {field})
  "SUM({table}[{field}])",   # DAX template with {placeholder} substitution
  0.95,                      # confidence score (0.0 - 1.0)
  ""                         # review note (empty = no review needed)
)
    """, story)

    H2("BUG FIX — Python Closure over Loop Variable", story)
    P("The recursive substitution loop calls <b>re.sub(pattern, _replacer, ...)</b> "
      "for each pattern. The _replacer function was defined inside the for loop. "
      "In Python, closures capture variables by <i>reference</i>, not by value. "
      "By the time re.sub() calls _replacer, the loop variable <font face='Courier'>template</font> "
      "has already advanced to the <i>last</i> pattern in the list — every substitution used the "
      "wrong template silently.", story)
    CODE("""\
# BEFORE (bug): closure captures template by reference
for pattern, template, confidence, note in FORMULA_PATTERNS:
    def _replacer(m):
        dax = template        # WRONG: always the last template

# AFTER (fix): default arguments capture values at definition time
for pattern, template, confidence, note in FORMULA_PATTERNS:
    def _replacer(m, _tmpl=template, _conf=confidence, _note=note):
        dax = _tmpl           # CORRECT: captured at loop iteration
    """, story)

    H2("LOD Expression Translation", story)
    P("Tableau's Level of Detail expressions are the hardest constructs to translate. "
      "They evaluate at a different grain than the current visual filter context.", story)
    simple_table(
        ["Tableau LOD", "Generated DAX", "Confidence"],
        [
            ["{FIXED [Region] : SUM([Sales])}",
             "CALCULATE(SUM(T[Sales]),\n  REMOVEFILTERS(), VALUES(T[Region]))",
             "0.65"],
            ["{INCLUDE [Product] : AVG([Price])}",
             "CALCULATE(AVERAGE(T[Price]),\n  SUMMARIZE(T, T[Product]))",
             "0.55"],
            ["{EXCLUDE [Month] : SUM([Sales])}",
             "CALCULATE(SUM(T[Sales]),\n  REMOVEFILTERS(T[Month]))",
             "0.60"],
        ],
        story, col_widths=[5.5*cm, 7*cm, 2*cm])

    note_box("All LOD expressions are flagged for human review regardless of confidence score "
             "because DAX filter context semantics differ fundamentally from Tableau's "
             "LOD evaluation order.", story)

    H2("LLM Fallback — _llm_translate()", story)
    P("When pattern matching yields confidence 0.0 AND use_llm=True, the formula is "
      "sent to an LLM with a structured prompt. The cascade tries Anthropic first "
      "(Claude Sonnet — matches the project stack), then falls back to OpenAI (GPT-4o), "
      "then returns a TODO comment if neither key is configured.", story)
    CODE("""\
prompt = f\"\"\"
Convert this Tableau formula to a DAX measure expression.
Table name in the data model: {table}
Tableau formula:
{formula}

Return ONLY the DAX expression, no explanation.
\"\"\"
    """, story)
    story.append(PageBreak())


# ── Section 8: Visual Generator ───────────────────────────────────────────────

def sec8(story):
    H1("8. Stage 4 — Visual Generator — generators/visual_generator.py", story)
    P("Maps Tableau worksheets and dashboard zone positions into Power BI "
      "PBIVisual and PBIReportPage objects.", story)

    H2("Visual Type Mapping — MARK_TO_VISUAL", story)
    simple_table(
        ["Tableau Mark", "Power BI Visual", "Confidence", "Notes"],
        [
            ["bar",        "barChart",    "0.95", ""],
            ["bar_h",      "barChart",    "0.90", "Set orientation=horizontal"],
            ["line",       "lineChart",   "0.95", ""],
            ["area",       "areaChart",   "0.90", ""],
            ["circle",     "scatterChart","0.85", ""],
            ["square",     "scatterChart","0.80", "Map shape to scatter"],
            ["text",       "tableEx",     "0.85", ""],
            ["pie",        "pieChart",    "0.90", ""],
            ["map / filled_map", "filledMap", "0.80", "Verify geo field"],
            ["symbol_map", "map",         "0.75", "Verify lat/lon fields"],
            ["gantt",      "gantt",       "0.55", "Requires AppSource visual"],
            ["polygon",    "shapeMap",    "0.50", "Requires custom shape file"],
            ["density",    "map",         "0.45", "Density layer not native"],
            ["automatic",  "barChart",    "0.70", "Tableau chose automatic — review"],
        ],
        story, col_widths=[3.5*cm, 3.5*cm, 2.5*cm, 7*cm])

    H2("Coordinate Normalisation", story)
    P("Tableau stores zone positions in absolute pixels relative to the dashboard canvas. "
      "Power BI uses percentage-based positioning relative to the report canvas (1280 × 720 pts). "
      "The conversion is straightforward:", story)
    CODE("""\
# Tableau dashboard is e.g. 1366 x 768 px
# Zone at x=683, y=0, w=683, h=384

x_pct = round((683 / 1366) * 100, 2)   # = 50.0%
y_pct = round((0   / 768)  * 100, 2)   # = 0.0%
w_pct = round((683 / 1366) * 100, 2)   # = 50.0%
h_pct = round((384 / 768)  * 100, 2)   # = 50.0%
    """, story)

    H2("Field Well Mapping — SHELF_TO_WELL", story)
    simple_table(
        ["Tableau Shelf", "Power BI Field Well"],
        [
            ["rows",    "values"],
            ["cols",    "axis"],
            ["color",   "legend"],
            ["size",    "size"],
            ["label",   "labels"],
            ["detail",  "details"],
            ["tooltip", "tooltips"],
            ["filter",  "filters"],
        ],
        story, col_widths=[4*cm, 13.5*cm])

    H2("Orphan Worksheet Handling", story)
    P("Worksheets that are not placed on any dashboard are still migrated — "
      "each becomes its own standalone report page with default 50×50% visual placement "
      "and is flagged in the migration report for manual positioning.", story)
    story.append(PageBreak())


# ── Section 9: PBIX Assembler ─────────────────────────────────────────────────

def sec9(story):
    H1("9. Stage 5 — PBIX Assembler — generators/pbix_assembler.py", story)
    P("This stage eliminates the need for Power BI Desktop entirely. It constructs "
      "a valid .pbix ZIP file from the generated M queries and report layout JSON.", story)

    H2("PBIX File Format", story)
    P("A .pbix file is a <b>renamed ZIP archive</b> with a specific set of mandatory files:", story)
    simple_table(
        ["File inside ZIP", "Content", "Built by"],
        [
            ["[Content_Types].xml", "MIME type manifest", "Hard-coded template"],
            ["Version", "Format version string (4.21)", "Hard-coded constant"],
            ["SecurityBindings", "Empty placeholder", "Empty string"],
            ["DataMashup", "ZIP-in-ZIP containing Power Query M", "_build_mashup_zip()"],
            ["Report/Layout", "JSON: pages, visuals, positions", "_build_layout()"],
        ],
        story, col_widths=[4.5*cm, 6*cm, 5*cm])

    H2("DataMashup — ZIP inside the PBIX", story)
    P("The DataMashup entry is itself a ZIP archive containing:", story)
    CODE("""\
DataMashup (binary ZIP)
  ├── [Content_Types].xml         MIME types for .m files
  ├── Section1.m                  Combined Power Query M section document
  ├── Formulas/Section1/          Legacy path (older PBI Service versions)
  │   └── Package/Formulas/
  │       └── Section1.m          Same content — duplicate for compatibility
  └── Config/Package.json         Minimal metadata {"version": "2.0"}
    """, story)
    P("The Section1.m file uses Tableau section syntax with each datasource "
      "as a named <font face='Courier'>shared</font> query:", story)
    CODE("""\
section Section1;

shared #"Orders" =
    let
        Source = Sql.Database("sql-prod.company.com", "SalesDB"),
        Table  = Source{[Schema="dbo", Item="Orders"]}[Data]
    in
        Table;

shared #"Customers" =
    let
        Source = Sql.Database("sql-prod.company.com", "SalesDB"),
        Table  = Source{[Schema="dbo", Item="Customers"]}[Data]
    in
        Table;
    """, story)

    H2("Report/Layout JSON", story)
    P("The layout follows Power BI's internal schema:", story)
    CODE("""\
{
  "id": 0,
  "sections": [
    {
      "id": 0,
      "name": "page0001",
      "displayName": "Executive Dashboard",
      "visualContainers": [
        {
          "x": 0, "y": 0, "z": 0,
          "width": 640, "height": 360,
          "config": "{ ... stringified visual JSON ... }",
          "filters": "[]"
        }
      ]
    }
  ]
}
    """, story)
    note_box("The config field is a JSON string (stringified JSON, not a nested object). "
             "This is a quirk of the Power BI internal format — the outer Layout JSON "
             "contains JSON-encoded strings for per-visual configuration.", story)

    H2("BIM — Tabular Model for XMLA Deployment", story)
    P("<b>build_bim()</b> generates a JSON file in the Tabular Model BIM format, "
      "which is the format understood by Tabular Editor CLI and the XMLA endpoint. "
      "It includes:", story)
    B("A hidden <b>_Measures</b> table containing all DAX measures with their source formula, confidence score, and review flag as annotations.", story)
    B("One table entry per datasource, with partition mode set to import or directQuery based on the CONN_TYPE_MAP setting.", story)
    B("Compatibility level 1567 (Power BI Premium / Fabric).", story)
    story.append(PageBreak())


# ── Section 10: Publisher ──────────────────────────────────────────────────────

def sec10(story):
    H1("10. Stage 6 — Publisher — generators/pbi_publisher.py", story)
    P("The publisher makes the migration completely touchless. When a workspace is "
      "specified, it authenticates, uploads the PBIX, waits for import completion, "
      "and triggers a dataset refresh — returning a live report URL.", story)

    H2("Authentication — Two Paths", story)
    simple_table(
        ["Path", "When Used", "Env Vars Required", "Best For"],
        [
            ["Service Principal\n(client credentials)", "PBI_CLIENT_SECRET is set",
             "PBI_TENANT_ID\nPBI_CLIENT_ID\nPBI_CLIENT_SECRET", "CI/CD pipelines,\nautomated batch runs"],
            ["Device Flow\n(interactive)", "No CLIENT_SECRET",
             "PBI_TENANT_ID\nPBI_CLIENT_ID", "First-time setup,\ndeveloper testing"],
        ],
        story, col_widths=[3.5*cm, 4*cm, 4*cm, 5.5*cm])

    H2("Service Principal Flow", story)
    CODE("""\
POST https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
Body:
  grant_type    = client_credentials
  client_id     = {PBI_CLIENT_ID}
  client_secret = {PBI_CLIENT_SECRET}
  scope         = https://analysis.windows.net/powerbi/api/.default
    """, story)

    H2("Device Flow", story)
    P("When no client secret is set, the user sees:", story)
    CODE("""\
Device-flow auth required:
  → Visit:  https://microsoft.com/devicelogin
  → Code:   ABC123
    """, story)
    P("The MSAL library polls until the user completes browser authentication.", story)

    H2("REST API — PBIX Import", story)
    CODE("""\
POST /v1.0/myorg/groups/{workspace_id}/imports
     ?datasetDisplayName={name}&nameConflict=Overwrite

Content-Type: multipart/form-data
Body: (binary PBIX file)

Response 202:
  { "id": "import-job-guid" }
    """, story)

    H2("Polling — wait_for_import()", story)
    P("Polls every 5 seconds up to 300 seconds:", story)
    CODE("""\
GET /v1.0/myorg/groups/{workspace_id}/imports/{import_id}

Response when complete:
  {
    "importState": "Succeeded",
    "datasets": [{ "id": "...", "name": "..." }],
    "reports":  [{ "id": "...", "name": "..." }]
  }
    """, story)

    H2("XMLA / Tabular Editor CLI", story)
    P("For Premium and Fabric workspaces, the BIM file is deployed via Tabular Editor CLI:", story)
    CODE("""\
TabularEditor model.bim \\
    -D "powerbi://api.powerbi.com/v1.0/myorg/MyWorkspace" \\
    MyDatasetName \\
    -O    # Overwrite existing
    -S    # Deploy schema changes
    -P    # Deploy partition changes
    """, story)

    H2("Full publish() Orchestration", story)
    simple_table(
        ["Step", "Action", "Function"],
        [
            ["1", "Acquire OAuth2 token", "get_token()"],
            ["2", "Resolve workspace name → GUID", "resolve_workspace_id()"],
            ["3a", "Deploy BIM via XMLA (if --xmla set)", "deploy_bim_via_xmla()"],
            ["3b", "Upload PBIX via REST API", "import_pbix()"],
            ["4", "Poll until import complete", "wait_for_import()"],
            ["5", "Trigger dataset refresh", "trigger_refresh()"],
            ["6", "Return live report URL", "Composed from report_id"],
        ],
        story, col_widths=[1.5*cm, 6*cm, 6.5*cm])
    story.append(PageBreak())


# ── Section 11: Validator ──────────────────────────────────────────────────────

def sec11(story):
    H1("11. Validator — validators/coverage_validator.py", story)
    P("The validator audits the generated PBIOutput against the source TableauIR "
      "and produces a structured ValidationReport used to generate the summary.md "
      "and manual_review.md files.", story)

    H2("ValidationIssue", story)
    simple_table(
        ["Field", "Values", "Description"],
        [
            ["severity", "ERROR / WARNING / INFO", "ERROR = must fix; WARNING = should fix; INFO = advisory"],
            ["category", "datasource / field / dax / visual / layout", "Which part of the migration this affects"],
            ["item", "str", "Name of the specific element (measure name, worksheet name etc.)"],
            ["message", "str", "Human-readable description of the issue"],
        ],
        story, col_widths=[2.5*cm, 4.5*cm, 10.5*cm])

    H2("Coverage Metrics", story)
    simple_table(
        ["Metric", "Formula", "Weight"],
        [
            ["Field Coverage %",   "translated_fields / total_calculated_fields × 100", "40%"],
            ["Visual Coverage %",  "visuals_auto / total_visuals × 100", "60%"],
            ["Overall Coverage %", "field_coverage × 0.4 + visual_coverage × 0.6", "—"],
        ],
        story, col_widths=[4*cm, 8*cm, 2.5*cm])

    H2("BUG FIX — visuals_auto Counter", story)
    P("The original code only incremented <font face='Courier'>visuals_auto</font> "
      "for visuals that had <i>no</i> review notes — meaning a bar chart with a minor "
      "note (e.g. 'verify geo field') was counted as zero, deflating the visual coverage "
      "percentage. The fix separates 'mapped' from 'needs review':", story)
    CODE("""\
# BEFORE (bug): flagged visuals excluded from visuals_auto
for vis in all_visuals:
    if vis.needs_review:
        report.visuals_flagged += 1
    else:
        report.visuals_auto += 1    # WRONG: only clean visuals counted

# AFTER (fix): all mapped visuals count toward coverage
for vis in all_visuals:
    report.visuals_auto += 1        # always — represents "mapped"
    if vis.needs_review:
        report.visuals_flagged += 1 # sub-count: mapped but flagged
    """, story)

    H2("Five Validation Checks", story)
    simple_table(
        ["Check", "What It Verifies", "Severity if Failed"],
        [
            ["Datasource coverage", "Every IR datasource has a generated M query", "ERROR"],
            ["Calculated field coverage", "Every calculated field has a DAX measure", "WARNING"],
            ["DAX review flags", "Measures with confidence < 0.70 are flagged", "WARNING"],
            ["DAX zero-confidence", "Measures that could not be translated at all", "ERROR"],
            ["Visual coverage", "Every visual has a mapped type", "WARNING"],
            ["Layout coverage", "Every worksheet placed on a report page", "WARNING"],
            ["Parameter detection", "Tableau parameters need manual What-If setup", "INFO"],
        ],
        story, col_widths=[4*cm, 7.5*cm, 3*cm])
    story.append(PageBreak())


# ── Section 12: Report Writer ──────────────────────────────────────────────────

def sec12(story):
    H1("12. Report Writer — generators/report_writer.py", story)
    P("Writes all generated artefacts to a structured output folder. "
      "Every file is UTF-8 encoded. The writer never overwrites — "
      "running the pipeline twice will overwrite previous outputs silently "
      "(directories are created with exist_ok=True).", story)

    H2("Output Files", story)
    simple_table(
        ["File", "Content", "Primary Consumer"],
        [
            ["{name}.ir.json",     "Full TableauIR as Pydantic JSON", "Debugging / re-run"],
            ["{name}.pbix",        "Deployable Power BI file", "Power BI Service / Desktop"],
            ["{name}.bim",         "Tabular model JSON", "Tabular Editor / XMLA endpoint"],
            ["powerquery/*.pq",    "One M query per datasource", "Power BI Advanced Editor"],
            ["dax/measures.dax",   "All DAX measures with [REVIEW] tags", "DAX Editor / developer"],
            ["layout/report_pages.json", "Visual specs with % coordinates", "Developer reference"],
            ["migration_report/summary.md", "Coverage % + source stats + next steps", "BI Manager"],
            ["migration_report/manual_review.md", "Errors → Warnings → Info items", "Developer"],
            ["migration_report/field_mapping.csv", "10-column Tableau→DAX lineage", "Stakeholder sign-off"],
        ],
        story, col_widths=[4.5*cm, 5.5*cm, 5.5*cm])

    H2("field_mapping.csv — 10-Column Lineage Table", story)
    simple_table(
        ["Column", "Description"],
        [
            ["Source Table",      "Datasource caption or name"],
            ["Tableau Field",     "Field caption or name"],
            ["Type",              "Pydantic datatype (string / real / date etc.)"],
            ["Is Calculated",     "True / False"],
            ["Tableau Formula",   "Original expression (blank for raw fields)"],
            ["DAX Measure",       "Generated DAX measure name"],
            ["DAX Expression",    "First 200 chars of generated DAX"],
            ["Confidence",        "Translation confidence as percentage"],
            ["Needs Review",      "True / False"],
            ["Review Reason",     "Human-readable reason for review flag"],
        ],
        story, col_widths=[3.5*cm, 14*cm])

    H2("BUG FIX — _safe() Filename Sanitisation", story)
    P("The original sanitiser could produce empty strings or all-underscore names "
      "for datasources with non-ASCII display names (e.g. Japanese characters). "
      "This caused a FileNotFoundError when attempting to write the .pq file:", story)
    CODE("""\
# BEFORE (bug): could return "" or "___"
def _safe(name):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

# AFTER (fix): strip leading/trailing underscores, fallback to "unnamed"
def _safe(name):
    result = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
    return result or "unnamed"
    """, story)
    story.append(PageBreak())


# ── Section 13: Pipeline ───────────────────────────────────────────────────────

def sec13(story):
    H1("13. Pipeline Orchestrator — pipeline.py", story)
    P("The pipeline module wires all stages together into a single "
      "<b>migrate_workbook()</b> function and provides a batch wrapper.", story)

    H2("migrate_workbook() — Data Flow", story)
    simple_table(
        ["Stage", "Function Called", "Input", "Output Added to PBIOutput"],
        [
            ["1 — Parse",   "parse_twb()",            "twb_path",      "TableauIR"],
            ["2 — M Query", "generate_m_queries()",   "ir.datasources","m_queries"],
            ["3 — DAX",     "generate_dax_measures()", "ir (full)",    "dax_measures"],
            ["4 — Visuals", "generate_report_pages()", "ir (full)",    "report_pages"],
            ["5 — Assemble","validate() + write_outputs()\n+ assemble_pbix() + build_bim()",
             "ir + PBIOutput", ".pbix + .bim + report files"],
            ["6 — Publish", "publish()  (optional)",  "pbix_path + bim", "report_url in summary"],
        ],
        story, col_widths=[3*cm, 4.5*cm, 3.5*cm, 6.5*cm])

    H2("Function Signature", story)
    CODE("""\
def migrate_workbook(
    twb_path:      Path,               # source .twb or .twbx
    output_dir:    Path,               # base output directory
    use_llm:       bool = True,        # enable LLM fallback for DAX
    workspace:     str  = None,        # PBI workspace name/GUID (enables publish)
    xmla_endpoint: str  = None,        # XMLA URL (Premium/Fabric only)
    overwrite:     bool = True,        # overwrite existing PBI report
) -> dict:                             # summary dict with coverage + URL
    """, story)

    H2("Error Isolation in migrate_batch()", story)
    P("Each workbook is wrapped in a try/except block. A failure in one workbook "
      "logs the error and adds it to the summary dict with an 'error' key, "
      "but processing continues for all remaining files in the batch.", story)
    story.append(PageBreak())


# ── Section 14: CLI ────────────────────────────────────────────────────────────

def sec14(story):
    H1("14. CLI — cli.py", story)
    P("Built on <b>Click</b>. Two commands — <font face='Courier'>migrate</font> (single file) "
      "and <font face='Courier'>migrate-batch</font> (folder) — share publish options "
      "via a DRY decorator pattern.", story)

    H2("migrate Command", story)
    simple_table(
        ["Option", "Type", "Default", "Description"],
        [
            ["--input",        "Path (required)", "—",            ".twb or .twbx file to migrate"],
            ["--output",       "Path",            "output_pbi/",  "Base output directory"],
            ["--no-llm",       "Flag",            "False",        "Disable LLM fallback for DAX"],
            ["--workspace",    "str",             "None",         "PBI workspace — enables publish"],
            ["--xmla",         "str",             "None",         "XMLA endpoint URL for Fabric/Premium"],
            ["--no-overwrite", "Flag",            "False",        "Abort if report already exists"],
            ["--verbose / -v", "Flag",            "False",        "Show DEBUG-level log output"],
        ],
        story, col_widths=[3*cm, 2.5*cm, 2.5*cm, 9.5*cm])

    H2("_add_publish_options — DRY Decorator Pattern", story)
    P("Rather than duplicating the three publish options across both commands, "
      "they are defined in a list and applied via a decorator function:", story)
    CODE("""\
_publish_options = [
    click.option("--workspace", ...),
    click.option("--xmla", ...),
    click.option("--no-overwrite", ...),
]

def _add_publish_options(cmd):
    for opt in reversed(_publish_options):   # reversed: Click applies in reverse order
        cmd = opt(cmd)
    return cmd

@cli.command("migrate")
@_add_publish_options    # injects all three options
def migrate_cmd(...):
    ...
    """, story)

    H2("_print_summary() — Colour-coded Output", story)
    simple_table(
        ["Condition", "Colour", "Example"],
        [
            ["errors == 0",        "Green",  "✓ sales_dashboard  coverage=100%  errors=0  warnings=2"],
            ["errors > 0",         "Yellow", "✓ complex_report   coverage=78%   errors=3  warnings=5"],
            ["Migration failed",   "Red",    "✗ broken_file: ValueError: No .twb found inside"],
            ["Live URL printed",   "Cyan",   "Live → https://app.powerbi.com/groups/.../reports/..."],
        ],
        story, col_widths=[3.5*cm, 2*cm, 12*cm])
    story.append(PageBreak())


# ── Section 15: Mapping Tables ─────────────────────────────────────────────────

def sec15(story):
    H1("15. Mapping Tables — utils/mappings.py", story)
    P("All mapping tables are pure Python dictionaries and lists — no external config files. "
      "This makes them easy to version-control, diff, and extend without any YAML parsing overhead.", story)

    H2("AGG_MAP — Tableau → DAX Aggregations", story)
    simple_table(
        ["Tableau", "DAX Function"],
        [
            ["SUM", "SUM"], ["AVG", "AVERAGE"], ["COUNT", "COUNT"],
            ["COUNTD", "DISTINCTCOUNT"], ["MIN", "MIN"], ["MAX", "MAX"],
            ["MEDIAN", "MEDIAN"], ["STDEV", "STDEV.S"], ["STDEVP", "STDEV.P"],
            ["VAR", "VAR.S"], ["VARP", "VAR.P"], ["ATTR", "SELECTEDVALUE"],
            ["YEAR", "YEAR"], ["QUARTER", "QUARTER"], ["MONTH", "MONTH"], ["DAY", "DAY"],
        ],
        story, col_widths=[3.5*cm, 14*cm])

    H2("DTYPE_MAP — Data Type Mapping", story)
    simple_table(
        ["Tableau Type", "Power BI Type"],
        [
            ["string",   "Text"],
            ["integer",  "Whole Number"],
            ["real",     "Decimal Number"],
            ["boolean",  "True/False"],
            ["date",     "Date"],
            ["datetime", "Date/Time"],
            ["spatial",  "Text  (no direct PBI equivalent)"],
        ],
        story, col_widths=[4*cm, 13.5*cm])

    H2("Extending the Pattern Catalog", story)
    P("To add a new Tableau function pattern, append a 4-tuple to "
      "<font face='Courier'>FORMULA_PATTERNS</font> in mappings.py:", story)
    CODE("""\
(
  r"SPACE\((\d+)\)",             # regex for SPACE(n)
  "REPT(\" \", {field})",        # DAX template  ({field} = capture group 1)
  0.90,                          # confidence
  ""                             # no review note
)
    """, story)
    story.append(PageBreak())


# ── Section 16: Bug Fixes ──────────────────────────────────────────────────────

def sec16(story):
    H1("16. Bug Fixes — Code Review Findings", story)
    P("Six bugs were identified in a structured code review and fixed before "
      "this document was written. All fixes are in the current codebase.", story)
    SP(story)
    simple_table(
        ["ID", "Severity", "File", "Root Cause", "Fix Applied"],
        [
            ["B1", "CRITICAL",
             "dax_generator.py",
             "Python closure captured loop variable template by reference. "
             "All recursive DAX substitutions used the last pattern's template, not the matched one.",
             "Default-arg capture: def _replacer(m, _tmpl=template, _conf=confidence, ...)"],
            ["B2", "CRITICAL",
             "mquery_generator.py",
             "Table.NestedJoin creates a nested Table column. "
             "Without ExpandTableColumn, all joined fields were invisible — "
             "users saw an unexpanded [Table] cell.",
             "Added ExpandTableColumn step after every NestedJoin, with "
             "prefixed column names to prevent collisions."],
            ["B3", "CRITICAL",
             "twb_parser.py",
             "Shelf text split on all commas. DATEADD('month',-1,[Date]) "
             "was incorrectly split into three tokens, causing malformed field names.",
             "Replaced .split(',') with _split_shelf() — a depth-aware "
             "splitter that only splits at parenthesis depth 0."],
            ["B4", "SECURITY",
             "twb_parser.py",
             "xml.etree.ElementTree is not XXE-safe. A malicious .twb could "
             "read local filesystem files via XML entity expansion.",
             "Switched to defusedxml with graceful fallback and warning log."],
            ["B5", "SAFETY",
             "report_writer.py",
             "_safe() could return empty string or all-underscores for "
             "non-ASCII datasource names, causing FileNotFoundError on write.",
             "Added .strip('_') and 'unnamed' fallback to _safe()."],
            ["B6", "CORRECTNESS",
             "coverage_validator.py",
             "visuals_auto counter excluded flagged visuals, making "
             "visual coverage % artificially low even when visuals were mapped.",
             "visuals_auto now increments for all mapped visuals; "
             "visuals_flagged is a sub-count for 'mapped with notes'."],
        ],
        story, col_widths=[0.8*cm, 1.8*cm, 3.2*cm, 5.5*cm, 6.2*cm])
    story.append(PageBreak())


# ── Section 17: Enhancement Roadmap ────────────────────────────────────────────

def sec17(story):
    H1("17. Enhancement Roadmap", story)
    P("Fourteen enhancements identified in the code review, prioritised by value.", story)
    SP(story)
    H2("High Value — Do First", story)
    simple_table(
        ["ID", "Enhancement", "Effort", "Impact"],
        [
            ["E1", "ELSEIF chain → SWITCH(TRUE(), ...)\nMulti-branch Tableau IFs are very common", "Low", "High"],
            ["E2", "Auto-generate a standard M Date table\nRequired for RUNNING_SUM / DATESYTD", "Medium", "High"],
            ["E3", "Named Groups → DAX SWITCH skeleton\nTableau Named Groups are common in BI workbooks", "Medium", "High"],
            ["E4", "Multi-datasource blending warning\nPBI needs model relationships, not view-level blends", "Low", "High"],
            ["E5", "Multi-dimension FIXED LOD pattern\n{FIXED [A],[B] : ...} not matched by current patterns", "Low", "High"],
        ],
        story, col_widths=[0.8*cm, 8*cm, 1.8*cm, 1.8*cm])
    SP(story)
    H2("Medium Value — Next Sprint", story)
    simple_table(
        ["ID", "Enhancement", "Effort", "Impact"],
        [
            ["E6",  "Tableau Set → DAX calculated table\nCALCULATETABLE(VALUES(...), ...) pattern", "Medium", "Medium"],
            ["E7",  "Bin → DAX calculated column\nFLOOR([Field]/n)*n with bin size from IR", "Low", "Medium"],
            ["E8",  "Conditional formatting spec in layout JSON\nHighlight table background rules → PBI cond. format", "Medium", "Medium"],
            ["E9",  "Parameter → What-If M snippet\nAuto-generate the slider M query + slicer visual spec", "Low", "Medium"],
            ["E10", "--diff mode: only output changed measures/visuals\nRe-run on updated .twb without full regeneration", "Medium", "Medium"],
        ],
        story, col_widths=[0.8*cm, 8*cm, 1.8*cm, 1.8*cm])
    SP(story)
    H2("Testing & Quality", story)
    simple_table(
        ["ID", "Enhancement", "Effort", "Impact"],
        [
            ["E11", "Unit tests for _translate_formula()\nTable-driven tests for every FORMULA_PATTERNS entry", "Low", "Medium"],
            ["E12", "Golden output comparison\nStore expected .dax / .pq and fail CI on regression", "Medium", "High"],
            ["E13", "LLM response validation\nStrip markdown fences, verify DAX syntax before accepting", "Low", "Medium"],
            ["E14", "batch_summary.json output\nMachine-readable summary for downstream tooling", "Low", "Low"],
        ],
        story, col_widths=[0.8*cm, 8*cm, 1.8*cm, 1.8*cm])
    story.append(PageBreak())


# ── Section 18: E2E Example ────────────────────────────────────────────────────

def sec18(story):
    H1("18. End-to-End Example Walkthrough", story)
    P("This section traces the bundled <b>sample_sales_dashboard.twb</b> through "
      "all 6 pipeline stages.", story)

    H2("Source Workbook — What the Parser Extracts", story)
    simple_table(
        ["Element", "Count", "Details"],
        [
            ["Datasources", "1", "orders_ds — SQL Server, dbo.Orders, DirectQuery"],
            ["Worksheets", "6", "Sales by Region, Profit by Category, Sales Trend,\nCustomer Scatter, Sales Map, KPI Summary"],
            ["Dashboards", "2", "Executive Dashboard (4 visuals), Customer Analysis (2 visuals)"],
            ["Calculated Fields", "7", "Profit Ratio, Sales per Customer, Days to Ship,\nAbove Average Sales, Profit Band, YTD Sales, Customer Upper"],
            ["Parameters", "0", "None in this workbook"],
        ],
        story, col_widths=[3*cm, 1.5*cm, 13*cm])

    H2("Stage 3 — DAX Generated for Each Calculated Field", story)
    simple_table(
        ["Tableau Formula", "Generated DAX", "Confidence"],
        [
            ["SUM([Profit])/SUM([Sales])",
             "SUM(Orders[Profit]) / SUM(Orders[Sales])", "0.95"],
            ["SUM([Sales])/COUNTD([Customer ID])",
             "SUM(Orders[Sales]) / DISTINCTCOUNT(Orders[Customer ID])", "0.95"],
            ["DATEDIFF('day',[Order Date],[Ship Date])",
             "DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)", "0.80"],
            ["SUM([Sales]) > {FIXED [Region] : AVG(SUM([Sales]))}",
             "SUM(Orders[Sales]) > CALCULATE(AVERAGE(...), REMOVEFILTERS(), VALUES(...))", "0.65"],
            ["IF [Profit] > 500 THEN 'High' ELSE ... END",
             "IF(Orders[Profit] > 500, \"High\", IF(..., \"Medium\", \"Loss\"))", "0.80"],
            ["RUNNING_SUM(SUM([Sales]))",
             "CALCULATE(SUM(Orders[Sales]), DATESYTD(Date[Date]))", "0.50"],
            ["UPPER([Customer Name])",
             "UPPER(Orders[Customer Name])", "0.95"],
        ],
        story, col_widths=[5.5*cm, 7.5*cm, 2*cm])

    H2("Stage 4 — Visual Mapping per Dashboard", story)
    H3("Executive Dashboard (1366 × 768 px)", story)
    simple_table(
        ["Worksheet", "Tableau Mark", "PBI Visual", "Position (%)"],
        [
            ["Sales by Region",    "bar",  "barChart",    "x=0, y=0, w=50, h=50"],
            ["Profit by Category", "bar",  "barChart",    "x=50, y=0, w=50, h=50"],
            ["Sales Trend",        "line", "lineChart",   "x=0, y=50, w=50, h=50"],
            ["KPI Summary",        "text", "tableEx",     "x=50, y=50, w=50, h=50"],
        ],
        story, col_widths=[4*cm, 3*cm, 3*cm, 7.5*cm])
    H3("Customer Analysis (1366 × 768 px)", story)
    simple_table(
        ["Worksheet", "Tableau Mark", "PBI Visual", "Position (%)"],
        [
            ["Customer Scatter", "circle",     "scatterChart", "x=0, y=0, w=66.7, h=100"],
            ["Sales Map",        "filled_map", "filledMap",    "x=66.7, y=0, w=33.3, h=100"],
        ],
        story, col_widths=[4*cm, 3*cm, 3*cm, 7.5*cm])

    H2("Stage 5 — Output Files Written", story)
    CODE("""\
output_pbi/sample_sales_dashboard/
  sample_sales_dashboard.pbix      2.2 KB  (deployable)
  sample_sales_dashboard.bim       3.1 KB  (XMLA)
  powerquery/
    Orders.pq                      190 B
  dax/
    measures.dax                   1.4 KB  (12 measures, 0 flagged)
  layout/
    report_pages.json              5.9 KB  (2 pages, 6 visuals)
  ir/
    sample_sales_dashboard.ir.json 4.2 KB
  migration_report/
    summary.md                     Overall coverage: 100.0%
    manual_review.md               0 errors, 0 warnings
    field_mapping.csv              17 rows (all fields)
    """, story)
    story.append(PageBreak())


# ── Section 19: Deployment Guide ──────────────────────────────────────────────

def sec19(story):
    H1("19. Deployment Guide", story)

    H2("Step 1 — Install Dependencies", story)
    CODE("""\
pip3 install defusedxml click pydantic requests msal reportlab
# Optional: for LLM DAX translation
pip3 install anthropic openai
    """, story)

    H2("Step 2 — One-Time Azure App Registration", story)
    simple_table(
        ["Step", "Action"],
        [
            ["1", "portal.azure.com → Azure Active Directory → App registrations → New registration"],
            ["2", "Name: tableau-pbi-migrator — note the Tenant ID and Client ID from Overview"],
            ["3", "Certificates & secrets → New client secret — copy the secret value immediately"],
            ["4", "API permissions → Add → Power BI Service → Delegated:\n"
                  "Dataset.ReadWrite.All, Report.ReadWrite.All, Workspace.Read.All\n"
                  "→ Grant admin consent"],
            ["5", "In Power BI Service → Your Workspace → Access → add the app as Member or Admin"],
        ],
        story, col_widths=[0.8*cm, 16.7*cm])

    H2("Step 3 — Environment Variables", story)
    CODE("""\
# Add to ~/.zshrc or ~/.bash_profile

# Required for publish
export PBI_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export PBI_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export PBI_CLIENT_SECRET="your-secret-value"

# Optional: LLM DAX translation
export ANTHROPIC_API_KEY="sk-ant-..."    # Claude Sonnet
export OPENAI_API_KEY="sk-..."           # GPT-4o (fallback)
    """, story)

    H2("Step 4 — Run Commands", story)
    CODE("""\
# Local only — single file
python3 -m tableau_to_pbi migrate \\
    --input tableau_to_pbi/input_twb/MyDashboard.twb

# Local only — batch
python3 -m tableau_to_pbi migrate-batch \\
    --input-dir tableau_to_pbi/input_twb/

# Touchless publish — single file
python3 -m tableau_to_pbi migrate \\
    --input   tableau_to_pbi/input_twb/MyDashboard.twb \\
    --workspace "Analytics Team"

# Touchless publish — batch
python3 -m tableau_to_pbi migrate-batch \\
    --input-dir tableau_to_pbi/input_twb/ \\
    --workspace "Analytics Team"

# Fabric / Premium — XMLA semantic model deploy
python3 -m tableau_to_pbi migrate \\
    --input   tableau_to_pbi/input_twb/MyDashboard.twb \\
    --workspace "Analytics Team" \\
    --xmla    "powerbi://api.powerbi.com/v1.0/myorg/Analytics Team"

# Pattern-only (no LLM, no API key needed)
python3 -m tableau_to_pbi migrate-batch \\
    --input-dir tableau_to_pbi/input_twb/ \\
    --no-llm

# Verbose output (shows every visual and measure as it's generated)
python3 -m tableau_to_pbi migrate \\
    --input tableau_to_pbi/input_twb/MyDashboard.twb -v
    """, story)
    story.append(PageBreak())


# ── Section 20: Glossary ───────────────────────────────────────────────────────

def sec20(story):
    H1("20. Glossary", story)
    simple_table(
        ["Term", "Definition"],
        [
            ["BIM",  "Business Intelligence Model. A JSON file in the Tabular Model format that "
                     "defines tables, columns, measures, and relationships for an Analysis Services "
                     "database. Used by Tabular Editor and the XMLA endpoint to deploy Power BI "
                     "semantic models programmatically."],
            ["DAX",  "Data Analysis Expressions. The formula language used in Power BI, "
                     "SSAS Tabular, and Excel Power Pivot to define calculated columns, "
                     "measures, and calculated tables. Evaluated in filter context."],
            ["IR",   "Intermediate Representation. A structured, language-agnostic JSON object "
                     "that captures the full meaning of a Tableau workbook. Acts as the contract "
                     "between the Parser stage and all downstream stages."],
            ["LOD",  "Level of Detail expression. A Tableau construct that allows calculations "
                     "to be evaluated at a different grain than the current visual. Types: "
                     "FIXED (explicit grain), INCLUDE (finer grain), EXCLUDE (coarser grain). "
                     "Equivalent in DAX requires careful use of CALCULATE + REMOVEFILTERS."],
            ["M Query / Power Query",
                     "The functional query language used in Power BI to connect to data sources, "
                     "transform data, and define tables. Stored as .m or .pq text files. "
                     "Evaluated inside the Power Query engine (Mashup engine) before DAX sees the data."],
            ["PBIX", "Power BI Desktop file format. A ZIP archive containing a DataMashup "
                     "(Power Query M), Report/Layout (JSON), and optionally a DataModel "
                     "(embedded tabular engine). Can be uploaded to Power BI Service."],
            ["TWB",  "Tableau Workbook. A plain XML file (extension .twb) containing all "
                     "datasource definitions, calculated fields, worksheet configurations, "
                     "and dashboard layouts."],
            ["TWBX", "Tableau Packaged Workbook. A ZIP archive (extension .twbx) containing "
                     "a .twb file plus embedded data extracts (.hyper files)."],
            ["XMLA", "XML for Analysis. A SOAP-based protocol for querying and managing "
                     "Analysis Services databases. Power BI Premium and Fabric expose an "
                     "XMLA read-write endpoint enabling programmatic deployment of semantic models."],
            ["XXE",  "XML External Entity attack. A vulnerability where an XML parser processes "
                     "external entity references in untrusted XML input, potentially reading "
                     "local files or making server-side requests. Prevented by using defusedxml."],
        ],
        story, col_widths=[2.5*cm, 15*cm])
    SP(story)
    HR(story)
    SP(story)
    P("<i>Generated by the Tableau → Power BI Migration Accelerator documentation tool. "
      "All code and documentation © LatentView Analytics 2026.</i>", story, "caption")


# ── Page template ──────────────────────────────────────────────────────────────

def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Header bar
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, h - 1.8*cm, w, 1.8*cm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(2*cm, h - 1.1*cm, "Tableau → Power BI Migration Accelerator")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - 2*cm, h - 1.1*cm, "Code Walkthrough  |  LatentView Analytics")

    # Footer
    canvas.setFillColor(C_GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(2*cm, 1.2*cm, f"Page {doc.page}")
    canvas.drawCentredString(w/2, 1.2*cm, "CONFIDENTIAL — Internal Use Only")
    canvas.drawRightString(w - 2*cm, 1.2*cm, "June 2026")
    canvas.restoreState()


# ── Main ───────────────────────────────────────────────────────────────────────

def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
        title="Tableau to Power BI Migration Accelerator — Code Walkthrough",
        author="LatentView Analytics",
        subject="Code Walkthrough Document",
    )

    story = []
    cover_page(story)
    toc_page(story)
    sec1(story)
    sec2(story)
    sec3(story)
    sec4(story)
    sec5(story)
    sec6(story)
    sec7(story)
    sec8(story)
    sec9(story)
    sec10(story)
    sec11(story)
    sec12(story)
    sec13(story)
    sec14(story)
    sec15(story)
    sec16(story)
    sec17(story)
    sec18(story)
    sec19(story)
    sec20(story)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\n✓ PDF written: {OUTPUT}")
    print(f"  Size : {size_kb:.1f} KB")
    print(f"  Pages: ~{len([x for x in story if isinstance(x, PageBreak)]) + 1}")


if __name__ == "__main__":
    build()
