"""
Generate a combined Gource log including all git submodules,
"""

import os
import re
import subprocess
from pathlib import Path


LOG_DIR = Path("./gource_logs")
LOG_DIR.mkdir(exist_ok=True)


def run_git(cmd, cwd="."):
    """Run a git command and return its stdout as text."""
    return subprocess.check_output(
        ["git"] + cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL
    ).strip()


def get_branch_name(repo_path="."):
    """Return current branch or 'HEAD' if detached."""
    try:
        name = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if name == "HEAD":
            # Detached HEAD, fallback to commit hash
            return run_git(["rev-parse", "HEAD"], cwd=repo_path)
        return name
    except subprocess.CalledProcessError:
        return "HEAD"


def generate_log(repo_path: str, prefix: str):
    """Generate a gource custom log for a given repo, with optional path prefix."""
    safe_name = prefix.replace("/", "_").replace(".", "_")
    log_path = LOG_DIR / f"{safe_name}.log"
    branch = get_branch_name(repo_path)
    print(f"🧩 Generating log for {repo_path} (branch: {branch})")

    # Run git log to produce file changes in gource-friendly format
    git_log_cmd = [
        "git",
        "log",
        "--pretty=format:user:%aN%x09%ct",
        "--name-status",
        branch,
    ]
    proc = subprocess.Popen(
        git_log_cmd, cwd=repo_path, stdout=subprocess.PIPE, text=True
    )

    with open(log_path, "w", encoding="utf-8") as f_out:
        current_user = None
        current_time = None
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("user:"):
                parts = line.split("\t")
                if len(parts) >= 2:
                    current_user = parts[0][5:]
                    current_time = parts[1]
            elif line and line[0] in ("A", "M", "D"):
                status, *rest = line.split("\t", 1)
                if not rest:
                    continue
                file_path = rest[0]
                if prefix != ".":
                    file_path = f"{prefix}/{file_path}"
                if status == "A":
                    change_type = "A"
                elif status == "M":
                    change_type = "M"
                elif status == "D":
                    change_type = "D"
                else:
                    continue
                if current_time and current_user:
                    f_out.write(
                        f"{current_time}|{current_user}|{change_type}|{file_path}\n"
                    )

    proc.wait()
    return log_path


def get_submodules():
    """Return a list of submodule paths from .gitmodules."""
    gitmodules = Path(".gitmodules")
    if not gitmodules.exists():
        return []
    content = gitmodules.read_text(encoding="utf-8", errors="ignore")
    return re.findall(r"path\s*=\s*(.*)", content)


def merge_logs():
    """Merge and sort all .log files in gource_logs."""
    combined_log = LOG_DIR / "combined.log"
    logs = sorted(LOG_DIR.glob("*.log"))
    with open(combined_log, "w", encoding="utf-8") as out:
        lines = []
        for log_file in logs:
            lines += log_file.read_text(encoding="utf-8").splitlines()
        # Sort numerically by timestamp (first field)
        lines.sort(key=lambda l: int(l.split("|", 1)[0]) if "|" in l else 0)
        out.write("\n".join(lines))
        out.write("\n")
    return combined_log


def launch_gource(log_path: Path):
    """Launch gource on the combined log."""
    print("🎥 Launching Gource visualization...")
    subprocess.run(
        [
            "gource",
            str(log_path),
            "--highlight-users",
            "--auto-skip-seconds",
            "1",
            "--seconds-per-day",
            "0.1",
            "--file-idle-time",
            "0",
            "--stop-at-end",
            "--title",
            "Repository + Submodules",
        ]
    )


def main():
    print(f"📁 Logs will be stored in {LOG_DIR}")
    logs = []

    # Main repo
    logs.append(generate_log(".", "."))

    # Initialize & list submodules
    # subprocess.run(["git", "submodule", "update", "--init", "--recursive"],
    #                check=False, stdout=subprocess.DEVNULL)
    for sub in get_submodules():
        if Path(sub, ".git").exists():
            logs.append(generate_log(sub, sub))
        else:
            print(f"⚠️  Skipping {sub} (no .git directory found)")

    combined = merge_logs()
    launch_gource(combined)
    print("✅ Visualization complete.")


if __name__ == "__main__":
    main()
