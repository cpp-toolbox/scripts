import os
import shutil

src = "scripts/setup/github_workflow/build.yml"
dest_dir = ".github/workflows"
dest_file = os.path.join(dest_dir, "build.yml")

os.makedirs(dest_dir, exist_ok=True)

shutil.copy2(src, dest_file)

print(f"Copied {src} to {dest_file}")
