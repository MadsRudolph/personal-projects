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
# Each detector: (pattern, confidence, severity)
# confidence: how sure we are this is a real secret (not a false positive)
#   "confirmed" = pattern is unique to real secrets (e.g. AKIA prefix)
#   "likely"    = strong signal but could be a test value
#   "possible"  = needs human review

DETECTORS: list[tuple[str, re.Pattern, str, str]] = [
    # ── Cloud Providers ──
    ("AWS Access Key ID",       re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"), "confirmed", "critical"),
    ("AWS Secret Access Key",   re.compile(r"(?i)(?:aws_secret_access_key|aws_secret)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"), "confirmed", "critical"),
    ("Google API Key",          re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "confirmed", "high"),
    ("Google OAuth Secret",     re.compile(r"(?i)client_secret.*?['\"]([A-Za-z0-9\-_]{24})['\"]"), "possible", "high"),
    ("Azure Storage Key",       re.compile(r"(?i)(?:AccountKey|azure[_\-]?storage[_\-]?key)\s*[=:]\s*['\"]?([A-Za-z0-9+/=]{88})['\"]?"), "confirmed", "critical"),

    # ── Version Control / CI ──
    ("GitHub Token",            re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"), "confirmed", "critical"),
    ("GitHub Personal Token",   re.compile(r"github_pat_[A-Za-z0-9_]{22,255}"), "confirmed", "critical"),
    ("GitLab Token",            re.compile(r"glpat-[A-Za-z0-9\-_]{20,}"), "confirmed", "critical"),

    # ── Communication ──
    ("Slack Token",             re.compile(r"xox[bposa]-[0-9]{10,}-[A-Za-z0-9\-]+"), "confirmed", "critical"),
    ("Slack Webhook",           re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+"), "confirmed", "high"),
    ("Discord Bot Token",       re.compile(r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}"), "likely", "critical"),
    ("Telegram Bot Token",      re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"), "confirmed", "critical"),

    # ── Payment ──
    ("Stripe Secret Key",       re.compile(r"sk_live_[0-9a-zA-Z]{24,}"), "confirmed", "critical"),
    ("Stripe Publishable Key",  re.compile(r"pk_live_[0-9a-zA-Z]{24,}"), "confirmed", "medium"),

    # ── AI ──
    ("OpenAI API Key",          re.compile(r"sk-[A-Za-z0-9]{20,}"), "likely", "critical"),
    ("Anthropic API Key",       re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"), "confirmed", "critical"),

    # ── Package Registries ──
    ("NPM Token",               re.compile(r"npm_[A-Za-z0-9]{36}"), "confirmed", "high"),
    ("PyPI Token",              re.compile(r"pypi-[A-Za-z0-9\-_]{50,}"), "confirmed", "high"),

    # ── Crypto / Auth ──
    ("Private Key",             re.compile(r"-----BEGIN\s+(RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "confirmed", "critical"),
    ("JWT Token",               re.compile(r"eyJ[A-Za-z0-9\-_]{10,}\.eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_.+/=]{10,}"), "likely", "high"),
    ("Basic Auth in URL",       re.compile(r"https?://[^\s:]+:[^\s@]+@[^\s]+"), "likely", "critical"),
    ("Database Connection String", re.compile(r"(?i)(?:postgres|mysql|mongodb|redis|mssql)://[^\s'\"]+:[^\s'\"]+@[^\s'\"]+"), "confirmed", "critical"),

    # ── Messaging / Email ──
    ("SendGrid API Key",        re.compile(r"SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}"), "confirmed", "critical"),
    ("Twilio API Key",          re.compile(r"SK[0-9a-fA-F]{32}"), "likely", "high"),
    ("Mailgun API Key",         re.compile(r"key-[A-Za-z0-9]{32}"), "likely", "high"),

    # ── IoT / Home Automation ──
    ("Home Assistant Token",    re.compile(r"(?i)(?:ha|hass)[_\-]?(?:long_lived)?[_\-]?token\s*[=:]\s*['\"]?(eyJ[A-Za-z0-9\-_]+)"), "confirmed", "critical"),
    ("Spotify Client Secret",   re.compile(r"(?i)spotify[_\-]?(?:client)?[_\-]?secret\s*[=:]\s*['\"]?([A-Za-z0-9]{32})['\"]?"), "likely", "high"),

    # ── Generic Patterns (lower confidence) ──
    ("Generic Secret Assignment", re.compile(r"(?i)(?:secret|password|passwd|pwd|token|apikey|api_key|auth_token|access_token|private_key)\s*[=:]\s*['\"]([^\s'\"]{8,})['\"]"), "possible", "medium"),
    ("Generic Secret in ENV",     re.compile(r"(?i)(?:SECRET|PASSWORD|TOKEN|API_KEY|APIKEY|AUTH|PRIVATE_KEY)[A-Z_]*\s*=\s*['\"]?([^\s'\"#]{8,})['\"]?"), "possible", "medium"),
]

# Files/patterns to always skip
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".pfb", ".tfm",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".o", ".obj",
    ".bin", ".dat", ".db", ".sqlite",
    ".pyc", ".pyo", ".class", ".lock", ".sum",
    ".min.js", ".min.css",
}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum",
              "Cargo.lock", "poetry.lock", "composer.lock", "Gemfile.lock"}
SKIP_PATHS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              "dist", "build", ".next", "vendor", ".gradle"}

PLACEHOLDER_RE = re.compile(
    r"(?i)(?:example|placeholder|xxx+|your[_\-]|insert[_\-]|changeme|"
    r"todo|fixme|dummy|sample|replace[_\-]|fill[_\-]in|<[^>]+>|\$\{|\{\{)")


# ── Shannon Entropy ──────────────────────────────────────────────────────────

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


# High-entropy string in an assignment context
HIGH_ENTROPY_ASSIGNMENT_RE = re.compile(
    r"(?i)(?:secret|password|token|key|apikey|api_key|auth|credential|private)"
    r"\s*[=:]\s*['\"]?([A-Za-z0-9+/=\-_]{16,})['\"]?"
)

def check_entropy(line: str) -> tuple[str, float] | None:
    """Check for high-entropy strings in secret-like assignments."""
    m = HIGH_ENTROPY_ASSIGNMENT_RE.search(line)
    if not m:
        return None
    value = m.group(1)
    ent = shannon_entropy(value)
    # Threshold: 4.0 bits/char is typical for random secrets
    # (English text ~4.0, random base64 ~5.9, random hex ~4.0)
    if ent >= 4.0 and len(value) >= 16:
        return value, ent
    return None


# ── Data ─────────────────────────────────────────────────────────────────────

@dataclass
class Incident:
    repo: str
    detector: str
    file: str
    line_num: int
    matched_text: str       # redacted
    raw_match: str          # for dedup (also redacted, but full pattern)
    confidence: str         # confirmed, likely, possible
    severity: str           # critical, high, medium, low
    status: str             # "active" or "historic"
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


# ── Scanner ──────────────────────────────────────────────────────────────────

def redact(text: str, keep: int = 5) -> str:
    if len(text) <= keep + 3:
        return "*" * len(text)
    return text[:keep] + "*" * min(10, len(text) - keep)


def should_skip_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    for p in parts:
        if p in SKIP_PATHS:
            return True
    ext = os.path.splitext(path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return True
    basename = os.path.basename(path)
    if basename in SKIP_FILES:
        return True
    return False


def is_placeholder(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text))


def scan_line(line: str, detector_name: str, pattern: re.Pattern,
              confidence: str, severity: str) -> list[tuple[str, str, str, str]]:
    """Returns list of (matched_text, confidence, severity, raw_match)."""
    results = []
    for match in pattern.finditer(line):
        raw = match.group(1) if match.lastindex else match.group(0)
        if is_placeholder(raw):
            continue
        # Boost confidence if entropy is high
        ent = shannon_entropy(raw)
        final_confidence = confidence
        if ent >= 4.5 and confidence == "possible":
            final_confidence = "likely"
        results.append((redact(raw), final_confidence, severity, redact(raw, 8)))
    return results


def scan_current_files(repo_root: Path, repo_name: str) -> list[Incident]:
    """Scan current HEAD files for active secrets."""
    incidents = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_PATHS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            rel_path = str(fpath.relative_to(repo_root)).replace("\\", "/")
            if should_skip_path(rel_path):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = content.splitlines()
            for line_num, line in enumerate(lines, start=1):
                if len(line) > 2000:
                    continue

                for det_name, pattern, confidence, severity in DETECTORS:
                    for match in pattern.finditer(line):
                        raw = match.group(1) if match.lastindex else match.group(0)
                        if is_placeholder(raw):
                            continue
                        ent = shannon_entropy(raw)
                        final_conf = confidence
                        if ent >= 4.5 and confidence == "possible":
                            final_conf = "likely"

                        start = max(0, line_num - 1 - 3)
                        end = min(len(lines), line_num - 1 + 4)
                        context = [(i + 1, lines[i]) for i in range(start, end)]

                        incidents.append(Incident(
                            repo=repo_name, detector=det_name,
                            file=rel_path, line_num=line_num,
                            matched_text=redact(raw), raw_match=redact(raw, 12),
                            confidence=final_conf, severity=severity,
                            status="active", entropy=ent,
                            context_lines=context,
                        ))

                # Entropy-only detection for unknown patterns
                ent_result = check_entropy(line)
                if ent_result:
                    value, ent = ent_result
                    # Skip if already caught by a specific detector
                    already_found = any(
                        i.file == rel_path and i.line_num == line_num
                        for i in incidents
                    )
                    if not already_found and not is_placeholder(value):
                        start = max(0, line_num - 1 - 3)
                        end = min(len(lines), line_num - 1 + 4)
                        context = [(i + 1, lines[i]) for i in range(start, end)]
                        incidents.append(Incident(
                            repo=repo_name, detector="High Entropy Secret",
                            file=rel_path, line_num=line_num,
                            matched_text=redact(value), raw_match=redact(value, 12),
                            confidence="possible", severity="medium",
                            status="active", entropy=ent,
                            context_lines=context,
                        ))
    return incidents


def scan_git_history(repo_root: Path, repo_name: str,
                     active_secrets: set[str]) -> list[Incident]:
    """Scan git log diffs for secrets that were added then removed."""
    incidents = []
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--all", "--diff-filter=AD",
             "-p", "--format=COMMIT:%H|%aI|%an|%s", "--no-color"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if result.returncode != 0:
            return incidents
    except (subprocess.TimeoutExpired, Exception):
        return incidents

    current_commit = ""
    current_date = ""
    current_author = ""
    current_message = ""
    current_file = ""
    diff_lines: list[str] = []

    def flush_diff():
        nonlocal diff_lines
        if not current_file or not diff_lines or should_skip_path(current_file):
            diff_lines = []
            return

        added_lines = [(i, l[1:]) for i, l in enumerate(diff_lines, 1) if l.startswith("+") and not l.startswith("+++")]

        for diff_line_num, line in added_lines:
            if len(line) > 2000:
                continue
            for det_name, pattern, confidence, severity in DETECTORS:
                for match in pattern.finditer(line):
                    raw = match.group(1) if match.lastindex else match.group(0)
                    if is_placeholder(raw):
                        continue
                    key = f"{det_name}:{redact(raw, 12)}"
                    if key in active_secrets:
                        continue  # Already reported as active
                    ent = shannon_entropy(raw)
                    final_conf = confidence
                    if ent >= 4.5 and confidence == "possible":
                        final_conf = "likely"

                    # Context from diff
                    start = max(0, diff_line_num - 4)
                    end = min(len(diff_lines), diff_line_num + 3)
                    context = [(i + 1, diff_lines[i]) for i in range(start, end)]

                    incidents.append(Incident(
                        repo=repo_name, detector=det_name,
                        file=current_file, line_num=diff_line_num,
                        matched_text=redact(raw), raw_match=redact(raw, 12),
                        confidence=final_conf, severity=severity,
                        status="historic",
                        commit_sha=current_commit[:8],
                        commit_date=current_date[:10],
                        commit_author=current_author,
                        commit_message=current_message[:80],
                        entropy=ent, context_lines=context,
                    ))
                    active_secrets.add(key)  # Prevent dupes across commits
        diff_lines = []

    for raw_line in result.stdout.splitlines():
        if raw_line.startswith("COMMIT:"):
            flush_diff()
            parts = raw_line[7:].split("|", 3)
            if len(parts) == 4:
                current_commit, current_date, current_author, current_message = parts
        elif raw_line.startswith("diff --git"):
            flush_diff()
            # Extract file path: "diff --git a/path b/path"
            m = re.search(r" b/(.+)$", raw_line)
            current_file = m.group(1) if m else ""
        elif raw_line.startswith("@@") or raw_line.startswith("+++") or raw_line.startswith("---"):
            pass
        elif current_file:
            diff_lines.append(raw_line)

    flush_diff()

    # Deduplicate: keep only unique detector+match combinations
    seen: set[str] = set()
    deduped: list[Incident] = []
    for inc in incidents:
        key = f"{inc.detector}:{inc.raw_match}"
        if key not in seen:
            seen.add(key)
            deduped.append(inc)
    return deduped


def scan_repo_full(repo_root: Path, repo_name: str) -> list[Incident]:
    """Full GitGuardian-style scan: current files + git history."""
    # 1) Scan current HEAD
    active = scan_current_files(repo_root, repo_name)

    # 2) Build set of already-found secrets for dedup
    active_keys = {f"{i.detector}:{i.raw_match}" for i in active}

    # 3) Scan git history for removed secrets
    historic = scan_git_history(repo_root, repo_name, active_keys)

    return active + historic


def fetch_repos(username: str) -> list[dict]:
    result = subprocess.run(
        ["gh", "repo", "list", username, "--visibility=public",
         "--json", "name,url", "--limit", "100"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    return json.loads(result.stdout)


def clone_repo_full(url: str, dest: Path) -> None:
    """Full clone (not shallow) so we can scan git history."""
    subprocess.run(
        ["git", "clone", "--quiet", url, str(dest)],
        capture_output=True, check=True,
    )


def find_local_repo(repo_name: str) -> Path | None:
    """Check common locations for an existing local clone."""
    home = Path.home()
    candidates = [
        home / repo_name,
        home / "personal-projects" / repo_name,
        home / "projects" / repo_name,
        home / "repos" / repo_name,
        home / "Documents" / repo_name,
    ]
    for path in candidates:
        if (path / ".git").is_dir():
            return path
    return None


def ensure_repo(repo_name: str, repo_url: str, tmpdir: Path) -> tuple[Path, bool]:
    """Returns (repo_path, is_local). Uses local clone if available, otherwise clones to tmpdir."""
    local = find_local_repo(repo_name)
    if local:
        # Fetch latest to make sure history is up to date, but don't fail if offline
        subprocess.run(
            ["git", "-C", str(local), "fetch", "--quiet", "--all"],
            capture_output=True, timeout=30,
        )
        return local, True
    dest = tmpdir / repo_name
    clone_repo_full(repo_url, dest)
    return dest, False


def count_commits(repo_root: Path) -> int:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_root), "rev-list", "--count", "--all"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return int(r.stdout.strip()) if r.returncode == 0 else 0
    except Exception:
        return 0


# ── App ──────────────────────────────────────────────────────────────────────

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_COLORS = {
    "critical": "#f38ba8",
    "high": "#fab387",
    "medium": "#f9e2af",
    "low": "#a6adc8",
}
STATUS_LABELS = {"active": "ACTIVE", "historic": "HISTORIC"}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Repo Security Scanner")
        self.geometry("1200x780")
        self.minsize(1000, 620)
        self.scanning = False
        self.results: list[ScanResult] = []
        self.findings_map: dict[str, Incident] = {}

        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(top, text="Repo Security Scanner",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        actions_frame = ctk.CTkFrame(top, fg_color="transparent")
        actions_frame.pack(side="right")

        self.prompt_btn = ctk.CTkButton(
            actions_frame, text="Generate Fix Prompt",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._generate_claude_prompt, width=160,
            fg_color="#8c4bb5", hover_color="#6e3b8e",
        )
        self.prompt_btn.pack(side="left", padx=(0, 12))

        self.scan_btn = ctk.CTkButton(
            actions_frame, text="Scan Repos",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_scan, width=120,
        )
        self.scan_btn.pack(side="left")

        user_frame = ctk.CTkFrame(top, fg_color="transparent")
        user_frame.pack(side="right", padx=(0, 16))

        ctk.CTkLabel(user_frame, text="GitHub user:",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self.username_var = tk.StringVar(value="MadsRudolph")
        self.username_entry = ctk.CTkEntry(
            user_frame, textvariable=self.username_var,
            font=ctk.CTkFont(size=13), width=200,
        )
        self.username_entry.pack(side="left", padx=(8, 0))

        # Progress
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=16)

        self.status_var = tk.StringVar(value="Ready — full clone + history scan")
        self.status_label = ctk.CTkLabel(
            prog_frame, textvariable=self.status_var,
            font=ctk.CTkFont(size=12), text_color="gray",
        )
        self.status_label.pack(anchor="w")

        self.progress = ctk.CTkProgressBar(prog_frame)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(4, 0))

        # Summary cards
        cards_outer = ctk.CTkFrame(self, fg_color="transparent")
        cards_outer.pack(fill="x", padx=16, pady=12)
        self.cards_container = ctk.CTkFrame(cards_outer, fg_color="transparent")
        self.cards_container.pack(fill="x")
        self._build_summary_cards()

        # Filter bar
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=16)

        ctk.CTkLabel(filter_frame, text="Filter:",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))
        self.filter_seg = ctk.CTkSegmentedButton(
            filter_frame,
            values=["All", "Active", "Historic", "Critical", "High", "Confirmed", "Possible"],
            command=self._apply_filter,
        )
        self.filter_seg.set("All")
        self.filter_seg.pack(side="left")

        # Main content: tree + detail
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # Tree
        tree_frame = ctk.CTkFrame(main)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        cols = ("severity", "status", "repo", "file", "detector", "confidence", "commit")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        headings = {
            "severity": ("Severity", 75), "status": ("Status", 75),
            "repo": ("Repo", 110), "file": ("File", 180),
            "detector": ("Detector", 160), "confidence": ("Confidence", 85),
            "commit": ("Commit", 80),
        }
        for col, (label, width) in headings.items():
            self.tree.heading(col, text=label,
                              command=lambda c=col: self._sort_column(c, False))
            stretch = col in ("file", "detector", "repo")
            self.tree.column(col, width=width, minwidth=50, stretch=stretch)

        scroll = ctk.CTkScrollbar(tree_frame, orientation="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        scroll.pack(side="right", fill="y", padx=4, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Detail panel
        detail_frame = ctk.CTkFrame(main)
        detail_frame.grid(row=0, column=1, sticky="nsew")

        # Detail header
        dh = ctk.CTkFrame(detail_frame, fg_color="transparent")
        dh.pack(fill="x", padx=12, pady=8)
        self.detail_title = ctk.CTkLabel(dh, text="Incident Details",
                                         font=ctk.CTkFont(size=15, weight="bold"))
        self.detail_title.pack(side="left")
        self.detail_badge = ctk.CTkLabel(dh, text="",
                                         font=ctk.CTkFont(size=11), text_color="gray")
        self.detail_badge.pack(side="right")

        # Metadata
        self.meta_frame = ctk.CTkFrame(detail_frame, fg_color="#1e1e2e",
                                       corner_radius=8)
        self.meta_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.meta_labels: dict[str, ctk.CTkLabel] = {}
        for key in ["Detector", "Severity", "Confidence", "Status",
                     "File", "Entropy", "Commit", "Date", "Author"]:
            row = ctk.CTkFrame(self.meta_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(row, text=f"{key}:", font=ctk.CTkFont(size=11),
                         text_color="#6c7086", width=75, anchor="e").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=11),
                               anchor="w")
            lbl.pack(side="left", padx=(6, 0))
            self.meta_labels[key] = lbl

        # Code context
        ctk.CTkLabel(detail_frame, text="Code Context",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 2))

        self.code_text = ctk.CTkTextbox(
            detail_frame, font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none", fg_color="#1e1e2e", border_width=1,
            border_color="#313150",
        )
        self.code_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.code_text.configure(state="disabled")

        self.code_text.tag_config("hit_bg", background="#3e2938")
        self.code_text.tag_config("hit_text", foreground="#f38ba8", background="#5e2b34")
        self.code_text.tag_config("linenum", foreground="#6c7086")
        self.code_text.tag_config("context", foreground="#cdd6f4")
        self.code_text.tag_config("diff_add", foreground="#a6e3a1")
        self.code_text.tag_config("diff_del", foreground="#f38ba8")

    def _build_summary_cards(self):
        for w in self.cards_container.winfo_children():
            w.destroy()

        self.card_vars = {
            "repos": tk.StringVar(value="0"),
            "incidents": tk.StringVar(value="0"),
            "active": tk.StringVar(value="0"),
            "historic": tk.StringVar(value="0"),
            "critical": tk.StringVar(value="0"),
        }
        cards = [
            ("Repos Scanned", self.card_vars["repos"], "#89b4fa"),
            ("Incidents", self.card_vars["incidents"], "#f9e2af"),
            ("Active", self.card_vars["active"], "#f38ba8"),
            ("In History", self.card_vars["historic"], "#fab387"),
            ("Critical", self.card_vars["critical"], "#f38ba8"),
        ]
        self.cards_container.grid_columnconfigure(tuple(range(len(cards))), weight=1)
        for i, (label, var, color) in enumerate(cards):
            card = ctk.CTkFrame(self.cards_container, corner_radius=10,
                                fg_color="#282840", border_width=1, border_color="#45475a")
            card.grid(row=0, column=i, sticky="ew", padx=4)
            ctk.CTkLabel(card, textvariable=var,
                         font=ctk.CTkFont(size=28, weight="bold"),
                         text_color=color).pack(pady=(12, 0))
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11),
                         text_color="#a6adc8").pack(pady=(0, 12))

    def _apply_theme(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="#dce4ee",
                        fieldbackground="#2b2b2b", borderwidth=0,
                        font=("Segoe UI", 10), rowheight=28)
        style.configure("Treeview.Heading", background="#333333",
                        foreground="#dce4ee", font=("Segoe UI", 10, "bold"),
                        borderwidth=1)
        style.map("Treeview", background=[("selected", "#1f538d")],
                  foreground=[("selected", "white")])
        style.map("Treeview.Heading", background=[("active", "#4d4d4d")])

        self.tree.tag_configure("critical", foreground="#f38ba8")
        self.tree.tag_configure("high", foreground="#fab387")
        self.tree.tag_configure("medium", foreground="#f9e2af")
        self.tree.tag_configure("low", foreground="#a6adc8")

    # ── Interaction ──────────────────────────────────────────────────────

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        inc = self.findings_map.get(sel[0])
        if not inc:
            return

        self.detail_title.configure(text=inc.detector)
        status_text = "ACTIVE — secret is live in repo" if inc.status == "active" \
            else "HISTORIC — removed but in git history"
        self.detail_badge.configure(text=status_text,
                                    text_color="#f38ba8" if inc.status == "active" else "#fab387")

        sev_color = SEVERITY_COLORS.get(inc.severity, "#cdd6f4")
        self.meta_labels["Detector"].configure(text=inc.detector)
        self.meta_labels["Severity"].configure(text=inc.severity.upper(),
                                                text_color=sev_color)
        self.meta_labels["Confidence"].configure(text=inc.confidence.upper())
        self.meta_labels["Status"].configure(
            text=inc.status.upper(),
            text_color="#f38ba8" if inc.status == "active" else "#fab387")
        self.meta_labels["File"].configure(text=f"{inc.file}:{inc.line_num}")
        self.meta_labels["Entropy"].configure(
            text=f"{inc.entropy:.2f} bits/char" if inc.entropy else "—")
        self.meta_labels["Commit"].configure(
            text=inc.commit_sha if inc.commit_sha else "(HEAD)")
        self.meta_labels["Date"].configure(
            text=inc.commit_date if inc.commit_date else "—")
        self.meta_labels["Author"].configure(
            text=inc.commit_author if inc.commit_author else "—")

        # Code context
        self.code_text.configure(state="normal")
        self.code_text.delete("1.0", "end")

        for lnum, ltext in inc.context_lines:
            prefix = f" {lnum:4d} | "
            full = prefix + ltext + "\n"

            start = self.code_text.index("end-1c")
            self.code_text.insert("end", full)
            row = start.split(".")[0]
            pipe_end = f"{row}.{len(prefix)}"
            line_end = self.code_text.index("end-1c")

            self.code_text.tag_add("linenum", start, pipe_end)

            if lnum == inc.line_num:
                self.code_text.tag_add("hit_bg", start, line_end)
                self.code_text.tag_add("hit_text", pipe_end, line_end)
            elif inc.status == "historic" and ltext.startswith("+"):
                self.code_text.tag_add("diff_add", pipe_end, line_end)
            elif inc.status == "historic" and ltext.startswith("-"):
                self.code_text.tag_add("diff_del", pipe_end, line_end)
            else:
                self.code_text.tag_add("context", pipe_end, line_end)

        self.code_text.configure(state="disabled")

    def _generate_claude_prompt(self):
        critical = [i for r in self.results for i in r.incidents
                    if i.severity in ("critical", "high")]
        if not critical:
            messagebox.showinfo("No Critical Findings",
                                "No critical/high severity incidents found.", parent=self)
            return

        by_repo: dict[str, list[Incident]] = {}
        for i in critical:
            by_repo.setdefault(i.repo, []).append(i)

        lines = [
            "Fix these security incidents found in my public GitHub repos.\n",
            "For secrets that are ACTIVE: remove them from code and rotate the credential.",
            "For secrets that are HISTORIC: the credential must still be rotated even though",
            "it was removed, because it exists in git history.\n",
        ]
        for repo, incs in by_repo.items():
            lines.append(f"### {repo}")
            for i in incs:
                status = "ACTIVE" if i.status == "active" else "IN GIT HISTORY"
                lines.append(
                    f"- [{status}] {i.detector} in `{i.file}:{i.line_num}` "
                    f"(confidence: {i.confidence})"
                )
                if i.commit_sha:
                    lines.append(f"  Introduced in commit {i.commit_sha} ({i.commit_date})")
            lines.append("")
        lines.append("Use environment variables for all secrets. "
                     "Consider using git filter-repo or BFG to purge history.")

        prompt = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(prompt)

        dialog = ctk.CTkToplevel(self)
        dialog.title("Fix Prompt")
        dialog.geometry("650x450")
        dialog.transient(self)
        ctk.CTkLabel(dialog, text="Copied to clipboard!",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(16, 8))
        tb = ctk.CTkTextbox(dialog, font=ctk.CTkFont(family="Consolas", size=12),
                            wrap="word")
        tb.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        tb.insert("1.0", prompt)
        tb.configure(state="disabled")

    # ── Scan Logic ───────────────────────────────────────────────────────

    def _start_scan(self):
        if self.scanning:
            return
        username = self.username_var.get().strip()
        if not username:
            messagebox.showwarning("Input needed", "Enter a GitHub username.")
            return

        self.scanning = True
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.results.clear()
        self.findings_map.clear()
        self.tree.delete(*self.tree.get_children())
        self._update_cards()
        self.status_var.set(f"Fetching public repos for {username}...")
        self.progress.set(0)

        self.code_text.configure(state="normal")
        self.code_text.delete("1.0", "end")
        self.code_text.configure(state="disabled")
        self.detail_title.configure(text="Incident Details")
        self.detail_badge.configure(text="Select an incident", text_color="gray")
        for lbl in self.meta_labels.values():
            lbl.configure(text="—")

        threading.Thread(target=self._scan_worker, args=(username,),
                         daemon=True).start()

    def _scan_worker(self, username: str):
        try:
            repos = fetch_repos(username)
        except Exception as e:
            self.after(0, lambda: self._scan_error(f"Failed to fetch repos: {e}"))
            return

        total = len(repos)
        if total == 0:
            self.after(0, lambda: self._scan_error("No public repos found."))
            return

        self.after(0, lambda: self.status_var.set(
            f"Found {total} repos. Full clone + history scan..."))

        tmpdir = tempfile.mkdtemp(prefix="repo-scan-")
        try:
            for i, repo in enumerate(repos):
                name = repo["name"]
                url = repo["url"]
                self.after(0, lambda n=name, idx=i: (
                    self.status_var.set(
                        f"[{idx + 1}/{total}] Resolving {n}..."),
                    self.progress.set(idx / total),
                ))

                sr = ScanResult(repo=name)
                try:
                    repo_path, is_local = ensure_repo(name, url, Path(tmpdir))
                    source = "local" if is_local else "cloned"
                    sr.commit_count = count_commits(repo_path)
                    self.after(0, lambda n=name, c=sr.commit_count, s=source: (
                        self.status_var.set(
                            f"[{i + 1}/{total}] Scanning {n} ({s}, {c} commits)..."),
                    ))
                    sr.incidents = scan_repo_full(repo_path, name)
                except subprocess.CalledProcessError as e:
                    sr.error = (e.stderr.decode() if e.stderr else str(e)).strip()
                except Exception as e:
                    sr.error = str(e)

                self.results.append(sr)
                if sr.incidents:
                    self.after(0, lambda s=sr: self._add_incidents(s.incidents))
                self.after(0, self._update_cards)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.after(0, self._scan_done)

    def _scan_error(self, msg: str):
        self.status_var.set(f"Error: {msg}")
        self.scanning = False
        self.scan_btn.configure(state="normal", text="Scan Repos")
        self.progress.set(0)

    def _scan_done(self):
        total = sum(len(r.incidents) for r in self.results)
        active = sum(1 for r in self.results for i in r.incidents if i.status == "active")
        historic = sum(1 for r in self.results for i in r.incidents if i.status == "historic")
        commits = sum(r.commit_count for r in self.results)
        errors = sum(1 for r in self.results if r.error)
        self.progress.set(1)
        msg = (f"Done. {len(self.results)} repos, {commits} commits scanned. "
               f"{total} incident(s): {active} active, {historic} in history.")
        if errors:
            msg += f" {errors} error(s)."
        self.status_var.set(msg)
        self.scanning = False
        self.scan_btn.configure(state="normal", text="Scan Repos")

    def _add_incidents(self, incidents: list[Incident]):
        for inc in incidents:
            fid = str(id(inc))
            self.findings_map[fid] = inc
            self.tree.insert("", "end", iid=fid, values=(
                inc.severity.upper(),
                inc.status.upper(),
                inc.repo,
                f"{inc.file}:{inc.line_num}",
                inc.detector,
                inc.confidence.upper(),
                inc.commit_sha or "HEAD",
            ), tags=(inc.severity,))

    def _update_cards(self):
        all_inc = [i for r in self.results for i in r.incidents]
        self.card_vars["repos"].set(str(len(self.results)))
        self.card_vars["incidents"].set(str(len(all_inc)))
        self.card_vars["active"].set(
            str(sum(1 for i in all_inc if i.status == "active")))
        self.card_vars["historic"].set(
            str(sum(1 for i in all_inc if i.status == "historic")))
        self.card_vars["critical"].set(
            str(sum(1 for i in all_inc if i.severity == "critical")))

    def _apply_filter(self, val: str):
        self.tree.delete(*self.tree.get_children())
        fmap = {"All": None, "Active": ("status", "active"),
                "Historic": ("status", "historic"),
                "Critical": ("severity", "critical"),
                "High": ("severity", "high"),
                "Confirmed": ("confidence", "confirmed"),
                "Possible": ("confidence", "possible")}
        filt = fmap.get(val)

        for r in self.results:
            for inc in r.incidents:
                if filt and getattr(inc, filt[0]) != filt[1]:
                    continue
                fid = str(id(inc))
                self.findings_map[fid] = inc
                self.tree.insert("", "end", iid=fid, values=(
                    inc.severity.upper(), inc.status.upper(), inc.repo,
                    f"{inc.file}:{inc.line_num}", inc.detector,
                    inc.confidence.upper(), inc.commit_sha or "HEAD",
                ), tags=(inc.severity,))

    def _sort_column(self, col: str, reverse: bool):
        data = [(self.tree.set(iid, col), iid)
                for iid in self.tree.get_children()]
        if col == "severity":
            data.sort(key=lambda t: SEVERITY_ORDER.get(t[0].lower(), 9),
                      reverse=reverse)
        else:
            data.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for idx, (_, iid) in enumerate(data):
            self.tree.move(iid, "", idx)
        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))


if __name__ == "__main__":
    app = App()
    app.mainloop()
