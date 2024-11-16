import os
import subprocess
import sys
import shutil

from fs_utils.main import recursively_find_directory

def run_command(command):
    """Run a command in the shell and check if it succeeds."""
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error: Command '{command}' failed with return code {result.returncode}.")
        sys.exit(result.returncode)

def main():
    shader_standard_path = recursively_find_directory('src', 'shader_standard')
    batcher_path = recursively_find_directory('src', 'batcher')

    if batcher_path:
        if not shader_standard_path:
            print("Error: You're using the batcher but you don't have the shader standard submodule, please add this submodule first.")
            sys.exit(1)

        requested_shaders_path = os.path.join('.', '.requested_shaders.txt')
        if not os.path.isfile(requested_shaders_path):
            print("Error: You're using the batcher but you don't have a '.requested_shaders.txt' in the root directory. Please create this and try again.")
            sys.exit(1)

        # Step to run the main.py script from the shader_standard directory
        main_py_path = os.path.join(shader_standard_path, 'main.py')
        if os.path.isfile(main_py_path):
            print("Running main.py -gc -gp from the shader_standard directory...")
            run_command(f"python3 {main_py_path} -sd assets/shaders -gc -gp")
        else:
            print(f"Error: main.py not found in {shader_standard_path}.")
            sys.exit(1)

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
    else:
        print("'batcher' directory not found in 'src', make sure it exists before running")
        # sys.exit(1)

if __name__ == "__main__":
    main()
