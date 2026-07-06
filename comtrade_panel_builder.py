"""
UNCOMTRADE R7 Project Reconstruction
Ontology reference:
ontology/UNCOMTRADE_R7_ONTOLOGICAL_PROJECT_REPORT.md

This script recreates the old R7 UN Comtrade workflow according to the
ontology, data logic, and fidelity principles documented in the ontology
report. It replaces the legacy Comtrade URL procedure with the modern
UN Comtrade API while preserving the old project sequence:
download -> dress / clean -> transpose / wide panel

The subscription key is read from:
secrets/comtrade_primary_key.txt

The key must never be hard-coded in this script.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

try:
    import comtradeapicall
except ImportError:  # pragma: no cover - runtime dependency check
    comtradeapicall = None


BASE_DIR = Path(__file__).resolve().parent
ONTOLOGY_PATH = BASE_DIR / "ontology" / "UNCOMTRADE_R7_ONTOLOGICAL_PROJECT_REPORT.md"
CONFIG_PATH = BASE_DIR / "config" / "panel_config.json"
KEY_PATH = BASE_DIR / "secrets" / "comtrade_primary_key.txt"
REFERENCE_DIR = BASE_DIR / "reference"
METADATA_DIR = REFERENCE_DIR / "metadata"

OUTPUT_DIR = BASE_DIR / "comtrade_panel_output"
RAW_DIR = OUTPUT_DIR / "raw"
PROCESSED_DIR = OUTPUT_DIR / "processed"
WIDE_DIR = OUTPUT_DIR / "wide"
VALIDATION_REPORT_PATH = OUTPUT_DIR / "validation_report.txt"

FLOW_MAP = {
    "import": "M",  # old rg=1
    "export": "X",  # old rg=2
}

REFERENCE_FILES = [
    "HSag2_partner.csv",
    "HSag4_partner.csv",
    "HSag6_partner.csv",
    "partner_list.csv",
]

METADATA_FILES = [
    "HS.json",
    "Reporters.json",
    "partnerAreas.json",
    "Frequency.json",
]


class ConfigurationError(RuntimeError):
    """Raised when the JSON config is missing or invalid."""


def info(message: str) -> None:
    print(message, flush=True)


def ensure_directories() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "import").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "export").mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    WIDE_DIR.mkdir(parents=True, exist_ok=True)


def load_config(config_path: Path) -> Dict:
    if not config_path.exists():
        raise ConfigurationError(
            f"Missing config file: {config_path}. Please create config/panel_config.json."
        )

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Invalid JSON in {config_path}: {exc}") from exc

    required_fields = [
        "reporter_code",
        "reporter_name",
        "years",
        "classification",
        "frequency",
        "flows",
        "partner_code",
        "commodity_codes",
        "max_codes_per_batch",
    ]

    missing = [field for field in required_fields if field not in config]
    if missing:
        raise ConfigurationError(f"Missing required config fields: {', '.join(missing)}")

    if not isinstance(config["years"], list) or not config["years"]:
        raise ConfigurationError("Config 'years' must be a non-empty list.")
    if not isinstance(config["commodity_codes"], list) or not config["commodity_codes"]:
        raise ConfigurationError("Config 'commodity_codes' must be a non-empty list.")
    if not isinstance(config["flows"], list) or not config["flows"]:
        raise ConfigurationError("Config 'flows' must be a non-empty list.")

    invalid_flows = [flow for flow in config["flows"] if flow not in FLOW_MAP]
    if invalid_flows:
        raise ConfigurationError(
            f"Unsupported flow(s) in config: {invalid_flows}. Use any of {list(FLOW_MAP)}"
        )

    return config


def load_subscription_key(key_path: Path) -> str:
    if not key_path.exists():
        raise FileNotFoundError(
            f"Missing subscription key file: {key_path}. "
            "Create secrets/comtrade_primary_key.txt with only the key in plain text."
        )

    key = key_path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"Subscription key file is empty: {key_path}")

    return key


def check_reference_files() -> Tuple[List[Path], List[Path]]:
    existing = []
    missing = []
    for name in REFERENCE_FILES:
        path = REFERENCE_DIR / name
        if path.exists():
            existing.append(path)
        else:
            missing.append(path)

    for path in missing:
        info(f"Warning: reference file missing: {path}")

    for name in METADATA_FILES:
        metadata_path = METADATA_DIR / name
        if not metadata_path.exists():
            info(f"Warning: metadata file missing: {metadata_path}")

    return existing, missing


def load_metadata_results(file_name: str) -> List[Dict]:
    metadata_path = METADATA_DIR / file_name
    if not metadata_path.exists():
        return []

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        info(f"Warning: failed reading metadata file {metadata_path}: {exc}")
        return []

    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    if isinstance(payload, list):
        return payload
    return []


def validate_config_with_metadata(config: Dict) -> None:
    reporters = load_metadata_results("Reporters.json")
    if reporters:
        reporter_map = {
            str(row.get("reporterCode") or row.get("id") or ""): str(row.get("reporterDesc") or row.get("text") or "")
            for row in reporters
        }
        reporter_code = str(config["reporter_code"])
        if reporter_code not in reporter_map:
            info(
                "Warning: reporter_code not found in Reporters metadata: "
                f"{reporter_code}"
            )
        else:
            metadata_name = reporter_map[reporter_code].strip()
            config_name = str(config["reporter_name"]).strip()
            if metadata_name and metadata_name.lower() != config_name.lower():
                info(
                    "Warning: reporter_name differs from metadata. "
                    f"config='{config_name}' metadata='{metadata_name}'"
                )

    frequencies = load_metadata_results("Frequency.json")
    if frequencies:
        allowed_freq = {str(row.get("id", "")).strip() for row in frequencies}
        freq = str(config["frequency"]).strip()
        if freq and freq not in allowed_freq:
            raise ConfigurationError(
                f"Config frequency '{freq}' is not present in metadata Frequency.json"
            )

    partner_areas = load_metadata_results("partnerAreas.json")
    if partner_areas and str(config["partner_code"]).lower() != "all":
        partner_allowed = {
            str(
                row.get("PartnerCode")
                or row.get("partnerCode")
                or row.get("id")
                or ""
            ).strip()
            for row in partner_areas
        }
        partner_code = str(config["partner_code"]).strip()
        if partner_code not in partner_allowed:
            info(
                "Warning: partner_code not found in partnerAreas metadata: "
                f"{partner_code}"
            )

    if str(config["classification"]).upper() == "HS":
        hs_results = load_metadata_results("HS.json")
        if hs_results:
            hs_ids = {str(row.get("id", "")).strip() for row in hs_results}
            configured_codes = [str(code).strip() for code in config["commodity_codes"]]
            invalid_codes = [code for code in configured_codes if code and code not in hs_ids]
            if invalid_codes:
                info(
                    "Warning: some commodity codes are not present in HS metadata; "
                    f"count={len(invalid_codes)}"
                )


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def to_dataframe(payload) -> pd.DataFrame:
    if payload is None:
        return pd.DataFrame()
    if isinstance(payload, pd.DataFrame):
        return payload.copy()
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            return pd.DataFrame(payload["data"])
        return pd.DataFrame([payload])
    return pd.DataFrame(payload)


def fetch_batch(
    *,
    subscription_key: str,
    reporter_code: str,
    partner_code: str,
    classification: str,
    frequency: str,
    year: int,
    flow_code: str,
    commodity_batch: List[str],
) -> pd.DataFrame:
    if comtradeapicall is None:
        raise RuntimeError(
            "Missing dependency 'comtradeapicall'. Install it in your environment to run API pulls."
        )

    partner_arg = None if str(partner_code).lower() == "all" else str(partner_code)

    payload = comtradeapicall.getFinalData(
        subscription_key,
        typeCode="C",
        freqCode=frequency,
        clCode=classification,
        period=str(year),
        reporterCode=str(reporter_code),
        cmdCode=",".join(commodity_batch),
        flowCode=flow_code,
        partnerCode=partner_arg,
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=250000,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=None,
        includeDesc=True,
    )
    return to_dataframe(payload)


def slugify_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_") or "reporter"


def output_prefix(reporter_name: str, flows: List[str]) -> str:
    name = slugify_name(reporter_name)
    flow_set = set(flows)
    if flow_set == {"import"}:
        suffix = "import"
    elif flow_set == {"export"}:
        suffix = "export"
    else:
        suffix = "trade"
    return f"{name}_{suffix}"


def save_year_raw_file(flow_name: str, reporter_code: str, year: int, frame: pd.DataFrame) -> Path:
    target = RAW_DIR / flow_name / f"{reporter_code}_{flow_name}_{year}_raw.csv"
    frame.to_csv(target, index=False)
    if frame.empty:
        info(f"Warning: saved empty raw yearly file: {target}")
    else:
        info(f"Saved raw yearly file: {target}")
    return target


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "reporter_code",
                "reporter_name",
                "partner_code",
                "partner_name",
                "commodity_code",
                "commodity_desc",
                "flow",
                "trade_value",
                "net_wgt",
                "qty",
            ]
        )

    lowered_map = {str(col).lower(): col for col in frame.columns}

    def find_col(candidates: List[str]) -> str | None:
        for candidate in candidates:
            if candidate in lowered_map:
                return lowered_map[candidate]
        return None

    year_col = find_col(["period", "refyear"])
    reporter_code_col = find_col(["reportercode", "reporteriso"])
    reporter_name_col = find_col(["reporterdesc"])
    partner_code_col = find_col(["partnercode", "partneriso"])
    partner_name_col = find_col(["partnerdesc"])
    cmd_code_col = find_col(["cmdcode"])
    cmd_desc_col = find_col(["cmddesc"])
    flow_code_col = find_col(["flowcode"])
    flow_name_col = find_col(["flowdesc"])

    trade_value_candidates = [
        "primaryvalue",
        "tradevalue",
        "cifvalue",
        "fobvalue",
    ]
    trade_value_col = find_col(trade_value_candidates)
    net_wgt_col = find_col(["netwgt"])
    qty_col = find_col(["qty"])

    normalized = pd.DataFrame()
    normalized["year"] = frame[year_col] if year_col else None
    normalized["reporter_code"] = frame[reporter_code_col] if reporter_code_col else None
    normalized["reporter_name"] = frame[reporter_name_col] if reporter_name_col else None
    normalized["partner_code"] = frame[partner_code_col] if partner_code_col else None
    normalized["partner_name"] = frame[partner_name_col] if partner_name_col else None
    normalized["commodity_code"] = frame[cmd_code_col] if cmd_code_col else None
    normalized["commodity_desc"] = frame[cmd_desc_col] if cmd_desc_col else None

    if flow_name_col:
        normalized["flow"] = frame[flow_name_col].astype(str).str.lower().map(
            {"imports": "import", "exports": "export", "import": "import", "export": "export"}
        )
    elif flow_code_col:
        normalized["flow"] = frame[flow_code_col].astype(str).map({"M": "import", "X": "export"})
    else:
        normalized["flow"] = None

    normalized["trade_value"] = frame[trade_value_col] if trade_value_col else None
    normalized["net_wgt"] = frame[net_wgt_col] if net_wgt_col else None
    normalized["qty"] = frame[qty_col] if qty_col else None

    normalized["year"] = pd.to_numeric(normalized["year"], errors="coerce").astype("Int64")
    for col in ["reporter_code", "partner_code", "commodity_code", "flow"]:
        normalized[col] = normalized[col].astype(str)
        normalized[col] = normalized[col].replace({"<NA>": "", "nan": ""})

    for col in ["reporter_name", "partner_name", "commodity_desc"]:
        normalized[col] = normalized[col].fillna("").astype(str)

    normalized["trade_value"] = pd.to_numeric(normalized["trade_value"], errors="coerce").fillna(0.0)
    normalized["net_wgt"] = pd.to_numeric(normalized["net_wgt"], errors="coerce").fillna(0.0)
    normalized["qty"] = pd.to_numeric(normalized["qty"], errors="coerce").fillna(0.0)

    normalized = normalized[normalized["year"].notna()].copy()
    normalized["year"] = normalized["year"].astype(int)
    return normalized


def load_reference_partner_codes() -> pd.DataFrame:
    partner_file = REFERENCE_DIR / "partner_list.csv"
    if not partner_file.exists():
        return load_partner_codes_from_metadata()

    try:
        frame = pd.read_csv(partner_file)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        info(f"Warning: failed to read partner list {partner_file}: {exc}")
        return load_partner_codes_from_metadata()

    lowered = {str(c).lower(): c for c in frame.columns}
    code_col = (
        lowered.get("partnercode")
        or lowered.get("partner_code")
        or lowered.get("country.code")
        or lowered.get("code")
    )
    name_col = (
        lowered.get("partnerdesc")
        or lowered.get("partner_name")
        or lowered.get("country.name")
        or lowered.get("name")
    )

    if not code_col:
        info("Warning: partner_list.csv present but partner code column not detected.")
        return load_partner_codes_from_metadata()

    out = pd.DataFrame()
    out["partner_code"] = frame[code_col].astype(str)
    out["partner_name"] = frame[name_col].astype(str) if name_col else ""
    out = out.replace({"<NA>": "", "nan": ""}).drop_duplicates()
    if out.empty:
        return load_partner_codes_from_metadata()
    return out


def load_partner_codes_from_metadata() -> pd.DataFrame:
    partner_areas = load_metadata_results("partnerAreas.json")
    if not partner_areas:
        return pd.DataFrame(columns=["partner_code", "partner_name"])

    rows = []
    for row in partner_areas:
        code = str(
            row.get("PartnerCode")
            or row.get("partnerCode")
            or row.get("id")
            or ""
        ).strip()
        name = str(
            row.get("PartnerDesc")
            or row.get("partnerDesc")
            or row.get("text")
            or ""
        ).strip()
        if code:
            rows.append({"partner_code": code, "partner_name": name})

    out = pd.DataFrame(rows).drop_duplicates(subset=["partner_code"], keep="first")
    if not out.empty:
        info(
            "Using partnerAreas metadata as partner reference domain: "
            f"{len(out)} partners"
        )
    return out


def _normalize_code_for_match(code: str) -> str:
    text = str(code).strip()
    if text == "":
        return ""
    normalized = text.lstrip("0")
    return normalized if normalized != "" else "0"


def load_hs_partner_domain(commodity_codes: List[str]) -> pd.DataFrame:
    code_lengths = sorted({len(str(code).strip()) for code in commodity_codes if str(code).strip()})
    if len(code_lengths) != 1 or code_lengths[0] not in {2, 4, 6}:
        return pd.DataFrame(columns=["partner_code", "partner_name"])

    hs_level = code_lengths[0]
    file_map = {
        2: REFERENCE_DIR / "HSag2_partner.csv",
        4: REFERENCE_DIR / "HSag4_partner.csv",
        6: REFERENCE_DIR / "HSag6_partner.csv",
    }
    matrix_path = file_map[hs_level]
    if not matrix_path.exists():
        return pd.DataFrame(columns=["partner_code", "partner_name"])

    try:
        matrix = pd.read_csv(
            matrix_path,
            usecols=["Commodity.Code", "Partner.Code", "Partner.Name"],
            dtype=str,
        )
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        info(f"Warning: failed to read HS partner matrix {matrix_path}: {exc}")
        return pd.DataFrame(columns=["partner_code", "partner_name"])

    wanted_codes = {_normalize_code_for_match(code) for code in commodity_codes}
    matrix["_cmd_norm"] = matrix["Commodity.Code"].map(_normalize_code_for_match)
    subset = matrix[matrix["_cmd_norm"].isin(wanted_codes)].copy()

    if subset.empty:
        return pd.DataFrame(columns=["partner_code", "partner_name"])

    out = pd.DataFrame()
    out["partner_code"] = subset["Partner.Code"].fillna("").astype(str)
    out["partner_name"] = subset["Partner.Name"].fillna("").astype(str)
    out = out.replace({"<NA>": "", "nan": ""}).drop_duplicates()
    out = out[out["partner_code"] != ""]
    info(
        f"Using HSag{hs_level} partner matrix reference for partner domain: "
        f"{len(out)} partners"
    )
    return out


def build_complete_panel(
    normalized: pd.DataFrame,
    config: Dict,
    reference_partners: pd.DataFrame,
) -> pd.DataFrame:
    years = sorted(int(y) for y in config["years"])
    commodities = sorted(str(c) for c in config["commodity_codes"])
    flows = list(config["flows"])

    observed_partners = normalized[["partner_code", "partner_name"]].drop_duplicates()
    observed_partners = observed_partners[observed_partners["partner_code"] != ""]
    hs_matrix_partners = load_hs_partner_domain(commodities)

    if str(config["partner_code"]).lower() == "all":
        candidates = [df for df in [hs_matrix_partners, reference_partners, observed_partners] if not df.empty]
        if candidates:
            partner_domain = pd.concat(candidates, ignore_index=True)
            partner_domain = partner_domain.drop_duplicates(subset=["partner_code"], keep="first")
        else:
            partner_domain = observed_partners
    else:
        partner_domain = pd.DataFrame(
            [{"partner_code": str(config["partner_code"]), "partner_name": ""}]
        )

    if partner_domain.empty:
        partner_domain = pd.DataFrame([{"partner_code": "0", "partner_name": ""}])

    commodity_desc = (
        normalized[["commodity_code", "commodity_desc"]]
        .drop_duplicates(subset=["commodity_code"], keep="first")
        .set_index("commodity_code")["commodity_desc"]
        .to_dict()
    )

    reporter_code = str(config["reporter_code"])
    reporter_name = str(config["reporter_name"])

    grid = (
        pd.MultiIndex.from_product(
            [
                years,
                [reporter_code],
                [reporter_name],
                sorted(partner_domain["partner_code"].astype(str).unique()),
                commodities,
                flows,
            ],
            names=[
                "year",
                "reporter_code",
                "reporter_name",
                "partner_code",
                "commodity_code",
                "flow",
            ],
        )
        .to_frame(index=False)
    )

    partner_name_map = partner_domain.set_index("partner_code")["partner_name"].to_dict()
    grid["partner_name"] = grid["partner_code"].map(partner_name_map).fillna("")
    grid["commodity_desc"] = grid["commodity_code"].map(commodity_desc).fillna("")

    grouped = (
        normalized.groupby(
            [
                "year",
                "reporter_code",
                "reporter_name",
                "partner_code",
                "partner_name",
                "commodity_code",
                "commodity_desc",
                "flow",
            ],
            as_index=False,
        )[["trade_value", "net_wgt", "qty"]]
        .sum()
    )

    merged = grid.merge(
        grouped,
        on=[
            "year",
            "reporter_code",
            "reporter_name",
            "partner_code",
            "partner_name",
            "commodity_code",
            "commodity_desc",
            "flow",
        ],
        how="left",
    )

    for col in ["trade_value", "net_wgt", "qty"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)

    merged = merged.sort_values(["year", "flow", "commodity_code", "partner_code"])
    return merged


def create_wide_panel(long_panel: pd.DataFrame) -> pd.DataFrame:
    if long_panel.empty:
        return pd.DataFrame()

    long_panel = long_panel.copy()
    long_panel["commodity_flow"] = (
        long_panel["commodity_code"].astype(str) + "_" + long_panel["flow"].astype(str)
    )

    wide = (
        long_panel.pivot_table(
            index=["partner_code", "partner_name", "year"],
            columns="commodity_flow",
            values="trade_value",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .sort_values(["year", "partner_code"])
    )

    wide.columns.name = None
    return wide


def write_validation_report(
    *,
    config: Dict,
    reference_missing: List[Path],
    raw_rows: int,
    normalized_rows: int,
    long_rows: int,
    wide_shape: Tuple[int, int],
    errors: List[str],
) -> None:
    lines = [
        "UN Comtrade panel validation report",
        f"Ontology: {ONTOLOGY_PATH}",
        f"Reporter: {config['reporter_name']} ({config['reporter_code']})",
        f"Years: {config['years']}",
        f"Classification/Frequency: {config['classification']} / {config['frequency']}",
        f"Flows: {config['flows']}",
        f"Partner setting: {config['partner_code']}",
        f"Configured commodity count: {len(config['commodity_codes'])}",
        f"Raw rows downloaded: {raw_rows}",
        f"Rows after normalization: {normalized_rows}",
        f"Long panel rows: {long_rows}",
        f"Wide panel shape: {wide_shape}",
    ]

    if reference_missing:
        lines.append("Missing reference files:")
        for path in reference_missing:
            lines.append(f"- {path}")

    if errors:
        lines.append("Batch/API errors encountered:")
        for err in errors:
            lines.append(f"- {err}")
    else:
        lines.append("Batch/API errors encountered: none")

    VALIDATION_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_builder() -> None:
    info("Starting UN Comtrade panel builder")

    if not ONTOLOGY_PATH.exists():
        info(f"Warning: ontology report not found at {ONTOLOGY_PATH}")

    ensure_directories()
    config = load_config(CONFIG_PATH)
    validate_config_with_metadata(config)
    subscription_key = load_subscription_key(KEY_PATH)

    if comtradeapicall is None:
        raise RuntimeError(
            "The package 'comtradeapicall' is not installed. "
            "Install it and run again."
        )

    info("Using subscribed getFinalData API")

    _, missing_reference_files = check_reference_files()

    reporter_code = str(config["reporter_code"])
    classification = str(config["classification"])
    frequency = str(config["frequency"])
    partner_code = str(config["partner_code"])
    commodity_codes = [str(code) for code in config["commodity_codes"]]
    batch_size = int(config["max_codes_per_batch"])

    all_raw_frames: List[pd.DataFrame] = []
    batch_errors: List[str] = []

    for flow_name in config["flows"]:
        flow_code = FLOW_MAP[flow_name]
        for year in config["years"]:
            year_frames: List[pd.DataFrame] = []
            for batch_no, commodity_batch in enumerate(chunked(commodity_codes, batch_size), start=1):
                info(
                    f"Fetching {flow_name} | year={year} | batch={batch_no} | codes={len(commodity_batch)}"
                )
                try:
                    frame = fetch_batch(
                        subscription_key=subscription_key,
                        reporter_code=reporter_code,
                        partner_code=partner_code,
                        classification=classification,
                        frequency=frequency,
                        year=int(year),
                        flow_code=flow_code,
                        commodity_batch=commodity_batch,
                    )
                    frame["__flow_name"] = flow_name
                    frame["__year"] = int(year)
                    frame["__batch"] = batch_no
                    year_frames.append(frame)
                except Exception as exc:  # pragma: no cover - network/API side effects
                    error_message = (
                        f"Failed batch flow={flow_name} year={year} batch={batch_no}: {exc}"
                    )
                    info(f"Warning: {error_message}")
                    batch_errors.append(error_message)
                time.sleep(0.8)

            year_frame = pd.concat(year_frames, ignore_index=True) if year_frames else pd.DataFrame()
            save_year_raw_file(flow_name, reporter_code, int(year), year_frame)

            if not year_frame.empty:
                all_raw_frames.append(year_frame)

    if all_raw_frames:
        raw_all = pd.concat(all_raw_frames, ignore_index=True)
    else:
        raw_all = pd.DataFrame()

    raw_all_path = RAW_DIR / f"{reporter_code}_all_raw.csv"
    raw_all.to_csv(raw_all_path, index=False)

    info("Creating processed long panel")
    normalized = normalize_columns(raw_all)

    required = ["year", "reporter_code", "partner_code", "commodity_code", "flow", "trade_value"]
    missing_required = [col for col in required if col not in normalized.columns]
    if missing_required:
        raise RuntimeError(
            "Normalization failed to produce required columns: "
            + ", ".join(missing_required)
        )

    reference_partners = load_reference_partner_codes()
    long_panel = build_complete_panel(normalized, config, reference_partners)

    prefix = output_prefix(str(config["reporter_name"]), list(config["flows"]))
    long_path = PROCESSED_DIR / f"{prefix}_long_panel.csv"
    long_panel.to_csv(long_path, index=False)

    info("Creating wide panel")
    wide_panel = create_wide_panel(long_panel)
    wide_path = WIDE_DIR / f"{prefix}_wide_panel.csv"
    wide_panel.to_csv(wide_path, index=False)

    info("Validation complete")
    write_validation_report(
        config=config,
        reference_missing=missing_reference_files,
        raw_rows=len(raw_all),
        normalized_rows=len(normalized),
        long_rows=len(long_panel),
        wide_shape=tuple(wide_panel.shape),
        errors=batch_errors,
    )

    info(f"Saved processed long panel: {long_path}")
    info(f"Saved wide panel: {wide_path}")
    info(f"Saved validation report: {VALIDATION_REPORT_PATH}")


def main() -> int:
    try:
        run_builder()
        return 0
    except (ConfigurationError, FileNotFoundError, ValueError, RuntimeError) as exc:
        info(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
