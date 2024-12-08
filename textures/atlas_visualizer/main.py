import os
import json
import cv2
import argparse
import numpy as np

def draw_atlas_visualization(image_path, json_data):
    """
    Draw rectangles from JSON data on the image and annotate with names.
    """
    image = cv2.imread(image_path)

    # Loop through the sub_textures and draw rectangles
    for key, rect in json_data['sub_textures'].items():
        x, y, width, height = rect['x'], rect['y'], rect['width'], rect['height']
        
        # Draw rectangle on the image (green color with thickness 2)
        cv2.rectangle(image, (int(x), int(y)), (int(x + width), int(y + height)), (0, 255, 0), 2)
        
        # Annotate with the key (name) of the rectangle
        cv2.putText(image, key, (int(x) + 8, int(y) + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
    
    return image

def process_directory(directory):
    """
    Recursively find JSON files and corresponding image files.
    """
    for root, dirs, files in os.walk(directory):
        json_files = [f for f in files if f.endswith('.json')]
        
        for json_file in json_files:
            json_path = os.path.join(root, json_file)
            image_path = os.path.splitext(json_path)[0] + '.png'  # Assuming PNG format for images
            
            # Check if corresponding image file exists
            if os.path.exists(image_path):
                print(f"Processing {json_file} with corresponding image {os.path.basename(image_path)}")

                # Read the JSON data
                with open(json_path, 'r') as f:
                    json_data = json.load(f)

                # Draw the atlas visualization
                result_image = draw_atlas_visualization(image_path, json_data)

                # Save the result
                output_path = os.path.splitext(json_path)[0] + '_atlas_visualization.png'
                cv2.imwrite(output_path, result_image)
                print(f"Saved visualization to {output_path}")
            else:
                print(f"Warning: Image file for {json_file} not found.")

def main():
    parser = argparse.ArgumentParser(description="Atlas Visualizer: Annotate images with rectangles from JSON files.")
    parser.add_argument('directory', type=str, help="The directory to search for JSON files and corresponding images.")
    args = parser.parse_args()
    
    process_directory(args.directory)

if __name__ == '__main__':
    main()
