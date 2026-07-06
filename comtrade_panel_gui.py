"""
UN Comtrade Panel GUI (Tkinter)

This GUI is an interactive control surface over comtrade_panel_builder.py.
Users set panel variables visually, save config/panel_config.json, and run
builder pulls while watching run logs.
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "panel_config.json"
BUILDER_PATH = BASE_DIR / "comtrade_panel_builder.py"
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"

REFERENCE_METADATA_DIR = BASE_DIR / "reference" / "metadata"
ALT_METADATA_DIR = BASE_DIR / "metadata"

DEFAULT_CONFIG = {
    "reporter_code": "699",
    "reporter_name": "India",
    "years": [2009, 2010],
    "classification": "HS",
    "frequency": "A",
    "flows": ["import", "export"],
    "partner_code": "all",
    "commodity_codes": ["01", "02", "03", "04", "05"],
    "max_codes_per_batch": 20,
}

HS_AG_LEVELS = ["AG2", "AG4", "AG6"]
SITC_AG_LEVELS = ["AG1", "AG2", "AG4"]


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self.tip_window is not None:
            return

        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            padx=6,
            pady=4,
            wraplength=360,
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class ComtradeGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("UN Comtrade Panel Builder")
        self.geometry("1160x820")

        self.process: subprocess.Popen | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()

        self.reporters_by_name: dict[str, str] = {}
        self.name_by_reporter_code: dict[str, str] = {}
        self.frequency_values: list[str] = ["A", "M"]

        self.commodity_catalog: list[dict] = []
        self.filtered_commodities: list[dict] = []
        self.visible_codes: list[str] = []
        self.selected_codes: set[str] = set()

        self._build_widgets()
        self._load_metadata_sources()
        self._load_or_default_config()
        self.after(120, self._drain_log_queue)

    def _build_widgets(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(root, text="Panel Configuration", padding=10)
        form.pack(fill=tk.X, side=tk.TOP)

        self.reporter_name_var = tk.StringVar()
        self.reporter_code_info_var = tk.StringVar(value="Reporter code: -")
        self.start_year_var = tk.StringVar()
        self.end_year_var = tk.StringVar()

        self.classification_var = tk.StringVar(value="HS")
        self.ag_level_var = tk.StringVar(value="AG2")
        self.frequency_var = tk.StringVar(value="A")
        self.partner_code_var = tk.StringVar(value="all")
        self.batch_size_var = tk.StringVar(value="20")

        self.flow_import_var = tk.BooleanVar(value=True)
        self.flow_export_var = tk.BooleanVar(value=True)

        self.search_var = tk.StringVar()
        self.selected_count_var = tk.StringVar(value="Selected commodities: 0")
        self.run_summary_var = tk.StringVar(value="Ready: HS AG2 | 0 commodities selected")
        self.show_selected_only = False
        self.show_selected_btn_var = tk.StringVar(value="Show selected")

        for variable in [
            self.start_year_var,
            self.end_year_var,
            self.flow_import_var,
            self.flow_export_var,
            self.frequency_var,
        ]:
            variable.trace_add("write", self._on_summary_trigger)

        ttk.Label(form, text="Reporter name").grid(row=0, column=0, sticky="w", pady=6)
        self.reporter_combo = ttk.Combobox(
            form,
            textvariable=self.reporter_name_var,
            values=[],
            state="normal",
            width=40,
        )
        self.reporter_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6)
        self.reporter_combo.bind("<<ComboboxSelected>>", self._on_reporter_changed)
        self.reporter_combo.bind("<FocusOut>", self._on_reporter_changed)
        ttk.Label(form, textvariable=self.reporter_code_info_var).grid(
            row=0, column=3, sticky="w", pady=6
        )

        ttk.Label(form, text="Years").grid(row=1, column=0, sticky="w", pady=6)
        years_frame = ttk.Frame(form)
        years_frame.grid(row=1, column=1, columnspan=2, sticky="w", pady=6)
        ttk.Entry(years_frame, textvariable=self.start_year_var, width=10).pack(side=tk.LEFT)
        ttk.Label(years_frame, text=" - ").pack(side=tk.LEFT, padx=4)
        ttk.Entry(years_frame, textvariable=self.end_year_var, width=10).pack(side=tk.LEFT)

        ttk.Label(form, text="Classification").grid(row=2, column=0, sticky="w", pady=6)
        classification_combo = ttk.Combobox(
            form,
            textvariable=self.classification_var,
            values=["HS", "SITC"],
            state="readonly",
            width=20,
        )
        classification_combo.grid(row=2, column=1, sticky="w", pady=6)
        classification_combo.bind("<<ComboboxSelected>>", self._on_classification_changed)

        ttk.Label(form, text="AG level").grid(row=2, column=2, sticky="w", pady=6)
        self.ag_combo = ttk.Combobox(
            form,
            textvariable=self.ag_level_var,
            values=HS_AG_LEVELS,
            state="readonly",
            width=16,
        )
        self.ag_combo.grid(row=2, column=3, sticky="w", pady=6)
        self.ag_combo.bind("<<ComboboxSelected>>", self._on_ag_level_changed)

        ttk.Label(form, text="Frequency").grid(row=3, column=0, sticky="w", pady=6)
        self.frequency_combo = ttk.Combobox(
            form,
            textvariable=self.frequency_var,
            values=self.frequency_values,
            state="readonly",
            width=20,
        )
        self.frequency_combo.grid(row=3, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Flows").grid(row=3, column=2, sticky="w", pady=6)
        flow_frame = ttk.Frame(form)
        flow_frame.grid(row=3, column=3, sticky="w", pady=6)
        ttk.Checkbutton(flow_frame, text="import", variable=self.flow_import_var).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Checkbutton(flow_frame, text="export", variable=self.flow_export_var).pack(side=tk.LEFT)

        ttk.Label(form, text="Partner code").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.partner_code_var, width=20).grid(
            row=4, column=1, sticky="w", pady=6
        )

        ttk.Label(form, text="Max codes per batch").grid(row=4, column=2, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.batch_size_var, width=12).grid(
            row=4, column=3, sticky="w", pady=6
        )

        for c in range(4):
            form.columnconfigure(c, weight=1)

        summary_row = ttk.Frame(root)
        summary_row.pack(fill=tk.X, pady=(8, 2))
        ttk.Label(summary_row, textvariable=self.run_summary_var).pack(side=tk.LEFT)

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, pady=(10, 8))

        load_btn = ttk.Button(actions, text="Load config", command=self._load_or_default_config)
        load_btn.pack(side=tk.LEFT, padx=(0, 8))
        save_btn = ttk.Button(actions, text="Save config", command=self._save_config)
        save_btn.pack(side=tk.LEFT, padx=(0, 8))
        reload_btn = ttk.Button(actions, text="Reload metadata", command=self._reload_metadata)
        reload_btn.pack(side=tk.LEFT, padx=(0, 8))
        run_btn = ttk.Button(actions, text="Run builder", command=self._run_builder)
        run_btn.pack(side=tk.LEFT, padx=(16, 8))
        stop_btn = ttk.Button(actions, text="Stop run", command=self._stop_builder)
        stop_btn.pack(side=tk.LEFT)

        ToolTip(
            load_btn,
            "Step 1 (optional): Load values from config/panel_config.json into the GUI.",
        )
        ToolTip(
            save_btn,
            "Step 2: Validate current form + commodity selection and write config/panel_config.json.",
        )
        ToolTip(
            reload_btn,
            "Use before selection if metadata files changed. Reloads reporters, frequencies, and commodity catalogs.",
        )
        ToolTip(
            run_btn,
            "Step 3: Save config and start comtrade_panel_builder.py. Recommended sequence: Reload metadata -> Load config -> adjust selections -> Run builder.",
        )
        ToolTip(
            stop_btn,
            "Emergency stop for an active run. Use only while a run is in progress.",
        )

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True)

        commodity_tab = ttk.Frame(notebook, padding=8)
        notebook.add(commodity_tab, text="Commodity Selector")

        log_tab = ttk.Frame(notebook, padding=8)
        notebook.add(log_tab, text="Run Log")

        search_row = ttk.Frame(commodity_tab)
        search_row.pack(fill=tk.X)
        ttk.Label(search_row, text="Search commodities").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        self.search_var.trace_add("write", self._on_search_changed)

        ttk.Button(
            search_row,
            textvariable=self.show_selected_btn_var,
            command=self._toggle_show_selected,
        ).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(search_row, text="Clear all", command=self._clear_selected).pack(side=tk.LEFT)

        ttk.Label(
            commodity_tab,
            text="Tip: click items to toggle selection. Use Show selected to review picks, and Clear all to reset.",
        ).pack(anchor="w", pady=(6, 0))

        list_frame = ttk.Frame(commodity_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.commodity_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
        )
        self.commodity_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.commodity_listbox.bind("<<ListboxSelect>>", self._on_commodity_select)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.commodity_listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.commodity_listbox.configure(yscrollcommand=scroll.set)

        status_row = ttk.Frame(commodity_tab)
        status_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(status_row, textvariable=self.selected_count_var).pack(side=tk.LEFT)

        self.log_text = tk.Text(log_tab, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _metadata_path_candidates(self, file_name: str) -> list[Path]:
        return [
            REFERENCE_METADATA_DIR / file_name,
            ALT_METADATA_DIR / file_name,
        ]

    def _load_metadata_payload(self, names: list[str]) -> list[dict]:
        for name in names:
            for path in self._metadata_path_candidates(name):
                if not path.exists():
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue

                if isinstance(payload, dict) and isinstance(payload.get("results"), list):
                    return payload["results"]
                if isinstance(payload, list):
                    return payload
        return []

    def _load_metadata_sources(self) -> None:
        reporter_rows = self._load_metadata_payload(["Reporters.json", "reporter.json"])
        self.reporters_by_name = {}
        self.name_by_reporter_code = {}
        for row in reporter_rows:
            code = str(row.get("reporterCode") or row.get("id") or "").strip()
            name = str(row.get("reporterDesc") or row.get("text") or "").strip()
            if code and name:
                self.reporters_by_name[name] = code
                self.name_by_reporter_code[code] = name

        reporter_names = sorted(self.reporters_by_name.keys())
        self.reporter_combo.configure(values=reporter_names)

        frequency_rows = self._load_metadata_payload(["Frequency.json"])
        if frequency_rows:
            values = [str(row.get("id") or "").strip() for row in frequency_rows]
            values = [v for v in values if v]
            if values:
                self.frequency_values = values
                self.frequency_combo.configure(values=self.frequency_values)

        self._refresh_commodity_catalog()

    def _reload_metadata(self) -> None:
        self._load_metadata_sources()
        self._append_log("Reloaded metadata sources.\n")

    def _on_reporter_changed(self, _event=None) -> None:
        name = self.reporter_name_var.get().strip()
        code = self.reporters_by_name.get(name)
        if code:
            self.reporter_code_info_var.set(f"Reporter code: {code}")
        else:
            self.reporter_code_info_var.set("Reporter code: unresolved")
        self._update_run_summary()

    def _on_classification_changed(self, _event=None) -> None:
        classification = self.classification_var.get().strip().upper()
        if classification == "HS":
            self.ag_combo.configure(values=HS_AG_LEVELS)
            if self.ag_level_var.get() not in HS_AG_LEVELS:
                self.ag_level_var.set("AG2")
        else:
            self.ag_combo.configure(values=SITC_AG_LEVELS)
            if self.ag_level_var.get() not in SITC_AG_LEVELS:
                self.ag_level_var.set("AG1")
        self.selected_codes.clear()
        self._refresh_commodity_catalog()
        self._update_run_summary()

    def _on_ag_level_changed(self, _event=None) -> None:
        self.selected_codes.clear()
        self._refresh_commodity_catalog()
        self._update_run_summary()

    def _load_or_default_config(self) -> None:
        config = DEFAULT_CONFIG
        if CONFIG_PATH.exists():
            try:
                config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception as exc:
                messagebox.showwarning("Config warning", f"Could not read config: {exc}")

        reporter_code = str(config.get("reporter_code", "")).strip()
        reporter_name = str(config.get("reporter_name", "")).strip()
        if not reporter_name and reporter_code in self.name_by_reporter_code:
            reporter_name = self.name_by_reporter_code[reporter_code]

        self.reporter_name_var.set(reporter_name)
        self._on_reporter_changed()

        years = [int(y) for y in config.get("years", []) if str(y).strip()]
        if years:
            self.start_year_var.set(str(min(years)))
            self.end_year_var.set(str(max(years)))
        else:
            self.start_year_var.set("2009")
            self.end_year_var.set("2010")

        classification = str(config.get("classification", "HS")).strip().upper()
        classification_ui = "SITC" if classification == "S4" else classification
        self.classification_var.set(classification_ui)
        self._on_classification_changed()

        commodity_codes = [str(c).strip() for c in config.get("commodity_codes", []) if str(c).strip()]
        inferred_ag = self._infer_ag_level(classification_ui, commodity_codes)
        if inferred_ag:
            self.ag_level_var.set(inferred_ag)
            self._refresh_commodity_catalog()

        self.frequency_var.set(str(config.get("frequency", "A")))
        self.partner_code_var.set(str(config.get("partner_code", "all")))
        self.batch_size_var.set(str(config.get("max_codes_per_batch", 20)))

        flows = {str(f).strip().lower() for f in config.get("flows", [])}
        self.flow_import_var.set("import" in flows)
        self.flow_export_var.set("export" in flows)

        self.selected_codes = set(commodity_codes)
        self.show_selected_only = False
        self.show_selected_btn_var.set("Show selected")
        self.search_var.set("")
        self._refresh_commodity_view()
        self._update_run_summary()

    def _on_summary_trigger(self, *_args) -> None:
        self._update_run_summary()

    def _infer_ag_level(self, classification: str, codes: list[str]) -> str:
        if not codes:
            return ""
        lengths = {len(c) for c in codes if c.isdigit()}
        if len(lengths) != 1:
            return ""
        length = next(iter(lengths))
        if classification == "HS":
            return {2: "AG2", 4: "AG4", 6: "AG6"}.get(length, "")
        return {1: "AG1", 2: "AG2", 4: "AG4"}.get(length, "")

    def _collect_config(self) -> dict:
        start_year = int(self.start_year_var.get().strip())
        end_year = int(self.end_year_var.get().strip())
        if start_year > end_year:
            raise ValueError("Start year cannot be greater than end year.")

        years = list(range(start_year, end_year + 1))

        flows = []
        if self.flow_import_var.get():
            flows.append("import")
        if self.flow_export_var.get():
            flows.append("export")
        if not flows:
            raise ValueError("At least one flow must be selected.")

        reporter_name = self.reporter_name_var.get().strip()
        reporter_code = self.reporters_by_name.get(reporter_name)
        if not reporter_code:
            raise ValueError(
                "Reporter name is not resolved to a reporter code. "
                "Choose a valid reporter name from metadata."
            )

        classification_ui = self.classification_var.get().strip().upper()
        classification = "S4" if classification_ui == "SITC" else classification_ui

        commodity_codes = sorted(self.selected_codes)
        if not commodity_codes:
            raise ValueError("Select at least one commodity from the commodity selector.")

        config = {
            "reporter_code": reporter_code,
            "reporter_name": reporter_name,
            "years": years,
            "classification": classification,
            "frequency": self.frequency_var.get().strip(),
            "flows": flows,
            "partner_code": self.partner_code_var.get().strip(),
            "commodity_codes": commodity_codes,
            "max_codes_per_batch": int(self.batch_size_var.get().strip()),
        }
        return config

    def _save_config(self) -> bool:
        try:
            config = self._collect_config()
        except Exception as exc:
            messagebox.showerror("Validation error", str(exc))
            return False

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self._append_log(f"Saved config: {CONFIG_PATH}\n")
        return True

    def _run_builder(self) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showinfo("Run active", "A builder run is already in progress.")
            return

        if not self._save_config():
            return

        python_exe = VENV_PYTHON if VENV_PYTHON.exists() else Path("python3")
        cmd = [str(python_exe), str(BUILDER_PATH)]

        self._append_log("\n=== Starting builder run ===\n")
        self._append_log("Command: " + " ".join(cmd) + "\n")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            messagebox.showerror("Run failed", f"Could not start builder: {exc}")
            return

        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _read_process_output(self) -> None:
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            self.log_queue.put(line)

        return_code = self.process.wait()
        self.log_queue.put(f"=== Builder finished with exit code {return_code} ===\n")

    def _stop_builder(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._append_log("Requested stop for running builder process.\n")
        else:
            self._append_log("No active builder run to stop.\n")

    def _drain_log_queue(self) -> None:
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(msg)
        self.after(120, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)

    def _refresh_commodity_catalog(self) -> None:
        classification = self.classification_var.get().strip().upper()
        ag_level = self.ag_level_var.get().strip().upper()

        if classification == "HS":
            rows = self._load_metadata_payload(["HS.json", "HS_2017.json", "HS_2012.json"])
            ag_target = {"AG2": 2, "AG4": 4, "AG6": 6}.get(ag_level, 2)
            catalog = []
            for row in rows:
                code = str(row.get("id") or "").strip()
                text = str(row.get("text") or "").strip()
                ag = row.get("aggrLevel", row.get("aggrlevel"))
                try:
                    ag_int = int(ag)
                except Exception:
                    ag_int = None
                if not code.isdigit() or ag_int != ag_target or len(code) != ag_target:
                    continue
                catalog.append({"code": code, "text": text})
            self.commodity_catalog = sorted(catalog, key=lambda x: x["code"])

        else:
            rows = self._load_metadata_payload(["classificationS4.json"])
            target_len = {"AG1": 1, "AG2": 2, "AG4": 4}.get(ag_level, 1)
            catalog = []
            for row in rows:
                code = str(row.get("id") or "").strip()
                text = str(row.get("text") or "").strip()
                if not code.isdigit() or len(code) != target_len:
                    continue
                catalog.append({"code": code, "text": text})
            self.commodity_catalog = sorted(catalog, key=lambda x: x["code"])

        self._refresh_commodity_view()

    def _refresh_commodity_view(self) -> None:
        query = self.search_var.get().strip().lower()
        self.commodity_listbox.delete(0, tk.END)
        self.visible_codes = []

        base_rows = (
            [row for row in self.commodity_catalog if row["code"] in self.selected_codes]
            if self.show_selected_only
            else list(self.commodity_catalog)
        )

        if query:
            self.filtered_commodities = [
                row
                for row in base_rows
                if query in row["code"].lower() or query in row["text"].lower()
            ]
        else:
            self.filtered_commodities = base_rows

        for row in self.filtered_commodities:
            code = row["code"]
            text = row["text"]
            display = f"{code} | {text}"
            idx = self.commodity_listbox.size()
            self.commodity_listbox.insert(tk.END, display)
            self.visible_codes.append(code)
            if code in self.selected_codes:
                self.commodity_listbox.selection_set(idx)

        self._update_selected_count()

    def _on_search_changed(self, *_args) -> None:
        self._refresh_commodity_view()

    def _on_commodity_select(self, _event=None) -> None:
        selected_indices = set(self.commodity_listbox.curselection())

        for code in self.visible_codes:
            if code in self.selected_codes:
                self.selected_codes.remove(code)

        for idx in selected_indices:
            if 0 <= idx < len(self.visible_codes):
                self.selected_codes.add(self.visible_codes[idx])

        self._update_selected_count()

    def _toggle_show_selected(self) -> None:
        self.show_selected_only = not self.show_selected_only
        self.show_selected_btn_var.set("Show all" if self.show_selected_only else "Show selected")
        self._refresh_commodity_view()

    def _clear_selected(self) -> None:
        self.selected_codes.clear()
        self.show_selected_only = False
        self.show_selected_btn_var.set("Show selected")
        self._refresh_commodity_view()

    def _update_selected_count(self) -> None:
        self.selected_count_var.set(f"Selected commodities: {len(self.selected_codes)}")
        self._update_run_summary()

    def _update_run_summary(self) -> None:
        classification = self.classification_var.get().strip().upper() or "HS"
        ag_level = self.ag_level_var.get().strip().upper() or "AG2"
        start_year = self.start_year_var.get().strip() or "?"
        end_year = self.end_year_var.get().strip() or "?"
        flow_count = int(bool(self.flow_import_var.get())) + int(bool(self.flow_export_var.get()))
        flows_label = "no flow" if flow_count == 0 else f"{flow_count} flow(s)"
        commodity_count = len(self.selected_codes)
        self.run_summary_var.set(
            f"Ready: {classification} {ag_level} | {commodity_count} commodities selected | "
            f"Years {start_year}-{end_year} | {flows_label}"
        )


if __name__ == "__main__":
    app = ComtradeGui()
    app.mainloop()
