import os
import argparse
import re

from text_utils.main import *


def sanitize_enum_name(filename):
    """
    Convert a filename to an uppercase, enum-friendly name.

    - Removes the file extension
    - Replaces separators with underscores
    - Converts a leading numeric prefix into words
    - Ensures only alphanumeric characters and underscores remain
    """

    name = os.path.splitext(filename)[0]

    # normalize separators early
    name = name.replace("-", "_").replace(" ", "_")

    # detect leading number (e.g. "123_test")
    match = re.match(r"^(\d+)(.*)", name)
    if match:
        number_part = int(match.group(1))
        rest = match.group(2)

        number_words = number_to_words(number_part)
        number_words = number_words.replace("-", "_").replace(" ", "_")

        name = f"{number_words}{rest}"

    # sanitize remaining characters
    name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)

    return name.upper()


def generate_sound_enum_and_map(audio_dir, relative_to):
    entries = []

    # walk recursively and collect audio files
    for root, dirs, files in os.walk(audio_dir):
        for file in files:
            if file.lower().endswith((".wav", ".mp3", ".ogg")):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, relative_to).replace("\\", "/")
                enum_name = sanitize_enum_name(file)
                entries.append((root, file, enum_name, rel_path))

    # sort by folder path then filename
    entries.sort(key=lambda e: (e[0].lower(), e[1].lower()))

    # generate enum and map code
    enum_entries = [e[2] for e in entries]
    map_entries = [f'    {{SoundType::{e[2]}, "{e[3]}"}}' for e in entries]

    enum_code = (
        "enum class SoundType {\n"
        + ",\n".join(f"    {e}" for e in enum_entries)
        + "\n};\n"
    )
    map_code = (
        "std::unordered_map<SoundType, std::string> sound_type_to_file = {\n"
        + ",\n".join(map_entries)
        + "\n};\n"
    )

    return enum_code, map_code


def main():
    parser = argparse.ArgumentParser(
        description="Generate C++ enum and map for audio files."
    )
    parser.add_argument("audio_dir", help="Directory containing audio files")
    parser.add_argument("relative_to", help="Base path to generate relative paths")
    args = parser.parse_args()

    enum_code, map_code = generate_sound_enum_and_map(args.audio_dir, args.relative_to)

    print("// Generated code, paste directly into C++ source\n")
    print("#include <unordered_map>\n#include <string>\n")
    print(enum_code)
    print(map_code)


if __name__ == "__main__":
    main()
