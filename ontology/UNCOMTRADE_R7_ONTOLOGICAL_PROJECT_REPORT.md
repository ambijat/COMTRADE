# UN Comtrade R7 Ontological Project Report

**Project corpus examined:** `comtrade7`  
**Prepared for:** UNCOMTRADE project continuity and migration  
**Date:** 5 July 2026  
**Purpose:** To preserve the intellectual, technical, and procedural fidelity of the old R-based UN Comtrade project while defining the best course for recreating it under the current UN Comtrade API regime.

---

## 1. Executive assessment

The uploaded `comtrade7` archive is an old but successful R-based data-production system for UN Comtrade. Its failure today should not be read as a failure of the project design. The failure lies mainly in the historical API procedure on which it depended. The old project was built around direct URL calls to the legacy endpoint:

```text
http://comtrade.un.org/api/get?
```

That access logic used the old `max`, `type`, `freq`, `px`, `ps`, `r`, `p`, `rg`, `cc`, and `fmt` parameter grammar. This procedure is now obsolete, fragile, and no longer a dependable foundation for future research work.

The core finding is therefore precise:

> The old R7 project should not be revived by repairing its legacy URL calls. It should be recreated by preserving its ontology, data model, transformation sequence, and research logic, while replacing the download layer with the current UN Comtrade Plus / Developer API workflow.

The durable value of the project is its disciplined conversion of raw trade data into complete, zero-filled, partner × commodity × year panels. This logic remains valid and should be retained.

---

## 2. Corpus inventory

The uploaded corpus contains **67 files** arranged as a working R project. The project has these major internal zones:

| Zone | Role in old project | Files observed |
|---|---|---:|
| `download/` | API calls and raw CSV production | 26 |
| `dressing/` | Cleaning, joining, zero-filling, rectangularisation | 6 |
| `transpose/` | Conversion from long panel to wide partner matrix | 2 |
| `hs_class/` | HS classification metadata and partner × commodity grids | 14 |
| `st_class/` | SITC classification metadata and partner × commodity grids | 9 |
| `partner_list/` | Country/reporter/partner coding material | 3 |
| `newversion/` | Later JSON metadata from the newer Comtrade ecosystem | 6 |

File-type distribution:

| File type | Count | Meaning |
|---|---:|---|
| `.R` | 23 | Operational scripts |
| `.csv` | 29 | Reference grids, partner lists, classification tables |
| `.json` | 9 | Metadata and classification descriptions |
| `.txt` | 3 | Project notes and readme files |
| `.xlsx` | 1 | Comtrade country-code material |
| Other/no extension | 2 | R workspace/history artefacts |

The corpus is not a loose collection of scripts. It is a staged data factory with a clear internal ontology.

---

## 3. Original project sequence

The root readme defines the operational sequence as:

```text
1. Download
2. Dressing
3. Transpose
```

This sequence is the project’s foundational grammar. It should be preserved exactly at the conceptual level.

### 3.1 Download

The download layer obtains raw UN Comtrade data for:

- a selected reporter country or reporter set;
- one or more years;
- import and export flows;
- selected commodity classification and aggregation level;
- all partners or World partner;
- commodity batches or partner batches depending on the aggregation level.

### 3.2 Dressing

The dressing layer performs the crucial research transformation:

1. Load a complete partner × commodity reference grid.
2. Load the downloaded raw Comtrade CSV.
3. Select a small set of analytical columns.
4. Convert partner and commodity codes to stable character/string values.
5. Join observed trade data onto the complete grid.
6. Replace missing trade values with zero.
7. Add the year.
8. Save a cleaned annual file.

This is the old project’s most important methodological contribution.

### 3.3 Transpose

The transpose layer pivots the data so that partner countries become columns. The result is a wide matrix useful for analytical work, visual inspection, and panel-style modelling.

The old transpose logic can be expressed as:

```text
Rows    = commodity code and commodity name
Columns = partner countries
Values  = trade value in US dollars
```

---

## 4. Core ontology of the old project

The old project rests on one core data proposition:

```text
Reporter × Partner × Commodity × Year × Flow → Trade_USD
```

