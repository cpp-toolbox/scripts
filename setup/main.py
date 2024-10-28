import os
import subprocess
import sys

def run_command(command):
    """Run a command in the shell and check if it succeeds."""
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error: Command '{command}' failed with return code {result.returncode}.")
        sys.exit(result.returncode)

def find_batcher(src_directory):
    """Recursively search for the 'batcher' directory within the given source directory."""
    for root, dirs, files in os.walk(src_directory):
        if 'batcher' in dirs:
            return os.path.join(root, 'batcher')
    return None

def main():
    # Step 1: Ensure the script is run from the root directory
    current_directory = os.getcwd()
    if not os.path.isdir(os.path.join(current_directory, 'scripts')):
        print("Error: This script must be run from the root directory of the project.")
        sys.exit(1)

    # Step 2: Initialize sbpt
    print("Initializing sbpt...")
    run_command("python3 scripts/sbpt/sbpt.py --init src")

    # Step 3: Recursively search for the 'batcher' directory in 'src'
    batcher_path = find_batcher('src')

    if batcher_path:
        requested_shaders_path = os.path.join('.', '.requested_shaders.txt')
        if not os.path.isfile(requested_shaders_path):
            print("Error: You're using the batcher but you don't have a '.requested_shaders.txt' in the root directory. Please create this and try again.")
            sys.exit(1)

        print("Running batcher.py with the provided config...")
        run_command(f"python3 {batcher_path}/batcher.py --config-file .requested_shaders.txt")
    else:
        print("Error: 'batcher' directory not found in 'src'.")
        sys.exit(1)

    # Step 4: Run conan install
    print("Running conan install...")
    run_command("conan install .")

    # Step 5: Run the build script
    print("Running build.py...")
    run_command("python scripts/build_notifier/build.py -t r -g")

    print("Setup completed successfully!")

if __name__ == "__main__":
    main()
