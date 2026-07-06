# UN Comtrade R7 Recreated Workflow

## What this recreated project does
This project reconstructs the original R7 UN Comtrade pipeline using modern Python while preserving the old ontology and processing sequence:

1. Download raw trade data from UN Comtrade.
2. Dress/clean into a complete long panel.
3. Transpose into wide analytical outputs.

The key goal is ontology fidelity, not a generic downloader.

## Why the old R procedure no longer works
The old scripts relied on the legacy URL API style (`http://comtrade.un.org/api/get?...`) and old parameter grammar. That route is no longer the dependable procedure. This rebuild uses modern API access through `comtradeapicall` and subscribed `getFinalData` calls.

## Ontology reference location
The conceptual authority is:

- `ontology/UNCOMTRADE_R7_ONTOLOGICAL_PROJECT_REPORT.md`

## Subscription key placement
Place your subscription key (plain text only) in:

- `secrets/comtrade_primary_key.txt`

Do not place the key inside source code.

## How to run
```bash
cd /media/ambijat/SOPRANO2/GPT_workflow/COMTRADE
source .venv/bin/activate
pip install -r requirements.txt
python comtrade_panel_builder.py
```

## GUI mode for interactive variable control
To adjust reporter, years, flows, partner, commodity codes, and batch size interactively:

```bash
cd /media/ambijat/SOPRANO2/GPT_workflow/COMTRADE
source .venv/bin/activate
python comtrade_panel_gui.py
```

The GUI writes `config/panel_config.json` and runs `comtrade_panel_builder.py` with live logs.

Current GUI UX model:

- Reporter is selected by name; reporter code is resolved automatically in the background from metadata.
- Years are entered as a start and end year range (start - end).
- Classification supports `HS` and `SITC` (mapped internally to `S4` for SITC workflows).
- AG level selection is available (`HS`: AG2/AG4/AG6, `SITC`: AG1/AG2/AG4).
- Commodity selection is metadata-driven with search and multi-select, instead of manual comma text editing.
- Run log is available in a separate tab so commodity selection remains the primary workspace.

## Output folders
Running the script creates/uses:

- `comtrade_panel_output/raw/import/`
- `comtrade_panel_output/raw/export/`
- `comtrade_panel_output/processed/`
- `comtrade_panel_output/wide/`
- `comtrade_panel_output/validation_report.txt`

## Expand from test run to larger HS2/HS4/HS6 runs
Edit `config/panel_config.json`:

1. Increase `years` range.
2. Add `flows` as `import`, `export`, or both.
3. Replace `commodity_codes` with HS2, HS4, or HS6 lists.
4. Tune `max_codes_per_batch` for stable API batching.

The script is designed to scale from the initial small test configuration to larger ontology-faithful panel production.

## Staged expansion configs created from ontology metadata
These ready-to-run configs were generated from `reference/metadata/HS.json` for chapters 01-05:

- `config/panel_config_hs4_01_05.json` (46 HS4 codes)
- `config/panel_config_hs6_01_05_stage1.json` (first 200 HS6 codes)

The active config currently points to the HS4 stage (`config/panel_config.json` contains the HS4 code list).

## Fresh metadata incorporation
The builder now consumes fresh metadata directly from `reference/metadata/`:

- `Reporters.json`: validates `reporter_code` and checks reporter name consistency.
- `Frequency.json`: validates configured frequency values (for example, `A`).
- `partnerAreas.json`: validates partner code and acts as fallback partner reference if CSV partner lists are missing/unreadable.
- `HS.json`: validates commodity codes for HS configurations and supports staged HS code generation workflows.

This means newly downloaded metadata files in `reference/metadata/` are actively used by the runtime checks, not only stored as static references.

## Session audit and direction note
For the latest full audit of structure, implementation journey, ontology-fidelity status, and proposed roadmap, see:

- `ontology/SESSION_AUDIT_AND_DIRECTION_2026-07-05.md`

## Project poster page (repository face)
A poster-style project page has been added to give this repository a visual front page:

- Local file: `index.html`

This page highlights:

- The 2026 refurbishment narrative and project arc.
- GUI-first workflow and newly introduced features.
- Placeholder panels for screenshots and validation visuals.
- A compact pipeline snapshot from acquisition to QA output.

### Add your real screenshots
Place screenshots at these paths to populate the poster gallery:

- `docs/screenshots/gui-overview.png`
- `docs/screenshots/panel-output.png`
- `docs/screenshots/validation-report.png`

### Optional GitHub Pages publication
If GitHub Pages is enabled for this repository, this poster can serve as the public project homepage.

- Suggested URL after enabling Pages: `https://ambijat.github.io/COMTRADE/`