This proposition remains fully valid.

### 4.1 Primary entities

| Entity | Meaning | Old project representation | Modern representation |
|---|---|---|---|
| Reporter | Country whose trade is being reported | `r`, `country.code` | `reporterCode` |
| Partner | Trade partner | `p`, `Partner.Code` | `partnerCode` |
| Commodity | HS/SITC product code | `cc`, `Commodity.Code` | `cmdCode` |
| Year/period | Annual reporting period | `ps` | `period` |
| Flow | Import or export | `rg=1`, `rg=2` | `flowCode='M'`, `flowCode='X'` |
| Classification | HS/SITC version or as-reported classification | `px` | `clCode` |
| Trade value | Monetary value | `Trade.Value..US..` | usually `primaryValue` / trade value field in returned API dataframe |

### 4.2 Secondary entities

| Entity | Meaning | Preservation priority |
|---|---|---:|
| Partner list | Stable country-code table | Very high |
| HS aggregation grid | Commodity × partner skeleton | Very high |
| SITC aggregation grid | SITC × partner skeleton | Medium-high |
| Raw yearly files | Audit trail of API extraction | High |
| Processed yearly files | Zero-filled analytical panels | Very high |
| Wide transpose files | Legacy analytical output | High |
| API key | Authentication secret | Must not be stored in code |
| Configuration | Years, reporters, flows, classification, aggregation | Very high |

---

## 5. Classification ontology

The old readme records a classification memory that is important for maintaining fidelity:

| Label | Meaning in old corpus |
|---|---|
| `HS0` | HS 1992 |
| `HS1` | HS 1996 |
| `HS2` | HS 2002 |
| `HS3` | HS 2007 |
| `HS4` | HS 2012 |
| `HS` | HS as reported |
| `S1`, `S2`, `S3`, `S4` | SITC revisions |
| `AG1`, `AG2`, `AG4`, `AG6` | Aggregated commodity digit levels |

The old scripts contain separate treatment for HS and SITC. The HS branch is more complete and operationally central in the observed project. The recreated project should therefore prioritise HS first and only later generalise to SITC.

---

## 6. Flow ontology

The old API uses numeric flow codes:

| Old flow code | Old meaning | Modern Comtrade API equivalent | Project label |
|---:|---|---|---|
| `rg=1` | Import | `flowCode='M'` | `import` |
| `rg=2` | Export | `flowCode='X'` | `export` |

This mapping must be hard-coded into the migration layer so that old file semantics remain faithful.

---

## 7. Spatial ontology

The old project distinguishes three spatial modes:

### 7.1 Single reporter, all partners

Example: Bangladesh as reporter, all partners as trade partners.

```text
reporter = 50
partner  = all
```

This is the standard country-panel mode.

### 7.2 Single reporter, selected partner packs

The old readme notes that large countries such as China create row-limit problems at higher aggregation levels. For such cases, partner chunks were used.

```text
partner batch = 5 countries at a time
```

### 7.3 World partner mode

The old corpus includes scripts with `World` logic. In Comtrade grammar, World is often represented as partner `0`.

```text
partner = 0
```

This mode is analytically different from all-partner mode. It gives total trade with the World, not the full bilateral partner matrix.

---

## 8. Temporal ontology

The old project is annual. The default frequency is:

```text
freq = A
```

The main period loop is a vector of years. The observed AG2 script, for example, uses:

```r
year <- as.character(c(2010:2019))
```

For faithful migration, period handling should remain annual by default. Monthly data should not be introduced into the first recreated version because it changes the research ontology and creates unnecessary volume.

---

## 9. Data transformation ontology

The old project’s transformation logic has three states:

```text
Raw state → Dressed state → Transposed state
```

### 9.1 Raw state

Raw files preserve the API return as closely as possible. Their function is auditability.

Recommended modern path:

```text
data/output/raw/<reporter>/<flow>/<year>_raw.csv
```

### 9.2 Dressed state

Dressed files are complete rectangular panels. Their function is comparability.

Recommended modern path:

```text
data/output/processed/<reporter>/<flow>/<year>_processed.csv
```

### 9.3 Transposed state

