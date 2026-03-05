#!/usr/bin/env python3
"""Statistics report for AI-generated code.

Primary source: ai_code_log.jsonl (Cursor Rule real-time logging)
Secondary source: agent-transcripts (Cursor auto-recorded, fuzzy extraction)
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
LOG_FILE = WORKSPACE / "ai_code_log.jsonl"


def _find_transcript_dir():
    """Find Cursor's agent-transcripts dir for this workspace."""
    cursor_projects = Path.home() / ".cursor" / "projects"
    if not cursor_projects.exists():
        return None
    workspace_slug = str(WORKSPACE).strip("/").replace("/", "-").replace(".", "-")
    candidate = cursor_projects / workspace_slug / "agent-transcripts"
    if candidate.exists():
        return candidate
    for d in cursor_projects.iterdir():
        if d.is_dir() and WORKSPACE.name in d.name:
            t = d / "agent-transcripts"
            if t.exists():
                return t
    return None


TRANSCRIPT_DIR = _find_transcript_dir()

CODE_EXTENSIONS = {
    ".sql", ".py", ".conf", ".sh", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".scala", ".go", ".rs", ".css", ".scss", ".html",
}

FILE_PATH_PATTERN = re.compile(
    r"(?:creat|modif|updat|writ|edit|generat)\w*"
    r"[^`\n]{0,30}"
    r"`([^`]+\.\w{1,5})`",
    re.IGNORECASE,
)


def load_log_records():
    if not LOG_FILE.exists():
        return []
    records = []
    for line in LOG_FILE.read_text().strip().splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def extract_from_transcripts():
    """Extract file operations from agent transcript text (fuzzy, best-effort)."""
    if not TRANSCRIPT_DIR or not TRANSCRIPT_DIR.exists():
        return []

    findings = []
    for jsonl_path in TRANSCRIPT_DIR.rglob("*.jsonl"):
        session_id = jsonl_path.stem
        for line in jsonl_path.read_text().strip().splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("role") != "assistant":
                continue
            for content_block in entry.get("message", {}).get("content", []):
                text = content_block.get("text", "")
                for match in FILE_PATH_PATTERN.finditer(text):
                    filepath = match.group(1)
                    ext = Path(filepath).suffix.lower()
                    if ext in CODE_EXTENSIONS:
                        findings.append({
                            "session": session_id,
                            "file": filepath,
                            "source": "transcript",
                        })
    seen = set()
    unique = []
    for f in findings:
        key = (f["session"], f["file"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def report_log(records):
    if not records:
        print("  (no records in ai_code_log.jsonl)")
        return

    total_files = len(records)
    created = sum(1 for r in records if r.get("action") == "create")
    modified = sum(1 for r in records if r.get("action") == "modify")
    total_lines_added = sum(r.get("lines_added", 0) for r in records)
    total_lines_modified = sum(r.get("lines_modified", 0) for r in records)

    ext_counter = Counter()
    daily_counter = defaultdict(int)
    for r in records:
        ext = Path(r["file"]).suffix or "(no ext)"
        ext_counter[ext] += r.get("lines_added", 0)
        day = r.get("ts", "")[:10]
        if day:
            daily_counter[day] += r.get("lines_added", 0)

    print(f"  Total operations:     {total_files}")
    print(f"  Files created:        {created}")
    print(f"  Files modified:       {modified}")
    print(f"  Lines added:          {total_lines_added}")
    print(f"  Lines modified:       {total_lines_modified}")

    if ext_counter:
        print(f"\n  Lines added by file type:")
        for ext, count in ext_counter.most_common():
            print(f"    {ext:12s}  {count:>6d}")

    if daily_counter:
        print(f"\n  Lines added by date:")
        for day in sorted(daily_counter):
            print(f"    {day}  {daily_counter[day]:>6d}")


def report_transcripts(findings):
    if not findings:
        print("  (no code files found in transcripts)")
        return

    print(f"  Files touched by AI (extracted from text): {len(findings)}")
    by_session = defaultdict(list)
    for f in findings:
        by_session[f["session"]].append(f["file"])

    for session, files in by_session.items():
        print(f"\n  Session {session[:8]}...:")
        for fp in files:
            print(f"    - {fp}")


def main():
    print("=" * 55)
    print("  AI Code Generation Statistics")
    print("=" * 55)

    print("\n--- Primary: ai_code_log.jsonl ---\n")
    records = load_log_records()
    report_log(records)

    print("\n--- Secondary: Agent Transcripts (fuzzy) ---\n")
    findings = extract_from_transcripts()
    report_transcripts(findings)

    print()


if __name__ == "__main__":
    main()
