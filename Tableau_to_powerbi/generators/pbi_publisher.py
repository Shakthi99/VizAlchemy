"""
Power BI Publisher — deploys generated artifacts to Power BI Service
without any manual steps.

Two deployment paths (chosen automatically based on what's configured):

Path A — PBIX Import (simpler, Import-mode datasets)
  POST /v1.0/myorg/groups/{workspace_id}/imports
  Uploads the assembled .pbix file directly.

Path B — XMLA / Tabular (DirectQuery, Premium/Fabric capacity)
  Uses the XMLA endpoint with Tabular Editor CLI (if installed)
  to deploy the BIM semantic model, then uses the REST API to
  push the report layout on top.

Auth: Service Principal (recommended for CI/CD) or interactive MSAL device-flow.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

# ── Auth helpers ───────────────────────────────────────────────────────────────

_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_PBI_SCOPE  = "https://analysis.windows.net/powerbi/api/.default"
_PBI_BASE   = "https://api.powerbi.com/v1.0/myorg"


def _get_token_service_principal(tenant_id: str, client_id: str, client_secret: str) -> str:
    """OAuth2 client-credentials flow — non-interactive, CI/CD safe."""
    resp = requests.post(
        _TOKEN_URL.format(tenant_id=tenant_id),
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
            "scope":         _PBI_SCOPE,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    log.debug("Acquired service-principal token (tenant=%s, client=%s)", tenant_id, client_id[:8])
    return token


def _get_token_device_flow(tenant_id: str, client_id: str) -> str:
    """
    Interactive device-flow — user visits a URL and enters a code.
    Fallback when no client secret is configured.
    """
    try:
        import msal
    except ImportError:
        raise RuntimeError(
            "msal is not installed. Run: pip3 install msal\n"
            "Or set PBI_CLIENT_SECRET for non-interactive auth."
        )

    app = msal.PublicClientApplication(client_id,
                                       authority=f"https://login.microsoftonline.com/{tenant_id}")
    flow = app.initiate_device_flow(scopes=[_PBI_SCOPE])
    log.info("Device-flow auth required:")
    log.info("  → Visit:  %s", flow["verification_uri"])
    log.info("  → Code:   %s", flow["user_code"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Device-flow auth failed: {result.get('error_description')}")
    return result["access_token"]


def get_token() -> str:
    """
    Resolve auth token from environment variables.
    Priority: service principal → device flow.

    Required env vars (service principal):
      PBI_TENANT_ID, PBI_CLIENT_ID, PBI_CLIENT_SECRET

    Required env vars (device flow):
      PBI_TENANT_ID, PBI_CLIENT_ID
    """
    tenant_id     = os.environ.get("PBI_TENANT_ID", "")
    client_id     = os.environ.get("PBI_CLIENT_ID", "")
    client_secret = os.environ.get("PBI_CLIENT_SECRET", "")

    if not tenant_id or not client_id:
        raise RuntimeError(
            "Missing PBI_TENANT_ID or PBI_CLIENT_ID environment variables.\n"
            "See README for setup instructions."
        )

    if client_secret:
        return _get_token_service_principal(tenant_id, client_id, client_secret)
    return _get_token_device_flow(tenant_id, client_id)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Workspace helpers ─────────────────────────────────────────────────────────

def resolve_workspace_id(token: str, workspace_name: str) -> str:
    """
    Resolve a workspace name to its GUID.
    If workspace_name is already a GUID, return as-is.
    """
    if len(workspace_name) == 36 and workspace_name.count("-") == 4:
        return workspace_name  # already a GUID

    resp = requests.get(f"{_PBI_BASE}/groups", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    groups = resp.json().get("value", [])
    for g in groups:
        if g["name"].lower() == workspace_name.lower():
            return g["id"]
    names = [g["name"] for g in groups]
    raise ValueError(
        f"Workspace '{workspace_name}' not found. Available: {names}"
    )


# ── Path A: PBIX Import ───────────────────────────────────────────────────────

def import_pbix(
    pbix_path: Path,
    workspace_id: str,
    token: str,
    dataset_name: str,
    overwrite: bool = True,
) -> str:
    """
    Upload a .pbix file to Power BI Service.
    Returns the import job ID; call wait_for_import() to confirm completion.
    """
    name_conflict = "Overwrite" if overwrite else "Abort"
    url = (
        f"{_PBI_BASE}/groups/{workspace_id}/imports"
        f"?datasetDisplayName={dataset_name}&nameConflict={name_conflict}"
    )

    with open(pbix_path, "rb") as f:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (pbix_path.name, f, "application/octet-stream")},
            timeout=120,
        )
    resp.raise_for_status()
    import_id = resp.json().get("id", "")
    log.info("PBIX import initiated — import_id=%s", import_id)
    return import_id


def wait_for_import(import_id: str, workspace_id: str, token: str,
                    max_wait_s: int = 300) -> dict:
    """Poll the import status endpoint until complete or timeout."""
    url = f"{_PBI_BASE}/groups/{workspace_id}/imports/{import_id}"
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        resp = requests.get(url, headers=_headers(token), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        state = data.get("importState", "Unknown")
        log.debug("Import state: %s", state)
        if state == "Succeeded":
            log.info("Import complete ✓  datasets=%s  reports=%s",
                     [d["name"] for d in data.get("datasets", [])],
                     [r["name"] for r in data.get("reports", [])])
            return data
        if state == "Failed":
            raise RuntimeError(f"PBI import failed: {data}")
        time.sleep(5)
    raise TimeoutError(f"Import did not complete within {max_wait_s}s")


# ── Path B: XMLA semantic model deployment ────────────────────────────────────

def deploy_bim_via_xmla(
    bim: dict,
    xmla_endpoint: str,
    database_name: str,
) -> bool:
    """
    Deploy a BIM/tabular model to an XMLA endpoint using Tabular Editor CLI.
    Requires: dotnet tool install -g TabularEditor.CLI

    xmla_endpoint example: powerbi://api.powerbi.com/v1.0/myorg/MyWorkspace
    """
    try:
        result = subprocess.run(
            ["TabularEditor", "--version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise FileNotFoundError()
    except FileNotFoundError:
        log.warning(
            "TabularEditor CLI not found — skipping XMLA deployment.\n"
            "Install with: dotnet tool install -g TabularEditor.CLI"
        )
        return False

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".bim", mode="w",
                                     delete=False, encoding="utf-8") as tmp:
        json.dump(bim, tmp, indent=2)
        tmp_path = tmp.name

    cmd = [
        "TabularEditor",
        tmp_path,
        "-D", f'"{xmla_endpoint}"', database_name,
        "-O",           # Overwrite
        "-S",           # Schema deploy
        "-P",           # Partitions deploy
        "-E",           # Error on warning
    ]
    log.info("Deploying BIM via XMLA: %s → %s", database_name, xmla_endpoint)
    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(tmp_path).unlink(missing_ok=True)

    if result.returncode == 0:
        log.info("XMLA deployment succeeded ✓")
        return True

    log.error("XMLA deployment failed:\n%s", result.stderr)
    return False


# ── Dataset refresh trigger ────────────────────────────────────────────────────

def trigger_refresh(dataset_id: str, workspace_id: str, token: str) -> None:
    """Trigger a dataset refresh after import."""
    url = f"{_PBI_BASE}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
    resp = requests.post(
        url,
        headers=_headers(token),
        json={"notifyOption": "NoNotification"},
        timeout=30,
    )
    if resp.status_code == 202:
        log.info("Refresh triggered for dataset %s", dataset_id)
    else:
        log.warning("Refresh trigger returned %d: %s", resp.status_code, resp.text)


# ── High-level publish orchestrator ──────────────────────────────────────────

def publish(
    pbix_path: Path,
    bim: dict,
    workbook_name: str,
    workspace: str,
    xmla_endpoint: Optional[str] = None,
    overwrite: bool = True,
) -> dict:
    """
    Full publish flow:
      1. Acquire auth token
      2. Resolve workspace GUID
      3a. If XMLA endpoint provided → deploy BIM, then import thin PBIX
      3b. Otherwise → import full PBIX (Import-mode)
      4. Trigger dataset refresh
      5. Return dashboard URL

    Returns a dict with: workspace_id, dataset_id, report_id, report_url
    """
    log.info("Publishing '%s' to workspace '%s' …", workbook_name, workspace)
    token        = get_token()
    workspace_id = resolve_workspace_id(token, workspace)

    # Semantic model deploy (XMLA path)
    if xmla_endpoint:
        deploy_bim_via_xmla(bim, xmla_endpoint, workbook_name)

    # PBIX import
    import_id = import_pbix(pbix_path, workspace_id, token, workbook_name, overwrite)
    result    = wait_for_import(import_id, workspace_id, token)

    datasets = result.get("datasets", [])
    reports  = result.get("reports", [])
    dataset_id = datasets[0]["id"] if datasets else ""
    report_id  = reports[0]["id"]  if reports  else ""

    # Trigger refresh so data loads immediately
    if dataset_id:
        trigger_refresh(dataset_id, workspace_id, token)

    report_url = (
        f"https://app.powerbi.com/groups/{workspace_id}/reports/{report_id}"
        if report_id else ""
    )

    result_info = {
        "workspace_id": workspace_id,
        "dataset_id":   dataset_id,
        "report_id":    report_id,
        "report_url":   report_url,
    }

    if report_url:
        log.info("✓ Published! Report URL: %s", report_url)
    else:
        log.warning("Import succeeded but could not resolve report URL")

    return result_info