Transposed files are wide analytical matrices. Their function is use in visualisation, modelling, and teaching/research outputs.

Recommended modern path:

```text
data/output/wide/<reporter>/<flow>/<year>_wide.csv
```

---

## 10. What worked well in the old R project

### 10.1 It had a clear project ontology

The project consistently framed trade as a relational object:

```text
country reports trade with partner in commodity for year and flow
```

This is conceptually robust.

### 10.2 It used complete grids

The use of `HSag2_partner.csv`, `HSag4_partner.csv`, `HSag6_partner.csv`, and related reference files allowed the project to avoid a common problem: downloaded Comtrade data only contains observed trade rows. Missing rows can mean zero, non-reporting, filtering, or API omission. The old project imposed a stable reference skeleton and then filled missing trade values as zero.

This creates a stable matrix across time.

### 10.3 It separated raw and processed data

The distinction between raw downloads and dressed outputs is methodologically sound. It allows later debugging and reproducibility checks.

### 10.4 It anticipated API limits

The old readme explicitly records request and row limits and proposes chunking strategies. This shows that the project was built from practical experience, not abstract coding alone.

### 10.5 It preserved classification metadata

The `hs_class`, `st_class`, and `newversion` directories contain important classification knowledge. These should not be discarded.

---

## 11. What failed or became obsolete

### 11.1 Legacy URL dependency

The old scripts rely on direct URL construction and `read.csv(url)`. This is the main point of collapse.

Old logic:

```r
read.csv("http://comtrade.un.org/api/get?...", header=TRUE)
```

Modern logic must use authenticated API access through current tools.

### 11.2 Hard-coded paths

The old project contains absolute paths such as:

```text
G:/R5/comtrade7/...
/media/ambijat/DATAWORLD/R7/comtrade7/...
```

These paths reflect successful historical use, but they prevent portability.

### 11.3 Repeated scripts

The old project has multiple near-duplicate R scripts for different aggregation levels and world/country modes. This was practical in the old era but is not ideal for maintenance.

### 11.4 Manual working-directory dependence

The project relies heavily on `setwd()`. This creates fragility because a script’s behaviour changes depending on where it is launched.

### 11.5 API key risk

Any modern reconstruction must not embed the subscription key inside source code. The key should be stored in a local file that is excluded from Git.

### 11.6 Field-name instability

The old dressing scripts expect fields such as:

```text
Trade.Value..US..
Partner.Code
Commodity.Code
```

Modern API output may use different column names. The migration must include a column-normalisation layer.

---

## 12. Old-to-new API translation ontology

| Old R API parameter | Old meaning | Modern Python/API equivalent |
|---|---|---|
| `type='C'` | Goods/commodities | `typeCode='C'` |
| `freq='A'` | Annual data | `freqCode='A'` |
| `px='HS'` | HS classification | `clCode='HS'` or specific HS revision where supported |
| `ps=<year>` | Period | `period='<year>'` |
| `r=<reporter>` | Reporter country | `reporterCode='<code>'` |
| `p='all'` | All partners | `partnerCode=None` or accepted all-partner setting |
| `p='0'` | World partner | `partnerCode='0'` |
| `rg=1` | Import | `flowCode='M'` |
| `rg=2` | Export | `flowCode='X'` |
| `cc=<codes>` | Commodity codes | `cmdCode='01,02,...'` |
| `fmt='csv'` | CSV return | JSON/dataframe return, then CSV export |

The official `comtradeapicall` Python package documents current Comtrade API access, including `getFinalData`, subscription-key use, final-data extraction, metadata, and bulk functions. The current R package `comtradr` also exposes a modern `ct_get_data()` grammar based on `commodity_classification`, `commodity_code`, `flow_direction`, `reporter`, `partner`, and `primary_token`.

---

## 13. Recommended modern project architecture

The best course is to create a new project that treats old R7 as an archival source and implements its logic in Python.

