import os
import pandas as pd
import glob
import re
from collections import defaultdict

def group_images_by_timestamp(image_dir):
    """Group images by their timestamp prefix (export session)"""
    image_files = glob.glob(os.path.join(image_dir, "*.png"))
    
    # Group images by timestamp
    grouped = defaultdict(list)
    
    for img_path in image_files:
        img_basename = os.path.basename(img_path)
        # Extract timestamp (format: mmdd-hhmmss)
        match = re.match(r'(\d{4}-\d{6})_', img_basename)
        if match:
            timestamp = match.group(1)
            grouped[timestamp].append(img_path)
    
    # Sort images within each group by image number
    for timestamp, imgs in grouped.items():
        grouped[timestamp] = sorted(imgs, key=lambda x: int(re.search(r'_img(\d+)\.png$', x).group(1)))
    
    return grouped

def find_matching_csv(csv_dir, timestamp):
    """Find the CSV file matching a timestamp"""
    pattern = os.path.join(csv_dir, f"{timestamp}_*.csv")
    matches = glob.glob(pattern)
    return matches[0] if matches else None

def split_csv_for_images(csv_path, image_paths, output_dir):
    """Split a CSV file based on the corresponding images"""
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Get all unique time samples in chronological order
    time_samples = sorted(df['Time Since Start (s)'].unique())
    
    # Calculate img_size based on number of images and time samples
    num_images = len(image_paths)
    img_size = (len(time_samples) - 1) // num_images  # The -1 accounts for skipping first sample
    
    print(f"CSV has {len(time_samples)} time samples, splitting into {num_images} images with {img_size} samples each")
    
    # For each image, create a corresponding CSV
    for img_idx, img_path in enumerate(image_paths):
        img_basename = os.path.basename(img_path)
        
        # Calculate time indices for this image, exactly matching original code's logic
        start_idx = 1 + img_idx * img_size  # Skip first sample, same as in original code
        end_idx = start_idx + img_size
        
        if end_idx > len(time_samples):
            print(f"Warning: Not enough time samples for image {img_idx+1}")
            continue
        
        # Get time range for this image
        img_times = time_samples[start_idx:end_idx]
        
        # Filter data for these times
        img_df = df[df['Time Since Start (s)'].isin(img_times)]
        
        # Create output filename matching the image
        output_basename = img_basename.replace('.png', '.csv')
        output_path = os.path.join(output_dir, output_basename)
        
        # Save the CSV
        img_df.to_csv(output_path, index=False)
        print(f"Created {output_path}")

def process_class(class_dir):
    """Process all CSVs for a class (range bucket)"""
    csv_dir = os.path.join(class_dir, "CSV")
    image_dir = os.path.join(class_dir, "Images")
    output_dir = os.path.join(class_dir, "FilteredCSV")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Group images by timestamp (identifies separate export sessions)
    grouped_images = group_images_by_timestamp(image_dir)
    
    if not grouped_images:
        print(f"No images found in {image_dir}")
        return
    
    num_img_values = [len(imgs) for imgs in grouped_images.values()]
    if num_img_values:
        print(f"Found {len(grouped_images)} export sessions")
        print(f"Number of images per export: {num_img_values[0]}")
    
    # Process each group of images (each export session)
    for timestamp, images in grouped_images.items():
        # Find matching CSV
        csv_path = find_matching_csv(csv_dir, timestamp)
        
        if csv_path:
            print(f"Processing {len(images)} images for timestamp {timestamp}")
            split_csv_for_images(csv_path, images, output_dir)
        else:
            print(f"No matching CSV found for timestamp {timestamp}")

def main():
    # Get the class directory from user
    class_name = input("Enter the class name (range bucket): ")
    class_dir = os.path.join("DataSet", class_name)
    
    if not os.path.isdir(class_dir):
        print(f"Class directory not found: {class_dir}")
        return
    
    process_class(class_dir)

if __name__ == "__main__":
    main()