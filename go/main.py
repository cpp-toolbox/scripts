import subprocess
import os
import shlex
import re
from pathlib import Path
from fs_utils.main import *
import shutil

def get_python_command():
    """
    Returns the appropriate Python command: 'python3' if available,
    otherwise 'python' if available. Raises an error if neither is found.
    """
    if shutil.which("python3"):
        return "python3"
    elif shutil.which("python"):
        return "python"
    else:
        raise EnvironmentError("Neither 'python3' nor 'python' is available in PATH.")

python_command = get_python_command()

def run_command(command: str, check: bool = True, cwd: str = None):
    """
    Run a shell command with optional working directory and error checking.
    """
    print(f"Running: {command}")
    subprocess.run(shlex.split(command), check=check, cwd=cwd)

def run_command_capture_output(command: str, check: bool = True, cwd: str = None) -> str:
    """
    Run a command and return its output.
    """
    print(f"Running: {command}")
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
    find_package_lines = []
    target_link_lines = []
    
    for line in conan_output.splitlines():
        line = line.strip()
        if line.startswith("find_package("):
            find_package_lines.append(line)
        elif line.startswith("target_link_libraries("):
            # Replace placeholder with actual CMake project reference
            fixed_line = line.replace("target_link_libraries(...", "target_link_libraries(${PROJECT_NAME}")
            target_link_lines.append(fixed_line)

    return find_package_lines, target_link_lines

def update_cmake_lists(find_packages: list[str], target_links: list[str], cmake_path: str):
    """
    Replace or append find_package / target_link_libraries in CMakeLists.txt
    """
    with open(cmake_path, "r") as f:
        lines = f.readlines()

    def is_replacable(line):
        return line.strip().startswith("find_package(") or \
               line.strip().startswith("target_link_libraries(")

    new_lines = []
    for line in lines:
        if is_replacable(line):
            continue
        new_lines.append(line)

    if find_packages or target_links:
        new_lines.append("\n# Automatically generated from conan install\n")
    new_lines.extend(f"{line}\n" for line in find_packages)
    new_lines.extend(f"{line}\n" for line in target_links)

    with open(cmake_path, "w") as f:
        f.writelines(new_lines)

# -- Conan file check --

path_filter = make_regex_filter(["conanfile.txt"], [])
conan_file_mod_times_path = ".conanfile_last_modified.json"

previous_mod_times = load_last_mod_times(conan_file_mod_times_path)
current_mod_times = get_modification_times(".", path_filter)
modified_since_last_time = find_modified_files(previous_mod_times, current_mod_times)
save_mod_times(current_mod_times, conan_file_mod_times_path)

conanfile_had_updates = len(modified_since_last_time) == 1
build_folder_exists = os.path.exists("build")
need_to_run_conan_install = conanfile_had_updates or not build_folder_exists

if need_to_run_conan_install:
    print("RUNNING CONAN INSTALL")
    # Run Conan and patch CMakeLists.txt
    conan_output = run_command_capture_output("conan install . --build=missing")
    find_packages, target_links = extract_cmake_snippets(conan_output)
    update_cmake_lists(find_packages, target_links, "CMakeLists.txt")

    run_command("cmake --preset conan-release")
else:
    print("NOT RUNNING CONAN INSTALL")

# -- .cpp files check --

cpp_files_mod_times_path = ".cpp_files_last_modified.json"
cpp_file_filter = make_regex_filter([r"\.cpp$"], [])

previous_mod_times = load_last_mod_times(cpp_files_mod_times_path)
current_mod_times = get_modification_times("src", cpp_file_filter)
new_cpp_files = find_new_files(previous_mod_times, current_mod_times)
save_mod_times(current_mod_times, cpp_files_mod_times_path)

if new_cpp_files:
    print("NEW CPP FILES")
    run_command("cmake --preset conan-release")
else: 
    print("NO NEW CPP FILES")


# -- Shader batchers --

shader_batcher_files = find_all_instances_of_file_in_directory_recursively(".", ".required_shader_batchers.txt")
uses_shader_batchers = len(shader_batcher_files) >= 1

if uses_shader_batchers:
    print("SHADER BATCHERS FOUND")
    run_command(f"{python_command} scripts/setup/graphics_systems.py")
else:
    print("NO SHADER BATCHERS FOUND")

# -- Shader batch preprocessor tool --

run_command(f"{python_command} scripts/sbpt/main.py src")

# -- Final build step --

run_command("cmake --build --preset conan-release")

import stat

def find_single_executable(build_release_path: str) -> str | None:
    """
    Return the only executable file in the given directory, or None if not found or multiple exist.
    """
    executables = []

    for entry in os.scandir(build_release_path):
        if entry.is_file():
            mode = os.stat(entry.path).st_mode
            if mode & stat.S_IXUSR:  # Executable by owner
                executables.append(entry.path)

    if len(executables) == 1:
        return executables[0]
    elif len(executables) > 1:
        print("Multiple executables found in build/Release.")
    else:
        print("No executable found in build/Release.")

    return None

# -- Try to run the single executable --

exe_path = find_single_executable("build/Release")
if exe_path:
    run_command(exe_path)