```text
COMTRADE_RECREATED/
├── README.md
├── ONTOLOGICAL_PROJECT_REPORT.md
├── comtrade_panel_builder.py
├── config/
│   └── panel_config.json
├── secrets/
│   └── comtrade_primary_key.txt
├── data/
│   ├── reference/
│   │   ├── partner_list.csv
│   │   ├── HSag2_partner.csv
│   │   ├── HSag4_partner.csv
│   │   └── HSag6_partner.csv
│   └── output/
│       ├── raw/
│       ├── processed/
│       └── wide/
├── archive/
│   └── comtrade7_original/
└── tests/
    └── test_small_panel.py
```

### 13.1 Why Python should be the main reconstruction language

Python is preferable for the recreated system because:

- the official UN Comtrade package is Python-first;
- `pandas` reproduces the old `dplyr`/`tidyr` transformations cleanly;
- path handling via `pathlib` is much safer than `setwd()`;
- project configuration can be separated from execution;
- the same code can later support CLI, GUI, notebooks, or scheduled runs.

### 13.2 Where R still has value

R should not be discarded intellectually. The old R scripts should remain in an archive because they preserve:

- the exact historical workflow;
- the batching decisions;
- country and commodity code assumptions;
- research practice embedded in comments and readmes.

However, R should no longer be the execution layer unless a modern `comtradr` version is separately implemented.

---

## 14. Secret-key architecture

The subscription key should be stored in:

```text
secrets/comtrade_primary_key.txt
```

The `.gitignore` must include:

```gitignore
secrets/
*.key
.env
```

The Python script should read the key at runtime:

```python
from pathlib import Path

key_path = Path('secrets/comtrade_primary_key.txt')
subscription_key = key_path.read_text().strip()
```

The key must not be planted inside the script because scripts are likely to be copied, shared, zipped, committed to Git, or submitted to other workflows.

---

## 15. Fidelity principles for the recreated project

To maintain fidelity, the recreated project should follow these principles.

### Principle 1: Preserve the three-stage grammar

Do not collapse everything into one opaque process. Preserve:

```text
Download → Dressing → Transpose
```

### Principle 2: Preserve raw data

Always save raw API returns before dressing.

### Principle 3: Preserve complete-grid logic

Always build the dressed panel from a partner × commodity reference grid.

### Principle 4: Preserve import/export separation

Do not merge imports and exports prematurely. Keep separate flow folders.

### Principle 5: Preserve annual file identity

Continue to save data year-wise. This helps debugging, reruns, and partial recovery.

### Principle 6: Preserve old code as archive, not as live dependency

The old R scripts should be kept in `archive/`, but the new project should not depend on them.

### Principle 7: Externalise configuration

Reporter countries, years, flows, classification, commodity level, batch size, and output folders should live in JSON/YAML configuration.

### Principle 8: Normalise API columns

Modern API responses must be translated into canonical project columns:

```text
Reporter.Code
Reporter
Partner.Code
Partner
Commodity.Code
Commodity
Year
Flow
Trade_USD
```

### Principle 9: Log every API request

Every run should preserve a request log containing:

- timestamp;
- reporter;
- period;
- flow;
- commodity batch;
- partner setting;
- success/failure;
- row count;
- output file.

### Principle 10: Separate reproducibility from convenience

Convenience features such as GUI buttons or dashboards should not replace the core reproducible command-line pipeline.

---

## 16. Best course ahead

The best course is a four-phase migration.

### Phase 1: Archival stabilisation

Create a preserved copy of the old project:

```text
archive/comtrade7_original/
```

Add a note that these scripts are not expected to run directly under the current Comtrade regime.

Deliverables:

- original R scripts preserved;
- old readmes preserved;
- old reference CSVs copied into `data/reference/`;
- this ontological report committed to the project.

### Phase 2: Minimal Python recreation

Build a Python script that reproduces the AG2 workflow first.

Why AG2 first?

- AG2 is manageable;
- the old readme says the latest coding logic was strongest in AG2;
- commodity batching by 20 is already explicit;
- it is easier to validate before AG4/AG6 expansion.

Deliverables:

- `comtrade_panel_builder.py`;
- `config/panel_config.json`;
- `secrets/comtrade_primary_key.txt` locally;
- raw, processed, and wide output folders.

### Phase 3: Validation against old R logic

Run a small historical test case:

