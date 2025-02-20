import numpy as np
import argparse
import csv
import re
from collections import defaultdict
import cv2

# Global variables
signal_freq = 100e3
default_chirp_bw = 750e6
ramp_time = 500      # ramp time in us
c = 3e8
ramp_time_s = ramp_time / 1e6
slope = default_chirp_bw / ramp_time_s

export_location = "DataExports/csvToImage/Images"

magnitude_min = -100
magnitude_max = 0

def dist_to_freq(dist):
    return (dist * 2 * slope / c) + signal_freq

def downsample(data, target_size):
    factor = len(data) // target_size
    downsampled_data = np.mean(np.reshape(data[:factor * target_size], (-1, factor)), axis=1)
    return downsampled_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shrink CSV file to a specific distance range")
    parser.add_argument("csv_file", type=str, help="CSV file to shrink")
    args = parser.parse_args()
    csv_file = args.csv_file
    
    # Extract the date and time from the csv_file name
    match1 = re.search(r"filtered_cfar_data_(.*?)_fft_size", csv_file)
    match2 = re.search(r"fft_size_(.*?)_sample_rate", csv_file)
    if match1 and match2:
        date_time_str = match1.group(1)
        distance = match2.group(1)
    else:
        raise ValueError("CSV file name does not match the expected pattern")
    
    file_name = f"{export_location}/{distance}_m_{date_time_str}.png"
    
    # Read the CSV file and filter the data
    filtered_data = defaultdict(list)
    with open(csv_file, mode='r') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in reader:
            t_since_start = float(row[0])
            frequency = float(row[1])
            magnitude = float(row[2])
            # Shift the magnitude to be between 0 and 225
            shifted_magnitude = (magnitude - magnitude_min) / (magnitude_max - magnitude_min) * 225
            filtered_data[t_since_start].append(shifted_magnitude)

    # Get the count of values for the first time_since_start
    first_t_start = sorted(filtered_data.keys())[0]
    num_per_sample = len(filtered_data[first_t_start])
    num_samples = len(filtered_data.keys())

    # Ensure num_samples is at least 225
    if num_samples < 225:
        raise ValueError("Number of samples is less than 225")

    # Downsample frequencies to 224
    downsampled_data = []
    for t in sorted(filtered_data.keys())[1:225]:  # Skip the first time sample
        downsampled_data.append(downsample(filtered_data[t], 224))

    # Convert to numpy array for image creation
    downsampled_data = np.array(downsampled_data).T
    downsampled_data = np.flipud(downsampled_data)

    # Normalize the data to the range 0-255 for image representation
    normalized_data = cv2.normalize(downsampled_data, None, 0, 255, cv2.NORM_MINMAX)

    # Convert to uint8
    image_data = normalized_data.astype(np.uint8)

    # Apply a color map
    colored_image = cv2.applyColorMap(image_data, cv2.COLORMAP_VIRIDIS)

    # Save the image
    cv2.imwrite(file_name, colored_image)

    # Display the image
    # cv2.imshow('Radar Waterfall Plot', colored_image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()