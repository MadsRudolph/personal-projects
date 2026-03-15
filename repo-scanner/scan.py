"""
Repo Security Scanner — GitGuardian-style Desktop GUI
Scans full git history of public repos for exposed secrets.
"""

import json
import math
import os
import re
import subprocess
import tempfile
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from pathlib import Path
from dataclasses import dataclass, field

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Detectors ────────────────────────────────────────────────────────────────
DETECTORS: list[tuple[str, re.Pattern, str, str]] = [
    ("AWS Access Key ID",       re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"), "confirmed", "critical"),
    ("AWS Secret Access Key",   re.compile(r"(?i)(?:aws_secret_access_key|aws_secret)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"), "confirmed", "critical"),
    ("Google API Key",          re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "confirmed", "high"),
    ("GitHub Token",            re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"), "confirmed", "critical"),
    ("Slack Token",             re.compile(r"xox[bposa]-[0-9]{10,}-[A-Za-z0-9\-]+"), "confirmed", "critical"),
    ("OpenAI API Key",          re.compile(r"sk-[A-Za-z0-9]{20,}"), "likely", "critical"),
    ("Stripe Secret Key",       re.compile(r"sk_live_[0-9a-zA-Z]{24,}"), "confirmed", "critical"),
    ("Generic Secret Assignment", re.compile(r"(?i)(?:secret|password|passwd|pwd|token|apikey|api_key|auth_token|access_token|private_key)\s*[=:]\s*['\"]([^\s'\"]{8,})['\"]"), "possible", "medium"),
]

SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".zip", ".tar", ".gz", ".exe", ".dll", ".pyc"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
SKIP_PATHS = {".git", "node_modules", "__pycache__", "venv"}

def shannon_entropy(s: str) -> float:
    if not s: return 0.0
    freq: dict[str, int] = {}
    for c in s: freq[c] = freq.get(c, 0) + 1
    return -sum((count / len(s)) * math.log2(count / len(s)) for count in freq.values())

def redact(text: str, keep: int = 5) -> str:
    if len(text) <= keep + 3: return "*" * len(text)
    return text[:keep] + "*" * 10

# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class Incident:
    repo: str
    detector: str
    file: str
    line_num: int
    matched_text: str
    raw_match: str
    confidence: str
    severity: str
    status: str
    commit_sha: str = ""
    commit_date: str = ""
    commit_author: str = ""
    commit_message: str = ""
    context_lines: list[tuple[int, str]] = field(default_factory=list)
    entropy: float = 0.0

@dataclass
class ScanResult:
    repo: str
    incidents: list[Incident] = field(default_factory=list)
    error: str | None = None
    commit_count: int = 0

@dataclass
class RepoSummary:
    name: str
    health: str
    open_count: int
    closed_count: int
    total_commits: int
    incidents: list[Incident]

# ── Scanner Logic ────────────────────────────────────────────────────────────

def scan_repo_full(repo_root: Path, repo_name: str) -> list[Incident]:
    incidents = []
    # Current files
    for dirpath, _, filenames in os.walk(repo_root):
        if any(p in dirpath for p in SKIP_PATHS): continue
        for fname in filenames:
            if os.path.splitext(fname)[1].lower() in SKIP_EXTENSIONS: continue
            fpath = Path(dirpath) / fname
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    for det, pat, conf, sev in DETECTORS:
                        for m in pat.finditer(line):
                            raw = m.group(1) if m.lastindex else m.group(0)
                            ctx = [(j, lines[j-1]) for j in range(max(1, i-3), min(len(lines)+1, i+4))]
                            incidents.append(Incident(repo_name, det, str(fpath.relative_to(repo_root)), i, redact(raw), raw, conf, sev, "active", context_lines=ctx, entropy=shannon_entropy(raw)))
            except: continue

    # History
    try:
        r = subprocess.run(["git", "-C", str(repo_root), "log", "--all", "-p", "--format=COMMIT:%H|%aI|%an|%s"], capture_output=True, text=True, errors="replace", timeout=60)
        curr_c = ""; curr_d = ""; curr_a = ""; curr_m = ""; curr_f = ""
        for line in r.stdout.splitlines():
            if line.startswith("COMMIT:"):
                parts = line[7:].split("|", 3)
                if len(parts)==4: curr_c, curr_d, curr_a, curr_m = parts
            elif line.startswith("diff --git"):
                m = re.search(r" b/(.+)$", line)
                curr_f = m.group(1) if m else ""
            elif line.startswith("+") and not line.startswith("+++") and curr_f:
                txt = line[1:]
                for det, pat, conf, sev in DETECTORS:
                    for m in pat.finditer(txt):
                        raw = m.group(1) if m.lastindex else m.group(0)
                        if any(inc.raw_match == raw and inc.detector == det for inc in incidents): continue
                        incidents.append(Incident(repo_name, det, curr_f, 0, redact(raw), raw, conf, sev, "historic", curr_c[:8], curr_d[:10], curr_a, curr_m[:50], entropy=shannon_entropy(raw)))
    except: pass
    return incidents

def fetch_repos(u):
    r = subprocess.run(["gh", "repo", "list", u, "--visibility=public", "--json", "name,url", "--limit", "100"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

# ── Desktop App ──────────────────────────────────────────────────────────────

SEVERITY_COLORS = {"critical": "#ff5555", "high": "#ffb86c", "medium": "#f1fa8c", "low": "#6272a4"}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Repo Security Scanner")
        self.geometry("1400x850") # Wider for split view
        self.scanning = False
        self.results = []
        self.repo_summaries = {}
        self.findings_map = {}
        self.current_repo = None
        self.current_view = "dashboard"

        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(top, text="Repo Scanner", font=("Segoe UI", 24, "bold")).pack(side="left")
        self.bc_frame = ctk.CTkFrame(top, fg_color="transparent"); self.bc_frame.pack(side="left", padx=20)
        
        btns = ctk.CTkFrame(top, fg_color="transparent"); btns.pack(side="right")
        self.user_var = tk.StringVar(value="MadsRudolph")
        ctk.CTkEntry(btns, textvariable=self.user_var, width=150).pack(side="left", padx=5)
        self.scan_btn = ctk.CTkButton(btns, text="Scan", command=self._start_scan, width=100); self.scan_btn.pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Ready"); ctk.CTkLabel(self, textvariable=self.status_var, text_color="gray").pack(anchor="w", padx=15)
        self.progress = ctk.CTkProgressBar(self); self.progress.set(0); self.progress.pack(fill="x", padx=15, pady=5)

        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent"); self.summary_frame.pack(fill="x", padx=15, pady=10)
        self._update_summaries()

        self.main_container = ctk.CTkFrame(self, fg_color="transparent"); self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        self._switch_view("dashboard")

    def _apply_theme(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview", background="#282a36", foreground="#f8f8f2", fieldbackground="#282a36", rowheight=30)
        s.configure("Treeview.Heading", background="#44475a", foreground="#f8f8f2", font=("Segoe UI", 10, "bold"))

    def _switch_view(self, view, **kwargs):
        self.current_view = view
        for w in self.main_container.winfo_children(): w.destroy()
        self._update_bc()
        if view == "dashboard": self._build_dashboard()
        elif view == "repo": 
            self.current_repo = kwargs.get("name")
            self._build_repo_view(self.current_repo)

    def _update_bc(self):
        for w in self.bc_frame.winfo_children(): w.destroy()
        b = ctk.CTkButton(self.bc_frame, text="Home", width=60, fg_color="transparent", text_color="#6272a4", command=lambda: self._switch_view("dashboard"))
        b.pack(side="left")
        if self.current_repo and self.current_view != "dashboard":
            ctk.CTkLabel(self.bc_frame, text=" > ").pack(side="left")
            ctk.CTkButton(self.bc_frame, text=self.current_repo, width=60, fg_color="transparent", text_color="#6272a4", command=lambda: self._switch_view("repo", name=self.current_repo)).pack(side="left")

    def _build_dashboard(self):
        t = ttk.Treeview(self.main_container, columns=("name", "health", "incidents"), show="headings")
        t.heading("name", text="Repository"); t.heading("health", text="Status"); t.heading("incidents", text="Findings")
        t.pack(fill="both", expand=True)
        t.tag_configure("at_risk", foreground="#ff5555"); t.tag_configure("safe", foreground="#50fa7b")
        for n, s in self.repo_summaries.items():
            t.insert("", "end", values=(n, "At Risk" if s.health=="at_risk" else "Safe", f"{s.open_count} open"), tags=(s.health,))
        t.bind("<<TreeviewSelect>>", lambda _: self._switch_view("repo", name=t.item(t.selection()[0])["values"][0]))

    def _build_repo_view(self, name):
        s = self.repo_summaries.get(name)
        if not s: return
        
        # Split Layout
        split = ctk.CTkFrame(self.main_container, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)
        split.grid_rowconfigure(0, weight=1)

        # Left: List
        left = ctk.CTkFrame(split); left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(left, text="Security Incidents", font=("Segoe UI", 16, "bold")).pack(pady=5)
        
        t = ttk.Treeview(left, columns=("type", "file", "sev"), show="headings")
        t.heading("type", text="Type"); t.heading("file", text="Location"); t.heading("sev", text="Sev")
        t.column("type", width=150); t.column("file", width=200); t.column("sev", width=80)
        t.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Right: Detail Sidebar
        self.sidebar = ctk.CTkFrame(split); self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.sidebar_placeholder = ctk.CTkLabel(self.sidebar, text="Select an incident to view details", text_color="gray")
        self.sidebar_placeholder.pack(expand=True)

        for i, inc in enumerate(s.incidents):
            iid = f"inc_{i}"
            self.findings_map[iid] = inc
            t.insert("", "end", iid=iid, values=(inc.detector, f"{inc.file}:{inc.line_num}", inc.severity.upper()))
        
        t.bind("<<TreeviewSelect>>", lambda _: self._update_sidebar(t.selection()[0]))

    def _update_sidebar(self, iid):
        inc = self.findings_map.get(iid)
        if not inc: return
        
        for w in self.sidebar.winfo_children(): w.destroy()
        
        top = ctk.CTkFrame(self.sidebar, fg_color="transparent"); top.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(top, text=inc.detector, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(top, text=f"{inc.severity.upper()} severity • {inc.status.upper()}", 
                      text_color=SEVERITY_COLORS.get(inc.severity), font=("Segoe UI", 11, "bold")).pack(anchor="w")

        meta = ctk.CTkFrame(self.sidebar, fg_color="#343746", corner_radius=8); meta.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(meta, text=f"File: {inc.file}", font=("Segoe UI", 11)).pack(anchor="w", padx=10, pady=2)
        if inc.commit_sha:
            ctk.CTkLabel(meta, text=f"Commit: {inc.commit_sha} by {inc.commit_author}", font=("Segoe UI", 11)).pack(anchor="w", padx=10, pady=2)

        txt = ctk.CTkTextbox(self.sidebar, font=("Consolas", 12), fg_color="#191a21"); txt.pack(fill="both", expand=True, padx=15, pady=10)
        for l, line in inc.context_lines:
            mark = " >>> " if l == inc.line_num else "     "
            txt.insert("end", f"{l:4d}{mark}{line}\n")
        txt.configure(state="disabled")

    def _update_summaries(self):
        for w in self.summary_frame.winfo_children(): w.destroy()
        vals = [("Repos", len(self.results)), ("Active", sum(s.open_count for s in self.repo_summaries.values())), ("Historic", sum(s.closed_count for s in self.repo_summaries.values()))]
        for l, v in vals:
            f = ctk.CTkFrame(self.summary_frame); f.pack(side="left", fill="both", expand=True, padx=5)
            ctk.CTkLabel(f, text=str(v), font=("Segoe UI", 20, "bold")).pack(); ctk.CTkLabel(f, text=l, font=("Segoe UI", 10)).pack()

    def _start_scan(self):
        u = self.user_var.get().strip()
        if not u: return
        self.scanning = True; self.scan_btn.configure(state="disabled")
        self.results = []; self.repo_summaries = {}; self.findings_map = {}
        threading.Thread(target=self._scan_thread, args=(u,), daemon=True).start()

    def _scan_thread(self, u):
        try:
            rs = fetch_repos(u)
            tmp = tempfile.mkdtemp()
            for i, r in enumerate(rs):
                if not self.scanning: break
                n = r["name"]; url = r["url"]
                self.after(0, lambda idx=i, name=n, tot=len(rs): self.status_var.set(f"[{idx+1}/{tot}] {name}..."))
                self.after(0, lambda idx=i, tot=len(rs): self.progress.set(idx/tot))
                p = Path(tmp) / n
                try: subprocess.run(["git", "clone", "--quiet", "--depth=1", url, str(p)], check=True)
                except: continue
                incs = scan_repo_full(p, n)
                h = "at_risk" if any(i.severity in ("critical", "high") for i in incs) else "safe"
                self.repo_summaries[n] = RepoSummary(n, h, sum(1 for i in incs if i.status=="active"), sum(1 for i in incs if i.status=="historic"), 0, incs)
                self.after(0, self._update_summaries)
                if self.current_view == "dashboard": self.after(0, self._build_dashboard)
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception as e: self.after(0, lambda msg=str(e): messagebox.showerror("Error", msg))
        self.after(0, self._scan_done)

    def _scan_done(self):
        self.scanning = False; self.scan_btn.configure(state="normal")
        self.status_var.set("Scan Complete"); self.progress.set(1)

if __name__ == "__main__": App().mainloop()