```text
Reporter: Bangladesh or India
Years: 2010–2011
Flow: import and export
Classification: HS
Aggregation: AG2
Partner: all
```

Check whether the new Python output has:

- same row logic as old `HSag2_partner.csv` grid;
- same partner/commodity rectangularity;
- missing values converted to zero;
- imports and exports saved separately;
- transposed wide file generated correctly.

### Phase 4: Generalisation

After AG2 is validated, extend to:

- AG4;
- AG6;
- World partner mode;
- selected partner-pack mode for large reporters;
- SITC/S4 if still needed;
- metadata refresh from new Comtrade reference endpoints.

---

## 17. Minimum viable recreated workflow

The first recreated workflow should be intentionally modest:

```text
Input:
  reporters: [699]
  years: [2009, 2010]
  flows: [import, export]
  classification: HS
  aggregation: AG2
  commodity_batch_size: 20
  partner_mode: all

Output:
  raw CSVs
  processed zero-filled CSVs
  wide partner-matrix CSVs
```

This is the correct proof-of-continuity test.

---

## 18. Suggested configuration schema

```json
{
  "project_name": "UNCOMTRADE_R7_RECREATED",
  "classification": "HS",
  "aggregation_level": "AG2",
  "reporters": [699],
  "years": [2009, 2010],
  "flows": ["import", "export"],
  "partner_mode": "all",
  "commodity_batch_size": 20,
  "api": {
    "typeCode": "C",
    "freqCode": "A",
    "breakdownMode": "classic",
    "maxRecords": 250000
  },
  "paths": {
    "subscription_key_file": "secrets/comtrade_primary_key.txt",
    "reference_dir": "data/reference",
    "output_dir": "data/output"
  }
}
```

---

## 19. Canonical output schema

The dressed output should use this canonical schema:

| Column | Type | Meaning |
|---|---|---|
| `Reporter.Code` | string/integer | Reporter country code |
| `Reporter` | string | Reporter country name |
| `Partner.Code` | string/integer | Partner country code |
| `Partner` | string | Partner country name |
| `Commodity.Code` | string | Commodity code, preserving leading zeroes |
| `Commodity` | string | Commodity description |
| `Year` | integer/string | Reporting year |
| `Flow` | string | `import` or `export` |
| `Trade_USD` | numeric | Trade value in current US dollars |
| `Source` | string | API or fallback/source marker |
| `Run_ID` | string | Unique run identifier |

The old R scripts did not always preserve all these columns, but adding them improves reproducibility while remaining faithful to the old model.

---

## 20. Error-handling ontology

The old readme notes that if transpose gives a key error, the relevant year should be redownloaded. This observation should become formal error handling.

| Error type | Likely cause | Modern response |
|---|---|---|
| Empty API response | No trade, wrong parameter, API limit, or outage | Save empty raw file with log entry; continue |
| Missing expected column | API schema change | Run column-normalisation map; fail clearly if unresolved |
| Duplicate rows | API returns repeated commodity/partner entries | Group by canonical keys and sum `Trade_USD` |
| Row-limit breach | Request too large | Reduce commodity or partner batch size |
| Rate limit | Too many calls | Sleep/backoff and resume |
| Partial file | Interrupted run | Use request log to rerun only failed batches |
| Transpose key error | Bad processed file or missing columns | Validate processed schema before transpose |

---

## 21. Logging requirements

A modern recreated project should create:

```text
data/output/logs/run_<timestamp>.csv
```

with these fields:

| Field | Meaning |
|---|---|
| `run_id` | Unique execution ID |
| `timestamp` | Request time |
| `reporter_code` | Reporter |
| `year` | Period |
| `flow` | Import/export |
| `commodity_batch` | Commodity codes requested |
| `partner_code` | Partner setting |
| `status` | success/failure/empty |
| `rows_returned` | Number of rows |
| `raw_file` | Raw output path |
| `error_message` | Failure message if any |

This will make the recreated system stronger than the old R7 project while preserving its spirit.

---

## 22. Treatment of old reference files

The old reference files are not junk. They are part of the project’s intellectual infrastructure.

### 22.1 Preserve as historical reference

