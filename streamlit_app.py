"""
Tableau → Power BI Migrator
Full pipeline: Parse TWB → Generate DAX → Map Visuals → Package PBIP
"""

import logging
import streamlit as st

from tableau_to_powerbi.pipeline import run_pipeline
from tableau_to_powerbi.config import CONFIG
from tableau_to_powerbi.utils import setup_logging

# Setup logging
setup_logging(CONFIG.log_level)
logger = logging.getLogger("tableau_to_powerbi.app")

# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Tableau → Power BI Migrator",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
        min-height: 100vh;
    }
    #MainMenu, footer, header { visibility: hidden; }
    .card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2.5rem 2rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 2.6rem; font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; text-align: center; line-height: 1.2; margin-bottom: 0.4rem;
    }
    .hero-sub {
        text-align: center; color: rgba(255,255,255,0.55);
        font-size: 1rem; font-weight: 400; margin-bottom: 2rem;
    }
    .step-row { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; margin-bottom: 2rem; }
    .step-badge {
        background: rgba(167,139,250,0.15); border: 1px solid rgba(167,139,250,0.35);
        border-radius: 999px; padding: 0.35rem 1rem; font-size: 0.78rem;
        font-weight: 500; color: #c4b5fd; letter-spacing: 0.02em;
    }
    .step-badge.active {
        background: linear-gradient(90deg, rgba(167,139,250,0.35), rgba(96,165,250,0.35));
        border-color: rgba(167,139,250,0.7); color: #fff;
    }
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.04);
        border: 2px dashed rgba(167,139,250,0.45);
        border-radius: 16px; padding: 1rem; transition: border-color 0.25s;
    }
    [data-testid="stFileUploader"]:hover { border-color: rgba(167,139,250,0.85); }
    .success-box {
        background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.4);
        border-radius: 14px; padding: 1.2rem 1.5rem; color: #6ee7b7;
        font-size: 0.9rem; margin-top: 1.25rem;
    }
    .info-box {
        background: rgba(96,165,250,0.1); border: 1px solid rgba(96,165,250,0.3);
        border-radius: 14px; padding: 1rem 1.5rem; color: #93c5fd;
        font-size: 0.85rem; margin-top: 1rem;
    }
    .warning-box {
        background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
        border-radius: 14px; padding: 1rem 1.5rem; color: #fcd34d;
        font-size: 0.85rem; margin-top: 1rem;
    }
    .stDownloadButton > button {
        background: linear-gradient(90deg, #7c3aed, #2563eb) !important;
        color: #fff !important; border: none !important;
        border-radius: 12px !important; font-weight: 600 !important;
        font-size: 1rem !important; padding: 0.75rem 2rem !important;
        width: 100% !important; margin-top: 1rem !important;
        box-shadow: 0 4px 20px rgba(124,58,237,0.45) !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(124,58,237,0.6) !important;
    }
    .meta-row { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1rem 0; }
    .meta-pill {
        background: rgba(255,255,255,0.07); border-radius: 8px;
        padding: 0.35rem 0.85rem; font-size: 0.8rem; color: rgba(255,255,255,0.65);
    }
    .meta-pill span { color: #e0e7ff; font-weight: 600; }
    .stats-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem; margin: 1.25rem 0;
    }
    .stat-card {
        background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 0.75rem; text-align: center;
    }
    .stat-value { font-size: 1.4rem; font-weight: 700; color: #a78bfa; }
    .stat-label { font-size: 0.7rem; color: rgba(255,255,255,0.45); margin-top: 0.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── UI Layout ─────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="hero-title">Tableau → Power BI Migrator</div>
    <p class="hero-sub">Upload a Tableau workbook and receive a ready-to-open Power BI project</p>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="step-row">
        <div class="step-badge active">① Upload .twb</div>
        <div class="step-badge">② Configure</div>
        <div class="step-badge">③ Parse & Translate</div>
        <div class="step-badge">④ Generate PBIP</div>
        <div class="step-badge">⑤ Download</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Upload Card ───────────────────────────────────────────────────────────────

st.markdown('<div class="card">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    label="Drop your `.twb` file here, or click to browse",
    type=["twb", "twbx"],
    accept_multiple_files=False,
    help="Tableau Workbook (.twb) or packaged workbook (.twbx) files are accepted.",
    label_visibility="visible",
)

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_size_kb = round(len(file_bytes) / 1024, 1)

    st.markdown(
        f"""
        <div class="meta-row">
            <div class="meta-pill">📄 File &nbsp;<span>{uploaded_file.name}</span></div>
            <div class="meta-pill">📦 Size &nbsp;<span>{file_size_kb} KB</span></div>
            <div class="meta-pill">✅ Status &nbsp;<span>Ready</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Configuration ─────────────────────────────────────────────────────────
    st.markdown("#### ⚙️ Configuration", unsafe_allow_html=False)

    # Quick-parse the TWB to extract the data directory
    from tableau_to_powerbi.parser import parse_twb as _quick_parse
    import os as _os
    try:
        _quick_ir = _quick_parse(file_bytes, uploaded_file.name)
        _detected_dir = _quick_ir.data_directory if _quick_ir.data_directory and _os.path.isdir(_quick_ir.data_directory) else CONFIG.default_data_directory
    except Exception:
        _detected_dir = CONFIG.default_data_directory

    # Derive default project name from filename
    import re as _re
    _base_name = uploaded_file.name.rsplit(".", 1)[0].strip()
    _base_name = _re.sub(r"\s*\(\d+\)\s*$", "", _base_name)
    _default_project = _base_name.replace(" ", "") + "Report" if _base_name else CONFIG.project_name

    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input(
            "Project Name", value=_default_project, help="Name for the Power BI project"
        )
    with col2:
        data_directory = st.text_input(
            "Data Directory", value=_detected_dir,
            help="Path where CSV data files are located (auto-detected from TWB)"
        )

    # ── Pre-flight Validation ────────────────────────────────────────────────
    # TMDL reserved words that need quoting
    _TMDL_RESERVED = {
        "end", "table", "column", "measure", "partition", "relationship",
        "expression", "model", "database", "ref", "annotation", "source",
        "mode", "type", "name", "role", "culture", "from", "to", "in",
        "true", "false", "none", "not", "and", "or", "is",
    }

    _validation_errors: list[str] = []
    _validation_warnings: list[str] = []
    _auto_fixes: list[str] = []
    _table_status: list[dict[str, str]] = []

    if _quick_ir and _os.path.isdir(data_directory):
        for _ds in _quick_ir.datasources:
            for _tbl in _ds.tables:
                _tbl_name = _tbl.name
                _issues_parts: list[str] = []

                # ── Check: table name is a TMDL reserved word ──
                if _tbl_name.lower() in _TMDL_RESERVED:
                    _auto_fixes.append(
                        f"Table **`{_tbl_name}`** is a TMDL reserved word → will be auto-quoted as `'{_tbl_name}'`"
                    )

                # ── Check: column names that are TMDL reserved words ──
                _reserved_cols = [c.name for c in _tbl.columns if c.name.lower() in _TMDL_RESERVED]
                if _reserved_cols:
                    _auto_fixes.append(
                        f"Table **`{_tbl_name}`**: columns {', '.join(f'`{c}`' for c in _reserved_cols)} "
                        f"are TMDL reserved words → will be auto-quoted"
                    )

                # ── Check: CSV file exists ──
                _csv_filename = _tbl.filename if _tbl.filename else f"{_tbl_name}.csv"
                _csv_path = _os.path.join(data_directory, _csv_filename)

                if not _os.path.isfile(_csv_path):
                    _validation_errors.append(
                        f"**{_tbl_name}**: CSV file not found → expected `{_csv_filename}` in `{data_directory}`"
                    )
                    _table_status.append({
                        "Table": _tbl_name,
                        "CSV File": _csv_filename,
                        "Status": "❌ File not found",
                        "Issues": "—",
                    })
                    continue

                # ── Check: CSV headers vs TWB columns ──
                try:
                    with open(_csv_path, "r", encoding="utf-8-sig") as _f:
                        _header_line = _f.readline().strip()
                    _csv_headers = [h.strip().strip('"') for h in _header_line.split(",")]
                    _csv_headers_set = set(_csv_headers)
                    _twb_columns = {c.name for c in _tbl.columns}

                    # Check for duplicate CSV headers
                    _dupes = [h for h in _csv_headers if _csv_headers.count(h) > 1]
                    if _dupes:
                        _validation_warnings.append(
                            f"**{_tbl_name}** (`{_csv_filename}`): duplicate column headers in CSV → "
                            + ", ".join(f"`{d}`" for d in sorted(set(_dupes)))
                        )
                        _issues_parts.append(f"Dupes: {', '.join(sorted(set(_dupes)))}")

                    # Check for columns in TWB missing from CSV
                    if _twb_columns:
                        _missing_in_csv = _twb_columns - _csv_headers_set
                        if _missing_in_csv:
                            _issues_parts.append(f"Missing: {', '.join(sorted(_missing_in_csv))}")
                            _validation_errors.append(
                                f"**{_tbl_name}** (`{_csv_filename}`): columns in TWB but missing in CSV → "
                                + ", ".join(f"`{c}`" for c in sorted(_missing_in_csv))
                            )

                    # Check CSV headers for reserved words (these get auto-quoted too)
                    _csv_reserved = [h for h in _csv_headers_set if h.lower() in _TMDL_RESERVED]
                    if _csv_reserved and not _reserved_cols:
                        # Only show if not already reported from TWB columns
                        _auto_fixes.append(
                            f"Table **`{_tbl_name}`**: CSV columns {', '.join(f'`{c}`' for c in _csv_reserved)} "
                            f"are TMDL reserved words → will be auto-quoted"
                        )

                except Exception as _e:
                    _validation_warnings.append(
                        f"**{_tbl_name}**: could not read CSV headers → {_e}"
                    )

                _status = "❌ Issues" if _issues_parts else "✅ OK"
                _table_status.append({
                    "Table": _tbl_name,
                    "CSV File": _csv_filename,
                    "Status": _status,
                    "Issues": "; ".join(_issues_parts) if _issues_parts else "None",
                })

    # ── Display validation results ──
    st.markdown("#### 🔍 Pre-flight Validation")

    if _table_status:
        st.markdown(
            "_Checking dataset mapping, TMDL compatibility, and column integrity._"
        )
        import pandas as _pd
        st.dataframe(
            _pd.DataFrame(_table_status),
            use_container_width=True,
            hide_index=True,
        )

    # ── Calculated Field Translation Preview ──
    if _quick_ir and _quick_ir.calculated_fields:
        from tableau_to_powerbi.translation import translate_calculated_field, infer_parent_table

        _calc_rows: list[dict[str, str]] = []
        _calc_warnings: list[str] = []

        # Collect all CSV column names to detect duplicates
        _all_csv_cols: set[str] = set()
        if _os.path.isdir(data_directory):
            for _ds2 in _quick_ir.datasources:
                for _tbl2 in _ds2.tables:
                    _csv_fn = _tbl2.filename if _tbl2.filename else f"{_tbl2.name}.csv"
                    _csv_p = _os.path.join(data_directory, _csv_fn)
                    if _os.path.isfile(_csv_p):
                        try:
                            with open(_csv_p, "r", encoding="utf-8-sig") as _ff:
                                _hdr2 = _ff.readline().strip()
                            _all_csv_cols.update(
                                h.strip().strip('"').lower() for h in _hdr2.split(",")
                            )
                        except Exception:
                            pass

        for _cf in _quick_ir.calculated_fields:
            _parent = _cf.parent_table or infer_parent_table(_cf, None)
            try:
                _dax = translate_calculated_field(_cf, _parent)
            except Exception as _e:
                _dax = f"⚠️ Translation failed: {_e}"
                _calc_warnings.append(
                    f"**{_cf.caption or _cf.name}**: could not translate formula `{_cf.formula[:80]}` → {_e}"
                )

            _cf_name = _cf.caption or _cf.name
            _is_duplicate = _cf_name.lower() in _all_csv_cols

            # Check if DAX still contains Tableau keywords (untranslated)
            _dax_lower = _dax.lower()
            _has_tableau_syntax = any(
                kw in _dax_lower for kw in [" then ", " end", " elseif "]
            )
            if _has_tableau_syntax:
                _auto_fixes.append(
                    f"Calculated field **`{_cf_name}`**: Tableau IF/THEN/END syntax → auto-converted to DAX `IF()` function"
                )

            # Check for multi-line (would break TMDL)
            if "\n" in _dax:
                _auto_fixes.append(
                    f"Calculated field **`{_cf_name}`**: multi-line expression → will be collapsed to single line"
                )

            # Check for duplicate with CSV column
            if _is_duplicate:
                _auto_fixes.append(
                    f"Calculated field **`{_cf_name}`**: duplicates a CSV column name → will be skipped (CSV column used instead)"
                )

            _status_icon = "⏭️" if _is_duplicate else ("✅" if not _has_tableau_syntax and "\n" not in _dax else "🔧")
            _calc_rows.append({
                "Field": _cf_name,
                "Tableau Formula": _cf.formula[:60] + ("..." if len(_cf.formula) > 60 else ""),
                "DAX Translation": _dax[:80] + ("..." if len(_dax) > 80 else ""),
                "Status": _status_icon + (" (skipped — exists in CSV)" if _is_duplicate else ""),
            })

        if _calc_warnings:
            for _cw in _calc_warnings:
                _validation_warnings.append(_cw)

        st.markdown("##### 🧮 Calculated Fields")
        st.markdown(
            f"_Found **{len(_quick_ir.calculated_fields)}** calculated field(s) in the workbook. "
            "These Tableau formulas are automatically translated to DAX._"
        )
        import pandas as _pd2
        st.dataframe(
            _pd2.DataFrame(_calc_rows),
            use_container_width=True,
            hide_index=True,
        )

    # Auto-fixes (informational - resolved automatically)
    if _auto_fixes:
        st.markdown("##### 🔧 Auto-resolved (no action needed)")
        st.info(
            "The following issues were detected and will be **automatically fixed** during conversion:\n\n"
            + "\n\n".join(f"• {f}" for f in _auto_fixes)
        )

    # Errors (blocking - user must fix)
    if _validation_errors:
        st.markdown("##### ❌ Blocking Issues")
        st.error(
            "Fix these before running the migration:\n\n"
            + "\n\n".join(f"• {e}" for e in _validation_errors)
        )
        st.markdown(
            """
            <div class="info-box">
                <strong>How to fix:</strong><br>
                1. <strong>File not found</strong> — place the CSV in the Data Directory above, 
                   or rename it to match the expected filename.<br>
                2. <strong>Column mismatch</strong> — open the CSV and verify the header row. 
                   Column names must match exactly (case-sensitive).<br><br>
                <em>After fixing, change the Data Directory field (or re-upload) to re-validate.</em>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Warnings (non-blocking)
    if _validation_warnings:
        st.markdown("##### ⚠️ Warnings")
        for _w in _validation_warnings:
            st.warning(_w)

    # All clear message
    if not _validation_errors and not _validation_warnings and _table_status:
        st.markdown(
            '<div class="success-box">✔ All pre-flight checks passed — ready to migrate.</div>',
            unsafe_allow_html=True,
        )

    # ── Run Conversion ────────────────────────────────────────────────────────
    _can_run = not _validation_errors
    if st.button("🚀 Run Migration", type="primary", use_container_width=True, disabled=not _can_run):
        with st.spinner("Running migration pipeline..."):
            progress = st.progress(0, text="Parsing Tableau workbook...")

            result = run_pipeline(
                twb_bytes=file_bytes,
                filename=uploaded_file.name,
                project_name=project_name,
                data_directory=data_directory,
            )

            progress.progress(100, text="Complete!")

        if result.success and result.pbip_bytes:
            # Show stats
            st.markdown(
                f"""
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{result.tables_count}</div>
                        <div class="stat-label">Tables</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{result.worksheets_count}</div>
                        <div class="stat-label">Worksheets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{result.measures_count}</div>
                        <div class="stat-label">DAX Measures</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{result.visuals_count}</div>
                        <div class="stat-label">Visuals</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div class="success-box">
                    ✔ &nbsp;<strong>Migration completed successfully.</strong> &nbsp;
                    Your Power BI project is ready — click below to download.
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Show warnings if any
            if result.warnings:
                warnings_html = "<br>".join(f"⚠️ {w}" for w in result.warnings)
                st.markdown(
                    f'<div class="warning-box">{warnings_html}</div>',
                    unsafe_allow_html=True,
                )

            # Download button
            st.download_button(
                label="⬇ Download Power BI Project (.zip)",
                data=result.pbip_bytes,
                file_name=f"{project_name}.zip",
                mime="application/zip",
            )

            st.markdown(
                f"""
                <div class="info-box">
                    <strong>Open it this way:</strong><br>
                    1. Extract <code>{project_name}.zip</code> to a normal folder.<br>
                    2. Open <code>{project_name}/{project_name}.pbip</code> from the extracted folder.<br>
                    3. Do <strong>not</strong> open the <code>.pbip</code> directly from inside the ZIP.<br><br>
                    <strong>Data files:</strong> Power BI uses the data directory you enter above only after the project opens.
                    Put your CSV files in <code>{data_directory}</code> or change the data directory in the app before running migration.
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Show details in expander
            with st.expander("📋 Migration Details"):
                if result.workbook_ir:
                    st.write("**Worksheets migrated:**")
                    for ws in result.workbook_ir.worksheets:
                        st.write(f"  - {ws.name} ({ws.mark_type})")

                st.write("**DAX Measures generated:**")
                for m in result.measures:
                    st.code(f"{m.name} = {m.dax_expression}", language="dax")

                if result.workbook_ir and result.workbook_ir.calculated_fields:
                    st.write("**Calculated Fields:**")
                    for cf in result.workbook_ir.calculated_fields:
                        st.write(
                            f"  - {cf.caption}: `{cf.formula}` → `{cf.dax_expression}`"
                        )

        else:
            st.error("Migration failed!")
            for err in result.errors:
                st.error(f"Error: {err}")

else:
    st.markdown(
        """
        <div style="text-align:center; padding: 1.5rem 0; color: rgba(255,255,255,0.3); font-size: 0.9rem;">
            No file selected yet — drag &amp; drop a <code>.twb</code> above to get started.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; margin-top:2rem; color:rgba(255,255,255,0.2); font-size:0.75rem;">
        Tableau → Power BI Migrator &nbsp;·&nbsp; Full pipeline: Parse → Translate → Map → Generate
    </div>
    """,
    unsafe_allow_html=True,
)
