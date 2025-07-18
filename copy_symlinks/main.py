import os
import shutil

def parse_symlink_file(symlink_file_path):
    mappings = {}
    with open(symlink_file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if '->' not in line or line.startswith('#') or not line:
                continue
            src, dst = map(str.strip, line.split('->', 1))
            mappings.setdefault(src, []).append(dst)
    return mappings

def copy_and_clobber(src_dir, dst_dir):
    if os.path.exists(dst_dir):
        print(f"Clobbering existing directory: {dst_dir}")
        shutil.rmtree(dst_dir)
    print(f"Copying {src_dir} -> {dst_dir}")
    shutil.copytree(src_dir, dst_dir)

def main(source_root, symlink_file_path):
    mappings = parse_symlink_file(symlink_file_path)

    for subdir, target_paths in mappings.items():
        full_src_path = os.path.join(source_root, subdir)

        if not os.path.isdir(full_src_path):
            print(f"Warning: source directory does not exist: {full_src_path}")
            continue

        for target_path in target_paths:
            full_dst_path = os.path.abspath(target_path)
            copy_and_clobber(full_src_path, full_dst_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Copy and clobber directories based on symlink file.")
    parser.add_argument("source_root", help="Path to the source root directory")
    parser.add_argument("symlink_file", help="Path to the symlink definition file")
    args = parser.parse_args()

    main(args.source_root, args.symlink_file)
