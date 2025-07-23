from fs_utils.main import *
from user_input.main import *
from text_utils.main import *
from collection_utils.main import *
from func_utils.main import *
import subprocess
import sys
import shlex

base_directory = "scripts"
pattern = r".*\.(py|sh)$"
max_depth = 1

matched_files = find_files_matching_regex(base_directory, pattern, max_depth)

def clean_file_path(path: str) -> str:
    # Removes first path component (e.g., "scripts/")
    path = strip_first_path_component(path)
    # Remove "main.py" ending if it doesn't add useful info
    if path_ends_with_filename(path, "main.py"):
        path = strip_last_path_component(path)
    return path

assert not has_collisions(clean_file_path, matched_files)

clean_fp_to_og_fp = {clean_file_path(fp): fp for fp in matched_files}
matched_files = [clean_file_path(f) for f in matched_files]
file_abbreviations = map_words_to_abbreviations(matched_files)
abbreviation_to_clean_path = invert_dict(file_abbreviations)
assert abbreviation_to_clean_path

abbreviation_to_og_path = {
    abbr: clean_fp_to_og_fp[clean_path]
    for abbr, clean_path in abbreviation_to_clean_path.items()
}

# Run loop
while True:
    selected_path = select_options_from_dict(abbreviation_to_og_path, True)[0]

    # Ask for arguments
    args_input = input(f"Enter arguments for '{selected_path}' (or press Enter for none): ")
    args_list = shlex.split(args_input.strip()) if args_input.strip() else []

    # Build the command
    if selected_path.endswith(".py"):
        cmd = [sys.executable, selected_path] + args_list
    elif selected_path.endswith(".sh"):
        cmd = ["bash", selected_path] + args_list
    else:
        print(f"Unknown file type: {selected_path}")
        continue

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)
