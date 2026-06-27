#!/usr/bin/env python3
"""
Wifite Desktop Launcher - GUI for wifite2 with powerful Crack-Only mode

- Crack Only tab: Browse any handshake directory (no monitor mode, no root required for cracking)
  Select previous .cap / .22000 files, pick wordlist, choose tool (hashcat/aircrack), crack with live output.
- Full Wifite tab: Configure common options and launch wifite in a terminal.

Designed to match the style/quality of other tools in ~/bin (Deauther etc).

LEGAL: Only use on networks you own or have explicit written authorization to test.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import re
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Try to import wifite internals for smarter handshake parsing (optional)
HAS_WIFITE = False
try:
    from wifite.model.handshake import Handshake as WifiteHandshake
    from wifite.config import Configuration as WifiteConfig
    HAS_WIFITE = True
except Exception:
    pass

APP_NAME = "Wifite Launcher"
VERSION = "1.0"

# Common handshake directories to auto-scan
COMMON_HS_DIRS = [
    Path.home() / "hs",
    Path("/root/hs"),
    Path.cwd() / "hs",
]
sudo_user = os.getenv("SUDO_USER")
if sudo_user:
    COMMON_HS_DIRS.append(Path("/home") / sudo_user / "hs")

# Known good wordlist locations on Kali / common distros (in preference order)
COMMON_WORDLISTS = [
    "/usr/share/wordlists/rockyou.txt",
    "/usr/share/wordlists/rockyou.txt.gz",
    "/usr/share/dict/wordlist-probable.txt",
    "/usr/share/wordlists/fasttrack.txt",
    "/usr/share/wordlists/wifite.txt",
    "/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt",
    "/usr/share/fern-wifi/common.txt",
]

CRACKED_FILE = "cracked.json"  # wifite convention (saved in cwd of launcher or user chosen)

# No protection integration anymore (user wants all cards treated equally for monitor mode).


class WifiteLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1100x780")
        self.minsize(980, 680)

        # State
        self.handshakes: List[Dict] = []  # each: {path, essid, bssid, type, date, filename}
        self.selected_paths: set = set()
        self.wordlist_path: Optional[str] = None
        self.hs_dir: Optional[str] = None
        self.cracking_thread: Optional[threading.Thread] = None
        self.stop_cracking = threading.Event()

        pass  # no special iface forcing

        # Shared UI vars
        self.hs_dir_var = tk.StringVar()
        self.wordlist_var = tk.StringVar()
        self.crack_tool_var = tk.StringVar(value="hashcat")  # hashcat | aircrack

        self._build_ui()
        self._discover_wordlists()
        self._auto_scan_handshakes()

        # Final niceties
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._log("Ready. Select handshakes in the Crack Only tab or configure a full attack.\n")

    # ---------------- UI CONSTRUCTION ----------------

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        title = ttk.Label(top, text=f"📡 {APP_NAME}", font=("TkDefaultFont", 16, "bold"))
        title.pack(side=tk.LEFT)

        ver = ttk.Label(top, text=f"v{VERSION}  •  wifite2 wrapper + offline cracker", foreground="#666")
        ver.pack(side=tk.LEFT, padx=12)

        # Legal warning (always visible)
        warn = ttk.Label(top, text="⚠️ Authorized testing only", foreground="#b00", font=("TkDefaultFont", 9))
        warn.pack(side=tk.RIGHT)

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.tab_crack = ttk.Frame(self.notebook, padding=6)
        self.tab_full = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.tab_crack, text=" Crack Handshakes Only (Offline) ")
        self.notebook.add(self.tab_full, text=" Full Wifite Attack (Monitor Mode) ")

        self._build_crack_tab()
        self._build_full_tab()

        # Bottom status + quick actions bar
        bottom = ttk.Frame(self, padding=(8, 4))
        bottom.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(bottom, textvariable=self.status_var, relief=tk.SUNKEN, padding=4).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(bottom, text="Open hs/ Folder", command=self._open_hs_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="View Cracked", command=self._show_cracked_popup).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Check .cap File...", command=self._check_cap_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Legal / About", command=self._show_legal).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Quit", command=self._on_close).pack(side=tk.RIGHT)

        # Output log (global, below tabs)
        log_frame = ttk.LabelFrame(self, text=" Activity Log ", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=9, wrap=tk.WORD, font=("monospace", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

    def _build_crack_tab(self):
        tab = self.tab_crack

        # === HANDSHAKE DIRECTORY ===
        dir_frame = ttk.LabelFrame(tab, text="Handshake Directory (contains *.cap and *.22000 files)", padding=8)
        dir_frame.pack(fill=tk.X, pady=(0, 6))

        row = ttk.Frame(dir_frame)
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=self.hs_dir_var, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="Browse...", command=self._browse_hs_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Scan Common", command=self._auto_scan_handshakes).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Refresh", command=self._refresh_handshakes).pack(side=tk.LEFT, padx=2)

        hint = ttk.Label(dir_frame, text="wifite default is ./hs — also scans ~/hs and /root/hs automatically on start", foreground="#555")
        hint.pack(anchor="w", pady=(4, 0))

        # === HANDSHAKE LIST ===
        list_frame = ttk.LabelFrame(tab, text="Captured Handshakes (select one or more)", padding=6)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        cols = ("essid", "bssid", "type", "date", "file")
        self.hs_tree = ttk.Treeview(list_frame, columns=cols, show="tree headings", selectmode="extended")
        self.hs_tree.heading("#0", text="✓")
        self.hs_tree.column("#0", width=30, stretch=False, anchor="center")
        self.hs_tree.heading("essid", text="ESSID")
        self.hs_tree.column("essid", width=220, minwidth=160)
        self.hs_tree.heading("bssid", text="BSSID")
        self.hs_tree.column("bssid", width=140, minwidth=120)
        self.hs_tree.heading("type", text="Type")
        self.hs_tree.column("type", width=80, minwidth=70, anchor="center")
        self.hs_tree.heading("date", text="Captured")
        self.hs_tree.column("date", width=160, minwidth=130)
        self.hs_tree.heading("file", text="Filename")
        self.hs_tree.column("file", width=260, minwidth=180)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.hs_tree.yview)
        self.hs_tree.configure(yscrollcommand=vsb.set)
        self.hs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.hs_tree.bind("<<TreeviewSelect>>", self._on_hs_selection_changed)
        self.hs_tree.bind("<Button-1>", self._on_hs_click, add="+")  # for checkbox toggle simulation

        # Selection helper buttons
        sel_row = ttk.Frame(list_frame)
        sel_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(sel_row, text="Select All", command=lambda: self._select_all(True)).pack(side=tk.LEFT)
        ttk.Button(sel_row, text="Select None", command=lambda: self._select_all(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(sel_row, text="Uncracked Only", command=self._select_uncracked).pack(side=tk.LEFT, padx=4)
        ttk.Button(sel_row, text="Invert", command=self._invert_selection).pack(side=tk.LEFT, padx=4)
        self.sel_label = ttk.Label(sel_row, text="0 selected")
        self.sel_label.pack(side=tk.RIGHT, padx=8)

        # === WORDLIST + TOOL + ACTIONS ===
        opts = ttk.Frame(tab)
        opts.pack(fill=tk.X, pady=4)

        # Wordlist
        wl_frame = ttk.LabelFrame(opts, text="Wordlist", padding=6)
        wl_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.wordlist_combo = ttk.Combobox(wl_frame, textvariable=self.wordlist_var, width=48, state="readonly")
        self.wordlist_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(wl_frame, text="Browse...", command=self._browse_wordlist).pack(side=tk.LEFT, padx=2)
        ttk.Button(wl_frame, text="Extract rockyou", command=self._ensure_rockyou).pack(side=tk.LEFT, padx=2)

        # Tool
        tool_frame = ttk.LabelFrame(opts, text="Cracking Tool", padding=6)
        tool_frame.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Radiobutton(tool_frame, text="hashcat (fast, GPU/CPU, best for PMKID)", variable=self.crack_tool_var, value="hashcat").pack(anchor="w")
        ttk.Radiobutton(tool_frame, text="aircrack-ng (CPU, works great on .cap handshakes)", variable=self.crack_tool_var, value="aircrack").pack(anchor="w")

        note = ttk.Label(tool_frame, text="Note: PMKID (*.22000) requires hashcat", foreground="#a60", font=("TkDefaultFont", 8))
        note.pack(anchor="w", pady=(2, 0))

        # Action buttons
        act = ttk.Frame(tab)
        act.pack(fill=tk.X, pady=6)

        self.start_btn = ttk.Button(act, text="▶ Start Cracking Selected", command=self._start_cracking, style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, ipady=6, ipadx=16)

        self.stop_btn = ttk.Button(act, text="■ Stop", command=self._stop_cracking, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=8, ipady=6)

        ttk.Button(act, text="Open Selected in File Manager", command=self._open_selected_hs).pack(side=tk.LEFT, padx=4)

        # Live cracking status area (per-run)
        self.crack_status = ttk.Label(tab, text="", font=("TkDefaultFont", 10, "bold"), foreground="#006")
        self.crack_status.pack(fill=tk.X, pady=(2, 4))

    def _build_full_tab(self):
        tab = self.tab_full

        info = ttk.Label(tab, text="Pre-configure options then launch wifite in a real terminal (recommended for interactive scanning/attacking).",
                         foreground="#444", wraplength=900, justify="left")
        info.pack(anchor="w", pady=(0, 8))

        # Shared settings row
        shared = ttk.Frame(tab)
        shared.pack(fill=tk.X, pady=4)

        ttk.Label(shared, text="Wordlist:").pack(side=tk.LEFT)
        ttk.Entry(shared, textvariable=self.wordlist_var, width=55).pack(side=tk.LEFT, padx=4)
        ttk.Button(shared, text="Browse", command=self._browse_wordlist).pack(side=tk.LEFT)

        ttk.Label(shared, text="   hs-dir:").pack(side=tk.LEFT, padx=(12, 0))
        ttk.Entry(shared, textvariable=self.hs_dir_var, width=28).pack(side=tk.LEFT, padx=4)
        ttk.Button(shared, text="Browse", command=self._browse_hs_dir).pack(side=tk.LEFT)

        # Flags
        flags = ttk.LabelFrame(tab, text="Common Options", padding=8)
        flags.pack(fill=tk.X, pady=6)

        self.flag_vars = {}
        flags_grid = ttk.Frame(flags)
        flags_grid.pack()

        flag_defs = [
            ("kill", "--kill", "Kill conflicting processes"),
            ("random_mac", "--random-mac", "Randomize MAC address"),
            ("ignore_cracked", "--ignore-cracked", "Hide previously cracked targets"),
            ("no_deauth", "--nodeauths", "Passive (no deauth)"),
            ("clients_only", "--clients-only", "Only targets with clients"),
            ("pmkid_only", "--pmkid", "PMKID capture only"),
            ("no_pmkid", "--no-pmkid", "Disable PMKID capture"),
            ("wps_only", "--wps-only", "WPS PIN/Pixie only"),
            ("wpa3", "--wpa3", "WPA3 networks only"),
        ]

        for i, (key, flag, label) in enumerate(flag_defs):
            var = tk.BooleanVar()
            self.flag_vars[key] = var
            ttk.Checkbutton(flags_grid, text=f"{flag}  ({label})", variable=var).grid(row=i//3, column=i%3, sticky="w", padx=8, pady=2)

        # Target / behavior
        tgt = ttk.LabelFrame(tab, text="Target / Behavior", padding=8)
        tgt.pack(fill=tk.X, pady=6)

        row1 = ttk.Frame(tgt)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Specific ESSID (contains):").pack(side=tk.LEFT)
        self.essid_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.essid_var, width=30).pack(side=tk.LEFT, padx=4)

        ttk.Label(row1, text="   BSSID:").pack(side=tk.LEFT)
        self.bssid_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.bssid_var, width=20).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(tgt)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Channel(s):").pack(side=tk.LEFT)
        self.channel_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.channel_var, width=12).pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text="(e.g. 1,6,11 or 36-48)").pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="   Pillage after (sec):").pack(side=tk.LEFT, padx=(16, 0))
        self.pillage_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.pillage_var, width=6).pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text="(0 = manual)").pack(side=tk.LEFT)

        # Command preview
        prev_frame = ttk.LabelFrame(tab, text="Command Preview", padding=6)
        prev_frame.pack(fill=tk.X, pady=6)

        self.cmd_preview = scrolledtext.ScrolledText(prev_frame, height=3, font=("monospace", 9), wrap=tk.WORD)
        self.cmd_preview.pack(fill=tk.X)
        self.cmd_preview.configure(state=tk.DISABLED)

        # Update preview when vars change
        for v in [self.wordlist_var, self.hs_dir_var, self.essid_var, self.bssid_var, self.channel_var, self.pillage_var]:
            v.trace_add("write", lambda *_: self._update_cmd_preview())
        for var in self.flag_vars.values():
            var.trace_add("write", lambda *_: self._update_cmd_preview())

        # Launch buttons
        launch = ttk.Frame(tab)
        launch.pack(fill=tk.X, pady=10)

        ttk.Button(launch, text="🖥️  Launch in Terminal (recommended)", command=self._launch_full_in_terminal,
                   style="Accent.TButton").pack(side=tk.LEFT, ipady=8, ipadx=20)
        ttk.Button(launch, text="Copy Command", command=self._copy_cmd).pack(side=tk.LEFT, padx=8, ipady=8)
        ttk.Button(launch, text="Quick: WPA2 + PMKID + rockyou", command=self._quick_preset_wpa2).pack(side=tk.LEFT, padx=8)

    # ---------------- HELPERS / DISCOVERY ----------------

    def _log(self, msg: str):
        self.log_text.configure(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _discover_wordlists(self):
        found = []
        seen = set()

        # Add any already in wifite config if we can import it
        if HAS_WIFITE:
            try:
                WifiteConfig.initialize(load_interface=False)
                if WifiteConfig.wordlist and os.path.exists(WifiteConfig.wordlist):
                    p = str(Path(WifiteConfig.wordlist).resolve())
                    if p not in seen:
                        found.append(p)
                        seen.add(p)
            except Exception:
                pass

        for p in COMMON_WORDLISTS:
            if os.path.exists(p) and p not in seen:
                found.append(p)
                seen.add(p)

        # Also scan a few more common places
        extra = list(Path("/usr/share/wordlists").glob("*.txt")) if Path("/usr/share/wordlists").exists() else []
        for p in extra:
            if p not in seen and p.stat().st_size > 10000:
                found.append(str(p))
                seen.add(str(p))

        # Put rockyou first if present (even gz)
        rockyou = [f for f in found if "rockyou" in f]
        others = [f for f in found if "rockyou" not in f]
        self.discovered_wordlists = rockyou + others

        self.wordlist_combo["values"] = self.discovered_wordlists
        if self.discovered_wordlists:
            self.wordlist_var.set(self.discovered_wordlists[0])
            self.wordlist_path = self.discovered_wordlists[0]

    def _browse_wordlist(self):
        path = filedialog.askopenfilename(title="Choose wordlist", filetypes=[("Text files", "*.txt *.lst *.gz"), ("All", "*.*")])
        if path:
            self.wordlist_var.set(path)
            self.wordlist_path = path
            if path not in self.discovered_wordlists:
                self.discovered_wordlists.insert(0, path)
                self.wordlist_combo["values"] = self.discovered_wordlists

    def _ensure_rockyou(self):
        """Extract rockyou.txt.gz to /tmp/rockyou.txt if needed"""
        gz = "/usr/share/wordlists/rockyou.txt.gz"
        out = "/tmp/rockyou.txt"
        if os.path.exists(out) and os.path.getsize(out) > 1000000:
            self.wordlist_var.set(out)
            self.wordlist_path = out
            self._log(f"Using already extracted rockyou: {out}")
            return

        if not os.path.exists(gz):
            messagebox.showwarning("Not found", "rockyou.txt.gz not found at /usr/share/wordlists/")
            return

        self._set_status("Extracting rockyou.txt.gz ... (this can take a moment)")
        try:
            subprocess.check_call(["gunzip", "-c", gz], stdout=open(out, "wb"))
            self.wordlist_var.set(out)
            self.wordlist_path = out
            self._log(f"Extracted rockyou to {out} ({os.path.getsize(out) // 1024 // 1024} MB)")
        except Exception as e:
            messagebox.showerror("Failed", f"Could not extract:\n{e}")
        finally:
            self._set_status("Idle")

    def _auto_scan_handshakes(self):
        candidates = [p for p in COMMON_HS_DIRS if p]
        # Add current hs_dir if set
        if self.hs_dir_var.get():
            candidates.insert(0, Path(self.hs_dir_var.get()))

        # Also try ./hs relative to wherever user might have run wifite
        candidates.append(Path.cwd() / "hs")

        found_any = False
        for d in candidates:
            if d and d.exists() and d.is_dir():
                self.hs_dir_var.set(str(d))
                self.hs_dir = str(d)
                self._scan_handshakes_dir(d)
                found_any = True
                break

        if not found_any:
            self._log("No handshake directories found automatically. Use Browse or 'Scan Common'.")
            self.handshakes = []
            self._refresh_tree()

    def _browse_hs_dir(self):
        path = filedialog.askdirectory(title="Select handshake directory (hs/)")
        if path:
            self.hs_dir_var.set(path)
            self.hs_dir = path
            self._scan_handshakes_dir(Path(path))

    def _refresh_handshakes(self):
        d = self.hs_dir_var.get()
        if d and Path(d).exists():
            self._scan_handshakes_dir(Path(d))
        else:
            self._auto_scan_handshakes()

    def _scan_handshakes_dir(self, directory: Path):
        self.handshakes = []
        self.selected_paths.clear()

        if not directory.exists():
            self._log(f"Directory does not exist: {directory}")
            self._refresh_tree()
            return

        try:
            for f in sorted(directory.iterdir()):
                if not f.is_file():
                    continue
                name = f.name
                if name.count("_") < 2:
                    continue

                ext = f.suffix.lower()
                if ext not in (".cap", ".22000"):
                    continue

                # Try wifite naming convention first: <prefix>_<essid>_<bssid-dashed>_<date>.<ext>
                essid = "?"
                bssid = "?"
                date = "?"
                hs_type = "4-WAY" if ext == ".cap" else "PMKID"

                parts = name.rsplit(".", 1)[0].split("_")
                if len(parts) >= 4:
                    # Last three before ext are usually essid, bssid, datetime? Wait wifite is name_essid_bssid_date
                    # Actually from source: name, essid, bssid, date = hs_file.split('_')  -- 4 parts total before ext
                    try:
                        if len(parts) == 4:
                            _prefix, essid, bssid_d, date_raw = parts
                        else:
                            essid = parts[1]
                            bssid_d = parts[2]
                            date_raw = parts[3] if len(parts) > 3 else "?"

                        bssid = bssid_d.replace("-", ":")
                        # date like 20250412T18-22-03
                        if "T" in date_raw:
                            dpart, tpart = date_raw.split("T", 1)
                            tpart = tpart.replace("-", ":")
                            date = f"{dpart} {tpart}"
                        else:
                            date = date_raw
                    except Exception:
                        pass

                # Fallback / enhancement: use wifite Handshake parser if available
                if HAS_WIFITE and ext == ".cap":
                    try:
                        h = WifiteHandshake(str(f))
                        h.divine_bssid_and_essid()
                        if h.essid:
                            essid = h.essid
                        if h.bssid:
                            bssid = h.bssid
                    except Exception:
                        pass

                self.handshakes.append({
                    "path": str(f),
                    "filename": name,
                    "essid": essid,
                    "bssid": bssid,
                    "type": hs_type,
                    "date": date,
                })

            self._log(f"Found {len(self.handshakes)} handshake(s) in {directory}")
        except Exception as e:
            self._log(f"Error scanning {directory}: {e}")

        self._refresh_tree()

    def _refresh_tree(self):
        for iid in self.hs_tree.get_children():
            self.hs_tree.delete(iid)

        for i, hs in enumerate(self.handshakes):
            checked = "☑" if hs["path"] in self.selected_paths else "☐"
            self.hs_tree.insert("", "end", iid=str(i), text=checked,
                                values=(hs["essid"], hs["bssid"], hs["type"], hs["date"], hs["filename"]))

        self._update_sel_label()

    def _on_hs_click(self, event):
        # Toggle checkbox on click in first column
        region = self.hs_tree.identify("region", event.x, event.y)
        if region == "tree":
            iid = self.hs_tree.identify_row(event.y)
            if iid:
                idx = int(iid)
                hs = self.handshakes[idx]
                p = hs["path"]
                if p in self.selected_paths:
                    self.selected_paths.remove(p)
                else:
                    self.selected_paths.add(p)
                self._refresh_tree()

    def _on_hs_selection_changed(self, _event=None):
        # Also support normal extended selection for convenience
        self._update_sel_label()

    def _update_sel_label(self):
        # Count both checkbox style + tree selection
        tree_sel = {self.handshakes[int(i)]["path"] for i in self.hs_tree.selection()}
        total = len(self.selected_paths | tree_sel)
        self.sel_label.config(text=f"{total} selected")

    def _select_all(self, state: bool):
        if state:
            self.selected_paths = {h["path"] for h in self.handshakes}
        else:
            self.selected_paths.clear()
        self.hs_tree.selection_remove(self.hs_tree.selection())
        self._refresh_tree()

    def _select_uncracked(self):
        cracked = self._load_cracked_bssids()
        self.selected_paths = {h["path"] for h in self.handshakes if h["bssid"] not in cracked}
        self._refresh_tree()

    def _invert_selection(self):
        current = self.selected_paths.copy()
        self.selected_paths = {h["path"] for h in self.handshakes} - current
        self._refresh_tree()

    def _load_cracked_bssids(self) -> set:
        cracked = set()
        cf = Path(CRACKED_FILE)
        if cf.exists():
            try:
                data = json.loads(cf.read_text())
                for entry in data:
                    if entry.get("bssid"):
                        cracked.add(entry["bssid"])
            except Exception:
                pass
        return cracked

    # ---------------- CRACKING (the important part) ----------------

    def _get_effective_selected(self) -> List[Dict]:
        tree_sel = {self.handshakes[int(i)]["path"] for i in self.hs_tree.selection()}
        paths = self.selected_paths | tree_sel
        return [h for h in self.handshakes if h["path"] in paths]

    def _start_cracking(self):
        selected = self._get_effective_selected()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select one or more handshakes first (click the checkbox column or use normal selection).")
            return

        wl = self.wordlist_var.get().strip()
        if not wl or not os.path.exists(wl):
            # Try to resolve rockyou.gz transparently
            if "rockyou" in wl and wl.endswith(".gz"):
                self._ensure_rockyou()
                wl = self.wordlist_var.get()
            else:
                messagebox.showerror("Wordlist required", "Choose a valid wordlist first.")
                return

        # Decompress on the fly if gz (aircrack/hashcat don't like .gz)
        if wl.endswith(".gz"):
            tmp = f"/tmp/rockyou_from_gz_{int(time.time())}.txt"
            self._log(f"Decompressing {wl} -> {tmp} for cracking...")
            try:
                subprocess.check_call(["gunzip", "-c", wl], stdout=open(tmp, "wb"))
                wl = tmp
            except Exception as e:
                messagebox.showerror("Decompress failed", str(e))
                return

        tool = self.crack_tool_var.get()
        self.wordlist_path = wl

        self.stop_cracking.clear()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._set_status(f"Cracking {len(selected)} target(s) with {tool}...")

        self.cracking_thread = threading.Thread(target=self._crack_worker, args=(selected, wl, tool), daemon=True)
        self.cracking_thread.start()

    def _stop_cracking(self):
        self.stop_cracking.set()
        self._log("Stop requested. Waiting for current crack to finish...")

    def _crack_worker(self, targets: List[Dict], wordlist: str, tool: str):
        self._log(f"=== Starting batch crack of {len(targets)} handshake(s) using {tool} ===")
        self._log(f"Wordlist: {wordlist}")

        successes = []

        for idx, hs in enumerate(targets, 1):
            if self.stop_cracking.is_set():
                break

            path = hs["path"]
            essid = hs["essid"]
            bssid = hs["bssid"]
            hs_type = hs["type"]

            self.crack_status.config(text=f"[{idx}/{len(targets)}] {essid} ({bssid}) — {tool}")
            self._log(f"\n>>> [{idx}/{len(targets)}] Cracking {hs_type} for {essid} / {bssid}")
            self._log(f"    File: {path}")

            key = None
            try:
                if tool == "hashcat":
                    key = self._crack_with_hashcat(path, bssid, essid, hs_type, wordlist)
                else:
                    if hs_type == "PMKID":
                        self._log("    aircrack-ng cannot crack PMKID hashes — skipping (use hashcat)")
                        continue
                    key = self._crack_with_aircrack(path, bssid, essid, wordlist)
            except Exception as e:
                self._log(f"    ERROR: {e}")

            if key:
                self._log(f"    ✓ SUCCESS! Key = {key}")
                successes.append((hs, key))
                self._save_cracked_result(hs, key)
            else:
                if not self.stop_cracking.is_set():
                    self._log("    ✗ Not found in wordlist (or tool failed)")

        # Finished
        self.crack_status.config(text="")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._set_status("Idle")

        if successes:
            self._log(f"\n=== Done. Cracked {len(successes)} / {len(targets)} ===")
            msg = "\n".join([f"{h['essid']} ({h['bssid']}): {k}" for h, k in successes])
            messagebox.showinfo("Cracking Complete", f"Found keys for:\n\n{msg}\n\nResults also saved to {CRACKED_FILE}")
        else:
            self._log("=== Batch complete. No keys recovered this run. ===")

    def _crack_with_aircrack(self, capfile: str, bssid: str, essid: str, wordlist: str) -> Optional[str]:
        key_file = f"/tmp/wifite_key_{os.getpid()}_{int(time.time())}.txt"
        cmd = [
            "aircrack-ng", "-a", "2", "-w", wordlist,
            "--bssid", bssid, "-l", key_file, capfile
        ]
        self._log("    $ " + " ".join(cmd))

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except FileNotFoundError:
            self._log("    aircrack-ng not found in PATH")
            return None

        key = None
        key_found_re = re.compile(r"KEY FOUND! \[ (.+) \]")
        percent_re = re.compile(r"(\d+)%\s+keys tested")

        for line in proc.stdout:
            if self.stop_cracking.is_set():
                proc.terminate()
                break
            line = line.strip()
            if not line:
                continue
            # Only show interesting lines
            if any(x in line for x in ("KEY FOUND", "%", "tested", "Passphrase", "Current")):
                self._log("    " + line[:180])

            m = key_found_re.search(line)
            if m:
                key = m.group(1).strip()
            elif "KEY FOUND" in line and not key:
                # fallback
                if "[" in line and "]" in line:
                    key = line.split("[", 1)[1].split("]", 1)[0].strip()

            if percent_re.search(line):
                # live update status
                self.crack_status.config(text=f"aircrack: {essid} — {line[:60]}")

        proc.wait()
        if os.path.exists(key_file):
            try:
                key = Path(key_file).read_text().strip() or key
            except Exception:
                pass
            try:
                os.unlink(key_file)
            except Exception:
                pass
        return key

    def _crack_with_hashcat(self, cap_or_22000: str, bssid: str, essid: str, hs_type: str, wordlist: str) -> Optional[str]:
        # Convert .cap to .22000 if needed
        hash_file = cap_or_22000
        tmp_hash = None

        if cap_or_22000.lower().endswith(".cap"):
            tmp_hash = f"/tmp/hc_{os.getpid()}_{int(time.time())}.22000"
            conv = ["hcxpcapngtool", "-o", tmp_hash, cap_or_22000]
            self._log("    $ " + " ".join(conv))
            try:
                res = subprocess.run(conv, capture_output=True, text=True, timeout=120)
                if res.returncode != 0 or not os.path.exists(tmp_hash) or os.path.getsize(tmp_hash) == 0:
                    self._log(f"    hcxpcapngtool conversion failed or produced empty file. stderr: {res.stderr[:300]}")
                    return None
                hash_file = tmp_hash
                self._log(f"    Converted to {tmp_hash}")
            except Exception as e:
                self._log(f"    Conversion error: {e}")
                return None

        # Now run hashcat -m 22000
        cmd = [
            "hashcat",
            "-m", "22000",
            "-a", "0",
            hash_file,
            wordlist,
            "--quiet",
            "-w", "3",
            "--status",
            "--status-timer", "10"
        ]
        self._log("    $ " + " ".join(cmd))

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except FileNotFoundError:
            self._log("    hashcat not found in PATH")
            if tmp_hash and os.path.exists(tmp_hash):
                os.unlink(tmp_hash)
            return None

        key = None
        # hashcat --quiet with status will eventually print the password on success
        for line in proc.stdout:
            if self.stop_cracking.is_set():
                proc.terminate()
                break
            line = line.strip()
            if not line:
                continue
            self._log("    " + line[:200])

            # Successful recovery line looks like:  22000:xxxxxxxx:....:password
            # Or when using --show later. For now we watch for a line that has the hash and a plaintext at end.
            if ":" in line and not line.startswith("Status"):
                # Very rough but effective: last field after last : that doesn't look like hex
                parts = line.split(":")
                candidate = parts[-1].strip()
                if candidate and len(candidate) > 2 and not all(c in "0123456789abcdefABCDEF" for c in candidate):
                    key = candidate

            if "Cracked" in line or "Recovered" in line:
                self.crack_status.config(text=f"hashcat: {essid} — {line[:70]}")

        proc.wait()

        if tmp_hash and os.path.exists(tmp_hash):
            try:
                os.unlink(tmp_hash)
            except Exception:
                pass

        # Fallback: ask hashcat to show any cracked result for this hash file
        if not key:
            try:
                show = subprocess.run(["hashcat", "-m", "22000", hash_file, "--show", "--quiet"],
                                      capture_output=True, text=True, timeout=30)
                for l in show.stdout.splitlines():
                    if ":" in l:
                        cand = l.split(":")[-1].strip()
                        if cand:
                            key = cand
                            break
            except Exception:
                pass

        return key

    def _save_cracked_result(self, hs: Dict, key: str):
        """Append a wifite-compatible entry to cracked.json"""
        entry = {
            "type": "WPA" if hs["type"] == "4-WAY" else "PMKID",
            "date": int(time.time()),
            "essid": hs["essid"],
            "bssid": hs["bssid"],
            "key": key,
            "handshake_file": hs["path"] if hs["type"] == "4-WAY" else None,
            "pmkid_file": hs["path"] if hs["type"] == "PMKID" else None,
        }
        try:
            data = []
            if os.path.exists(CRACKED_FILE):
                data = json.loads(Path(CRACKED_FILE).read_text())
            # avoid exact duplicates
            data = [d for d in data if not (d.get("bssid") == hs["bssid"] and d.get("key") == key)]
            data.append(entry)
            Path(CRACKED_FILE).write_text(json.dumps(data, indent=2))
            self._log(f"    Saved result to {CRACKED_FILE}")
        except Exception as e:
            self._log(f"    Warning: could not update cracked.json: {e}")

    # ---------------- FULL WIFITE LAUNCH ----------------

    def _update_cmd_preview(self):
        cmd = self._build_wifite_cmd()
        self.cmd_preview.configure(state=tk.NORMAL)
        self.cmd_preview.delete("1.0", tk.END)
        self.cmd_preview.insert("1.0", " ".join(cmd))
        self.cmd_preview.configure(state=tk.DISABLED)

    def _build_wifite_cmd(self) -> List[str]:
        cmd = ["wifite"]

        wl = self.wordlist_var.get().strip()
        if wl and os.path.exists(wl):
            cmd += ["--dict", wl]

        hs = self.hs_dir_var.get().strip()
        if hs:
            cmd += ["--hs-dir", hs]

        if self.essid_var.get().strip():
            cmd += ["-e", self.essid_var.get().strip()]
        if self.bssid_var.get().strip():
            cmd += ["-b", self.bssid_var.get().strip()]
        if self.channel_var.get().strip():
            cmd += ["-c", self.channel_var.get().strip()]
        if self.pillage_var.get().strip() and self.pillage_var.get() != "0":
            cmd += ["-p", self.pillage_var.get().strip()]

        flag_map = {
            "kill": "--kill",
            "random_mac": "--random-mac",
            "ignore_cracked": "--ignore-cracked",
            "no_deauth": "--nodeauths",
            "clients_only": "--clients-only",
            "pmkid_only": "--pmkid",
            "no_pmkid": "--no-pmkid",
            "wps_only": "--wps-only",
            "wpa3": "--wpa3",
        }
        for key, flag in flag_map.items():
            if self.flag_vars.get(key) and self.flag_vars[key].get():
                cmd.append(flag)

        return cmd

    def _launch_full_in_terminal(self):
        cmd = self._build_wifite_cmd()
        # We want a clean terminal running the command (as root via pkexec if needed)
        term_cmd = self._find_terminal_command(cmd)

        if not term_cmd:
            messagebox.showerror("No terminal", "Could not find a terminal emulator.\nInstall xfce4-terminal, gnome-terminal, konsole, or xterm.")
            return

        self._log("Launching: " + " ".join(cmd))
        try:
            subprocess.Popen(term_cmd)
            self._log("Terminal launched. You can close this window.")
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))

    def _find_terminal_command(self, wifite_args: List[str]) -> Optional[List[str]]:
        """Return a command list that will open a terminal and run the wifite command (with pkexec if not root)."""
        full_cmd = " ".join(wifite_args)

        # If not root we wrap with pkexec + env for X
        if os.geteuid() != 0:
            # The env dance is already handled by our launch.sh normally, but here we are inside the already-root GUI
            # So just run wifite directly (we are root)
            pass

        candidates = [
            ["xfce4-terminal", "--title=Wifite", "-x", "bash", "-c", f"{full_cmd}; echo; read -p 'Press enter to close...'"],
            ["gnome-terminal", "--", "bash", "-c", f"{full_cmd}; echo; read -p 'Press enter to close...'"],
            ["konsole", "-e", "bash", "-c", f"{full_cmd}; echo; read -p 'Press enter to close...'"],
            ["kitty", "-e", "bash", "-c", f"{full_cmd}; echo; read -p 'Press enter to close...'"],
            ["xterm", "-T", "Wifite", "-e", "bash", "-c", f"{full_cmd}; echo; read -p 'Press enter to close...'"],
        ]

        for c in candidates:
            if shutil.which(c[0]):
                return c
        return None

    def _copy_cmd(self):
        cmd = " ".join(self._build_wifite_cmd())
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self._log("Command copied to clipboard.")

    def _quick_preset_wpa2(self):
        self.wordlist_var.set("/usr/share/wordlists/rockyou.txt" if os.path.exists("/usr/share/wordlists/rockyou.txt") else "")
        self.flag_vars["kill"].set(True)
        self.flag_vars["ignore_cracked"].set(True)
        self.flag_vars["pmkid_only"].set(False)
        self._update_cmd_preview()
        self.notebook.select(self.tab_full)
        messagebox.showinfo("Preset loaded", "WPA2-friendly preset loaded. Adjust and launch in terminal.")

    # ---------------- EXTRAS ----------------

    def _open_hs_dir(self):
        d = self.hs_dir_var.get() or str(Path.cwd() / "hs")
        try:
            subprocess.Popen(["xdg-open", d])
        except Exception:
            messagebox.showinfo("Open", f"Open this folder manually:\n{d}")

    def _open_selected_hs(self):
        selected = self._get_effective_selected()
        if not selected:
            return
        # Open the directory of the first one
        d = os.path.dirname(selected[0]["path"])
        try:
            subprocess.Popen(["xdg-open", d])
        except Exception:
            pass

    def _show_cracked_popup(self):
        cf = Path(CRACKED_FILE)
        if not cf.exists():
            messagebox.showinfo("Cracked", f"No {CRACKED_FILE} found yet in current directory.")
            return
        try:
            data = json.loads(cf.read_text())
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        popup = tk.Toplevel(self)
        popup.title("Previously Cracked (from cracked.json)")
        popup.geometry("900x500")

        tree = ttk.Treeview(popup, columns=("date", "essid", "bssid", "type", "key"), show="headings")
        for col, w in [("date", 160), ("essid", 200), ("bssid", 140), ("type", 80), ("key", 280)]:
            tree.heading(col, text=col.upper())
            tree.column(col, width=w)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        for entry in sorted(data, key=lambda x: x.get("date", 0), reverse=True):
            dt = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("date", 0)))
            tree.insert("", "end", values=(dt, entry.get("essid", ""), entry.get("bssid", ""), entry.get("type", ""), entry.get("key", "")))

        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=4)

    def _check_cap_file(self):
        path = filedialog.askopenfilename(title="Select .cap or .22000 to check", filetypes=[("Capture/Hash", "*.cap *.22000"), ("All", "*.*")])
        if not path:
            return
        self._log(f"Running: wifite --check {path}")
        try:
            out = subprocess.check_output(["wifite", "--check", path], text=True, stderr=subprocess.STDOUT, timeout=60)
            self._log(out[:2000])
            messagebox.showinfo("wifite --check", out[:1500] or "No output")
        except subprocess.CalledProcessError as e:
            self._log(str(e.output)[:1500])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _show_legal(self):
        messagebox.showinfo(
            "Legal Notice",
            "This tool is for authorized security testing ONLY.\n\n"
            "You must have explicit permission from the owner of any network you test.\n\n"
            "Unauthorized access or interference with computer networks is illegal in most jurisdictions.\n\n"
            "By using this launcher you confirm you are acting legally and ethically."
        )

    def _on_close(self):
        if self.cracking_thread and self.cracking_thread.is_alive():
            if not messagebox.askyesno("Cracking in progress", "A cracking process is still running.\nReally quit?"):
                return
            self.stop_cracking.set()
        self.destroy()

    # ---------------- MAIN ENTRY ----------------

def main():
    # Make sure we have a writable cwd for cracked.json etc.
    os.chdir(Path.home())

    app = WifiteLauncher()
    # Some ttk themes look nicer
    try:
        app.tk.call("source", "/usr/share/tcltk/tk8.6/ttk/clam.tcl")  # or just let default
    except Exception:
        pass

    app.mainloop()


if __name__ == "__main__":
    main()