Keep copies of:

```text
HSag2_partner.csv
HSag4_partner.csv
HSag6_partner.csv
h4ag2_partner.csv
s4ag1_partner.csv
s4ag2_partner.csv
s4ag4_partner.csv
partner_list.csv
```

### 22.2 Use as fallback grids

In the first Python recreation, use the old grids to reproduce the old matrix exactly.

### 22.3 Add metadata refresh later

Only after the recreation is validated should a metadata-refresh step be added. Otherwise, the first migration may accidentally change the research object by altering the commodity/partner universe.

---

## 23. What not to do

The following paths should be avoided:

### 23.1 Do not merely patch the old URL

Replacing one URL with another inside the old R function will not solve the deeper problem. The parameter grammar, authentication, output schema, and limits have changed.

### 23.2 Do not plant the subscription key inside scripts

This creates a security and reproducibility problem.

### 23.3 Do not immediately redesign the entire research system

The first objective is continuity, not innovation. Recreate AG2 first, prove equivalence, then expand.

### 23.4 Do not mix raw and processed outputs

Raw and processed files must remain separate.

### 23.5 Do not delete the R code

The R code is an archive of methodological practice and should be retained.

---

## 24. Proposed repository README summary

The new repository should state:

```text
This project recreates the old R7 UN Comtrade workflow under the modern UN Comtrade API. The old project used legacy direct API URL calls that are no longer dependable. The recreated project preserves the original ontology: Download → Dressing → Transpose. It uses a local subscription-key file, modern API calls, pandas transformations, and old reference grids to maintain fidelity with the historical project.
```

---

## 25. Immediate next implementation tasks

| Priority | Task | Output |
|---:|---|---|
| 1 | Create recreated project folder | `COMTRADE_RECREATED/` |
| 2 | Copy old R7 corpus into archive | `archive/comtrade7_original/` |
| 3 | Copy reference CSVs | `data/reference/` |
| 4 | Add local secret-key path | `secrets/comtrade_primary_key.txt` |
| 5 | Add `.gitignore` | Exclude secrets and generated data if needed |
| 6 | Run AG2 test | raw/processed/wide output |
| 7 | Validate panel shape | row counts and zero-fill check |
| 8 | Add logs | reproducible request trail |
| 9 | Extend to AG4/AG6 | higher-resolution commodity panels |
| 10 | Add metadata refresh | modern reference-data update option |

---

## 26. Project philosophy

The old project reflects a research philosophy that should be explicitly preserved:

1. **Trade data must be made comparable before it becomes analytically useful.**
2. **Downloaded data is not yet research data.**
3. **The absent row is an epistemic problem.** It must be handled by a complete grid and a clear rule.
4. **Commodity classification is not a technical afterthought.** It defines the level at which the world economy is being observed.
5. **The API is only an acquisition layer.** The actual research value lies in the transformation architecture.
6. **Fidelity requires retaining old assumptions while modernising execution.**

This is why the migration should be ontological, not merely syntactic.

---

## 27. Final recommendation

The old R7 Comtrade project should be preserved as a methodological archive and recreated as a modern Python project. The priority should be:

```text
Preserve ontology → Replace API layer → Recreate panel builder → Validate AG2 → Expand to AG4/AG6 → Add metadata refresh
```

The best course ahead is not to fight the discontinued old Comtrade procedure. The best course is to carry forward the successful R7 design into a new execution environment.

The central continuity formula should guide all future work:

```text
Old R7 ontology + current Comtrade API + local gitignored key + pandas panel builder = faithful reconstruction
```

---

## 28. Source notes

This report is based on direct inspection of the uploaded `comtrade7` corpus, including the root readme, download scripts, dressing scripts, transpose scripts, HS/SITC classification folders, partner-list files, and newer JSON metadata. Current API direction was cross-checked against public documentation for the official `uncomtrade/comtradeapicall` Python package and the `ropensci/comtradr` R package.

Useful current reference points:

- Official Python package: `uncomtrade/comtradeapicall`
- Official/current R package ecosystem: `ropensci/comtradr`
- Current Comtrade Plus platform: `comtradeplus.un.org`

