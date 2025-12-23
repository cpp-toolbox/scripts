import os
import argparse
from PIL import Image

dimension_mappings = {}


def resize_image(image_path, new_width, new_height):
    with Image.open(image_path) as img:
        resized_img = img.resize((new_width, new_height))
        resized_img.save(image_path)
        print(f"Saved resized image: {image_path} ({new_width}x{new_height})")


def get_images(directory):
    supported_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(supported_extensions):
                yield os.path.join(root, file)


def prompt_new_dimensions(orig_width, orig_height):
    while True:
        dims = input(
            f"Enter new dimensions for {orig_width}x{orig_height} (format: width height), or skip (s): "
        ).strip()
        if dims.lower() == "s":
            return None
        try:
            width, height = map(int, dims.split())
            return width, height
        except:
            print(
                "Invalid input. Please enter two integers separated by space or 's' to skip."
            )


def main():
    parser = argparse.ArgumentParser(
        description="Interactively resize images in a directory."
    )
    parser.add_argument("directory", help="Target directory containing images")
    args = parser.parse_args()
    target_dir = args.directory

    if not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory.")
        return

    for image_path in get_images(target_dir):
        with Image.open(image_path) as img:
            orig_width, orig_height = img.size

        key = (orig_width, orig_height)
        if key in dimension_mappings:
            prev_new = dimension_mappings[key]
            use_prev = (
                input(
                    f"{image_path} ({orig_width}x{orig_height}) has a previous mapping to {prev_new[0]}x{prev_new[1]}. Use it? (y/n): "
                )
                .strip()
                .lower()
            )
            if use_prev == "y":
                resize_image(image_path, prev_new[0], prev_new[1])
                continue

        new_dims = prompt_new_dimensions(orig_width, orig_height)
        if new_dims:
            width, height = new_dims
            dimension_mappings[key] = (width, height)
            resize_image(image_path, width, height)
        else:
            print(f"Skipped {image_path}")


if __name__ == "__main__":
    main()
