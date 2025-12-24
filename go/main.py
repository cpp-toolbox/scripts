import argparse
import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path
from fs_utils.main import (
    make_regex_filter,
    load_last_mod_times,
    get_modification_times,
    find_modified_files,
    find_new_files,
    save_mod_times,
    find_all_instances_of_file_in_directory_recursively,
)

from collection_utils.main import *


# os utils

import platform
from enum import Enum, auto


class OSType(Enum):
    WINDOWS = auto()
    LINUX = auto()
    MACOS = auto()
    UNKNOWN = auto()


def get_os_type() -> OSType:
    system = platform.system()

    if system == "Windows":
        return OSType.WINDOWS
    elif system == "Linux":
        return OSType.LINUX
    elif system == "Darwin":  # macOS reports as "Darwin"
        return OSType.MACOS
    else:
        return OSType.UNKNOWN


# ------------------------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------------------------


def get_python_command():
    """
    Returns 'python3' if available, else 'python', else raises an error.
    """
    if shutil.which("python3"):
        return "python3"
    elif shutil.which("python"):
        return "python"
    elif shutil.which("py"):
        return "py"
    else:
        raise EnvironmentError("Neither 'python3' nor 'python' is available in PATH.")


def run_command(command: str, check: bool = True, cwd: str | None = None):
    """Run a shell command with optional working directory and error checking."""
    print(f"➡️  Running: {command}")
    subprocess.run(shlex.split(command), check=check, cwd=cwd)


