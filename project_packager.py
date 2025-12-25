import os
import sys
import shutil
import zipfile
import subprocess
import platform
import argparse
from pathlib import Path


def is_executable(file_path: Path) -> bool:
    """Return True if a file is likely an executable."""
    if not file_path.is_file():
        return False
    if platform.system() == "Windows":
        return file_path.suffix.lower() == ".exe"
    else:
        # On Unix-like systems, check for execute permission
        return os.access(file_path, os.X_OK) and not file_path.suffix


def get_git_info():
    """Return (branch_name, short_commit_hash), or ('unknown', 'unknown') if not a git repo."""
    try:
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode("utf-8")
            .strip()
        )
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode("utf-8")
            .strip()
        )
        # sanitize branch for filenames
        branch = branch.replace("/", "_")
        return branch, commit
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "unknown"


def package_project(custom_build_dir: str | None = None):
    project_dir = Path.cwd()
    project_name = project_dir.name
    default_build_dir = f"{project_name}_build"

    # Determine build directory
    build_dir = Path(custom_build_dir) if custom_build_dir else Path(default_build_dir)

    # Get Git branch and commit
    branch, commit = get_git_info()

    # base OS name
    system = platform.system().lower()
    if system == "darwin":
        os_name = "macos"
    elif system == "windows":
        os_name = "windows"
    elif system == "linux":
        os_name = "linux"
    else:
        os_name = system  # fallback

    # architecture
    arch = platform.machine().lower()

    # normalize macOS arch to intel/silicon
    if os_name == "macos":
        if arch == "x86_64":
            arch_name = "intel"
        elif arch == "arm64":
            arch_name = "silicon"
        else:
            arch_name = arch
    else:
        arch_name = arch  # leave as-is for Windows/Linux

    os_name = f"{os_name}_{arch_name}"

    suffix_parts = []
    if branch != "unknown" and commit != "unknown":
        suffix_parts.append(f"{branch}_{commit}")
    if os_name:
        suffix_parts.append(os_name)

    suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""
    zip_file = Path(f"{build_dir}{suffix}.zip")

    # Cleanup previous runs
    if build_dir.exists():
        print(f"Removing old build directory: {build_dir}")
        shutil.rmtree(build_dir)
    if zip_file.exists():
        print(f"Removing old zip file: {zip_file}")
        zip_file.unlink()

    print(f"Creating build directory: {build_dir}")
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy assets folder
    assets_src = project_dir / "assets"
    if assets_src.exists():
        print(f"Copying assets → {build_dir / 'assets'}")
        shutil.copytree(assets_src, build_dir / "assets")
    else:
        print("Warning: 'assets' folder not found, skipping.")

    # Find executables in build/Release
    release_dir = project_dir / "build" / "Release"
    if not release_dir.exists():
        print(f"Error: Release directory not found: {release_dir}")
        return

    exe_candidates = [f for f in release_dir.iterdir() if is_executable(f)]
    if not exe_candidates:
        print("Error: No executable found in build/Release")
        return

    # Choose executable (prompt if multiple)
    exe_file = exe_candidates[0]
    if len(exe_candidates) > 1:
        print("\nMultiple executables found:")
        for i, f in enumerate(exe_candidates, start=1):
            print(f"{i}. {f.name}")
        choice = input("Select which to package [1]: ").strip()
        index = (
            int(choice) - 1
            if choice.isdigit() and 1 <= int(choice) <= len(exe_candidates)
            else 0
        )
        exe_file = exe_candidates[index]

    print(f"Found executable: {exe_file.name}")
    shutil.copy2(exe_file, build_dir / exe_file.name)

    # Write commit info inside build dir
    commit_file = build_dir / "commit.txt"
    commit_file.write_text(
        f"Branch: {branch}\nCommit: {commit}\nOS: {os_name}\n", encoding="utf-8"
    )
    print(f"Embedded git info: {branch} @ {commit} on {os_name}")

    # Zip it up
    print(f"Creating zip archive: {zip_file}")
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(build_dir):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(build_dir.parent))

    print(f"\nPackaging complete: {zip_file}")
    if branch != "unknown":
        print(f"Git baked in: {branch} @ {commit} on {os_name}")


def clean_project():
    """Remove generated build directories and zip files."""
    project_dir = Path.cwd()
    project_name = project_dir.name
    build_prefix = f"{project_name}_build"

    deleted = False
    for path in project_dir.iterdir():
        if path.is_dir() and path.name.startswith(build_prefix):
            print(f"Removing directory: {path}")
            shutil.rmtree(path)
            deleted = True
        elif (
            path.is_file()
            and path.name.startswith(build_prefix)
            and path.suffix == ".zip"
        ):
            print(f"Removing file: {path}")
            path.unlink()
            deleted = True

    if not deleted:
        print("Nothing to clean.")
    else:
        print("Cleanup complete.")


def find_zip():
    """Return the first zip file in the current directory, or None if none exists."""
    zip_files = list(Path(".").glob("*.zip"))
    if zip_files:
        return zip_files[0].name
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Project Packager — package your build output with git metadata."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # package command
    package_parser = subparsers.add_parser(
        "package", help="Create a packaged zip of your project."
    )
    package_parser.add_argument(
        "-d", "--dir", type=str, default=None, help="Custom build directory name."
    )

    # clean command
    clean_parser = subparsers.add_parser(
        "clean", help="Remove build directories and zip files."
    )

    package_parser = subparsers.add_parser(
        "gha_zip_file_name", help="get the zip file in github actions format"
    )

    args = parser.parse_args()

    if args.command == "package":
        package_project(args.dir)
    elif args.command == "clean":
        clean_project()
    elif args.command == "find":
        zip_file = find_zip()
        if zip_file:
            # github actions expects name=value format
            print(f"zip_file={zip_file}")
        else:
            print("No zip file found", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
