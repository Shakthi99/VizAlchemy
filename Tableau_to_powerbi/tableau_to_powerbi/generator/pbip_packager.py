"""PBIP packager - assembles all generated content into a ZIP archive."""

from __future__ import annotations

import io
import json
import logging
import zipfile

from tableau_to_powerbi.config import CONFIG

logger = logging.getLogger("tableau_to_powerbi.generator")


def package_pbip(
    project_name: str,
    model_tmdl: str,
    database_tmdl: str,
    tables_tmdl: str,
    report_json: str,
    table_files: dict[str, str] | None = None,
    relationships_tmdl: str = "",
) -> bytes:
    """Package all generated content into a PBIP ZIP archive.
    
    If table_files and relationships_tmdl are provided, uses per-table TMDL files
    (standard PBIP folder structure). Otherwise falls back to single tables.tmdl.
    """
    buf = io.BytesIO()
    archive_root = project_name

    # Definition files for the generated PBIP package.
    definition_pmdl = json.dumps(
        {"version": "1.0", "setting": {"culture": "en-US"}},
        indent=2,
    )

    definition_pbism = json.dumps(
        {"version": "5.0", "settings": {}},
        indent=2,
    )

    definition_pbir = json.dumps(
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
            "version": "1.0",
            "datasetReference": {
                "byPath": {"path": f"../{project_name}.Dataset"},
                "byConnection": None,
            },
        },
        indent=2,
    )

    pbip_root = json.dumps(
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [
                {"report": {"path": f"{project_name}.Report"}},
            ],
            "settings": {"enableAutoRecovery": True},
        },
        indent=2,
    )

    def _utf8(text: str) -> bytes:
        return text.encode("utf-8")

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Root project file
        zf.writestr(
            f"{archive_root}/{project_name}.pbip",
            _utf8(pbip_root),
        )

        # Dataset files
        zf.writestr(
            f"{archive_root}/{project_name}.Dataset/definition.pmdl",
            _utf8(definition_pmdl),
        )
        zf.writestr(
            f"{archive_root}/{project_name}.Dataset/definition.pbism",
            _utf8(definition_pbism),
        )
        zf.writestr(
            f"{archive_root}/{project_name}.Dataset/definition/database.tmdl",
            _utf8(database_tmdl),
        )
        zf.writestr(
            f"{archive_root}/{project_name}.Dataset/definition/model.tmdl",
            _utf8(model_tmdl),
        )

        # Table and relationship files — use per-table structure
        if table_files:
            for tbl_name, tbl_content in table_files.items():
                zf.writestr(
                    f"{archive_root}/{project_name}.Dataset/definition/tables/{tbl_name}.tmdl",
                    _utf8(tbl_content),
                )
            if relationships_tmdl:
                zf.writestr(
                    f"{archive_root}/{project_name}.Dataset/definition/relationships.tmdl",
                    _utf8(relationships_tmdl),
                )
        else:
            zf.writestr(
                f"{archive_root}/{project_name}.Dataset/definition/tables.tmdl",
                _utf8(tables_tmdl),
            )

        # Report files
        zf.writestr(
            f"{archive_root}/{project_name}.Report/definition.pbir",
            _utf8(definition_pbir),
        )
        zf.writestr(
            f"{archive_root}/{project_name}.Report/report.json",
            _utf8(report_json),
        )

    buf.seek(0)
    result = buf.read()
    logger.info(
        "Packaged PBIP archive: %d bytes, project='%s'",
        len(result),
        project_name,
    )
    return result