def run_command_capture_output(
    command: str, check: bool = True, cwd: str | None = None
) -> str:
    """Run a command and return its captured stdout."""
    print(f"➡️  Running: {command}")
    result = subprocess.run(
        shlex.split(command),
        check=check,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout


def extract_cmake_snippets(conan_output: str):
    """
    Extracts find_package() and target_link_libraries() lines from conan output.
    """
    find_package_lines = []
    target_link_lines = []

    for line in conan_output.splitlines():
        line = line.strip()
        if line.startswith("find_package("):
            find_package_lines.append(line)
        elif line.startswith("target_link_libraries("):
            fixed_line = line.replace(
                "target_link_libraries(...", "target_link_libraries(${PROJECT_NAME}"
            )
            target_link_lines.append(fixed_line)

    return find_package_lines, target_link_lines


def update_cmake_lists(
    find_packages: list[str], target_links: list[str], cmake_path: str
):
    """
    Rewrites or appends find_package/target_link_libraries blocks in CMakeLists.txt
    """
    with open(cmake_path, "r") as f:
        lines = f.readlines()

    def is_replacable(line):
        return line.strip().startswith("find_package(") or line.strip().startswith(
            "target_link_libraries("
        )

    new_lines = [line for line in lines if not is_replacable(line)]

    if find_packages or target_links:
        new_lines.append("\n# Automatically generated from conan install\n")
    new_lines.extend(f"{line}\n" for line in find_packages)
    new_lines.extend(f"{line}\n" for line in target_links)

    with open(cmake_path, "w") as f:
        f.writelines(new_lines)


def find_single_executable(build_release_path: str) -> str | None:
    """
    Return the only executable in the directory, or None if not found/multiple exist.
    """
    executables = []
    for entry in os.scandir(build_release_path):
        if entry.is_file() and os.stat(entry.path).st_mode & stat.S_IXUSR:
            executables.append(entry.path)

    if len(executables) == 1:
        return executables[0]
    elif len(executables) > 1:
        print(" Multiple executables found in build/Release.")
    else:
        print(" No executable found in build/Release.")
    return None


# ------------------------------------------------------------------------------
# Build Planner
# ------------------------------------------------------------------------------


def plan_build_actions() -> list[str]:
    """
    Inspect the project and decide what steps are necessary.
    Returns a list of shell commands to be executed.
    """
    python_command = get_python_command()
    planned_steps: list[str] = []

    # -- shader tools always first --------------------------------------------
    shader_batcher_files = find_all_instances_of_file_in_directory_recursively(
        ".", ".required_shader_batchers.txt"
    )
    uses_shader_batchers = len(shader_batcher_files) >= 1

    # determine if shader batchers or shader sources changed
    shader_batcher_mod_times_path = ".shader_batcher_last_modified.json"

    previous_mod_times = load_last_mod_times(shader_batcher_mod_times_path)
    current_mod_times = get_modification_times("assets/shaders/src")
    modified_since_last_time = find_modified_files(
        previous_mod_times, current_mod_times
    )
    save_mod_times(current_mod_times, shader_batcher_mod_times_path)

    shader_batcher_needs_run = (
        uses_shader_batchers and len(modified_since_last_time) > 0
    )
    if shader_batcher_needs_run:
        planned_steps.append(f"{python_command} scripts/setup/graphics_systems.py")

    planned_steps.append(f"{python_command} scripts/sbpt/main.py init src")

    path_filter = make_regex_filter(["conanfile.txt"], [])
    conan_file_mod_times_path = ".conanfile_last_modified.json"

    previous_mod_times = load_last_mod_times(conan_file_mod_times_path)
    current_mod_times = get_modification_times(".", path_filter)
    modified_since_last_time = find_modified_files(
        previous_mod_times, current_mod_times
    )
    save_mod_times(current_mod_times, conan_file_mod_times_path)

    conanfile_had_updates = len(modified_since_last_time) == 1
    build_folder_exists = os.path.exists("build")
    need_to_run_conan_install = conanfile_had_updates or not build_folder_exists

    os_type = get_os_type()
    cmake_preset_command = ""

    if os_type == OSType.WINDOWS:
        cmake_preset_command = "cmake --preset conan-default"
    elif os_type == OSType.LINUX:
        cmake_preset_command = "cmake --preset conan-release"

    if need_to_run_conan_install:
        planned_steps.append("conan install . --build=missing")
        planned_steps.append(cmake_preset_command)

    # -- .cpp file changes -----------------------------------------------------
    cpp_files_mod_times_path = ".cpp_files_last_modified.json"
    cpp_file_filter = make_regex_filter([r"\.cpp$"], [])

    previous_mod_times = load_last_mod_times(cpp_files_mod_times_path)
    previous_files = previous_mod_times.keys()
    current_mod_times = get_modification_times("src", cpp_file_filter)
    current_files = current_mod_times.keys()
    new_cpp_files = find_new_files(previous_files, current_files)
    save_mod_times(current_mod_times, cpp_files_mod_times_path)

    if new_cpp_files and cmake_preset_command not in planned_steps:
        planned_steps.append(cmake_preset_command)

    # -- Final build -----------------------------------------------------------
    planned_steps.append("cmake --build --preset conan-release")

    return planned_steps


# ------------------------------------------------------------------------------
# CLI Entrypoint
# ------------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Smart project build orchestrator.")
    parser.add_argument(
        "--run", action="store_true", help="Run the built executable after build."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Run without asking for confirmation."
    )
    args = parser.parse_args()

    print("🔍 Determining what needs to be done...")
    planned_steps = plan_build_actions()

    if not planned_steps:
        print(" Nothing to do. Everything is up to date.")
        return

    print("\n Planned steps:")
    for i, step in enumerate(planned_steps, 1):
        print(f"  {i}. {step}")

    if not args.yes:
        proceed = input("\nProceed with these steps? [y/N] ").strip().lower()
        if proceed not in ("y", "yes"):
            print(" Aborted.")
            return

    print("\n Executing build plan...\n")
    for step in planned_steps:
        if step.startswith("conan install"):
            conan_output = run_command_capture_output(step)
            find_packages, target_links = extract_cmake_snippets(conan_output)
            update_cmake_lists(find_packages, target_links, "CMakeLists.txt")
        else:
            run_command(step)

    if args.run:
        exe_path = find_single_executable("build/Release")
        if exe_path:
            print(f"\n  Running built executable: {exe_path}\n")
            run_command(exe_path)


if __name__ == "__main__":
    main()
