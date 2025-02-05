import os
import subprocess
import sys
import shutil
import argparse

from fs_utils.main import recursively_find_directory

def run_command(command):
    """Run a command in the shell and check if it succeeds."""
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error: Command '{command}' failed with return code {result.returncode}.")
        sys.exit(result.returncode)

def setup_shader_standard(shader_standard_path: str):
    """Set up the shader standard by running its main.py script."""
    main_py_path = os.path.join(shader_standard_path, 'main.py')
    if os.path.isfile(main_py_path):
        print("Running main.py -gc -gp from the shader_standard directory...")
        run_command(f"python3 {main_py_path} -sd assets/shaders -gc -gp")
    else:
        print(f"Error: main.py not found in {shader_standard_path}.")
        sys.exit(1)

def setup_batcher(shader_standard_path: str, batcher_path: str):
    """Set up the batcher by copying shaders and running batcher.py."""
    requested_shaders_path = os.path.join('.', '.requested_shaders.txt')
    if not os.path.isfile(requested_shaders_path):
        print("Error: You're using the batcher but you don't have a '.requested_shaders.txt' in the root directory. Please create this and try again.")
        sys.exit(1)

    setup_shader_standard(shader_standard_path)

    # Paths to the original files
    shader_file = os.path.join(shader_standard_path, 'standard.py')
    shader_summary_file = os.path.join(shader_standard_path, 'shader_summary.py')

    # Calculate relative paths for copying
    dest_shader_path = os.path.join(batcher_path, 'standard.py')
    dest_shader_summary_path = os.path.join(batcher_path, 'shader_summary.py')

    try:
        # Copy files, overwriting if they exist
        if os.path.exists(dest_shader_path):
            os.remove(dest_shader_path)

        shutil.copy2(shader_file, dest_shader_path)

        if os.path.exists(dest_shader_summary_path):
            os.remove(dest_shader_summary_path)

        shutil.copy2(shader_summary_file, dest_shader_summary_path)

        print("Files copied and overwritten for standard.py and shader_summary.py in the batcher directory.")
    except FileExistsError:
        print("Warning: Symbolic links already exist in the batcher directory.")
    except Exception as e:
        print(f"Error creating symbolic links: {e}")
        sys.exit(1)

    # Run the batcher.py script after generating and symlinking
    print("Running batcher.py with the provided config...")
    run_command(f"python3 {batcher_path}/main.py --config-file .requested_shaders.txt")

def compile_shaders():
    """Compile shaders using the shader compilation script."""
    shader_main_path = os.path.join("assets", "shaders", "main.py")
    shader_src_dir = os.path.join("assets", "shaders", "src")
    shader_out_dir = os.path.join("assets", "shaders", "out")  # Just for reference, not created

    if not os.path.isfile(shader_main_path):
        print(f"Error: Shader compilation script '{shader_main_path}' not found.")
        sys.exit(1)

    if not os.path.isdir(shader_src_dir):
        print(f"Error: Shader source directory '{shader_src_dir}' not found.")
        sys.exit(1)

    print(f"Compiling shaders: {shader_main_path} {shader_src_dir} {shader_out_dir}...")
    run_command(f"python3 {shader_main_path} {shader_src_dir} {shader_out_dir}")
    print("Shaders compiled successfully.")

def main():
    parser = argparse.ArgumentParser(description="Setup graphics systems for shaders and batchers.")
    parser.add_argument(
        "--setup",
        choices=["batcher", "shader-cache", "compile-shaders"],
        help="Specify whether to setup 'batcher', 'shader-cache', or 'compile-shaders'. If not specified, all will run in sequence.",
    )
    args = parser.parse_args()

    shader_standard_path = recursively_find_directory('src', 'shader_standard')
    if not shader_standard_path and (args.setup in ["batcher", "shader-cache"] or args.setup is None):
        print("Error: You're using the batcher but you don't have the shader standard submodule, please add this submodule first.")
        sys.exit(1)

    if args.setup == "batcher":
        batcher_path = recursively_find_directory('src', 'batcher')
        if batcher_path:
            setup_batcher(shader_standard_path, batcher_path)
        else:
            print("'batcher' directory not found in 'src', make sure it exists before running.")
            sys.exit(1)
    elif args.setup == "shader-cache":
        setup_shader_standard(shader_standard_path)
    elif args.setup == "compile-shaders":
        compile_shaders()
    else:
        # Run all in sequence
        compile_shaders()
        setup_shader_standard(shader_standard_path)
        batcher_path = recursively_find_directory('src', 'batcher')
        if batcher_path:
            setup_batcher(shader_standard_path, batcher_path)
        else:
            print("'batcher' directory not found in 'src', make sure it exists before running.")
            sys.exit(1)

if __name__ == "__main__":
    main()
