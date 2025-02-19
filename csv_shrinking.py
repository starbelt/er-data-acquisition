import numpy as np
import argparse
import csv
import re
from collections import defaultdict

# Global variables
signal_freq = 140e3
default_chirp_bw = 750e6
ramp_time = 500      # ramp time in us
c = 3e8
ramp_time_s = ramp_time / 1e6
slope = default_chirp_bw / ramp_time_s


def freq_to_dist(freq):
    return (freq - signal_freq) * c / (2 * slope)

def dist_to_freq(dist):
    return (dist * 2 * slope / c) + signal_freq

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shrink CSV file to a specific distance range")
    parser.add_argument("min_dist_m", type=float, help="Minimum distance in meters")
    parser.add_argument("max_dist_m", type=float, help="Maximum distance in meters")
    parser.add_argument("csv_file", type=str, help="CSV file to shrink")
    args = parser.parse_args()
    min_dist = args.min_dist_m
    max_dist = args.max_dist_m
    csv_file = args.csv_file

    fft_size_match = re.search(r'fft_size_(\d+)', csv_file)
    sample_rate_match = re.search(r'sample_rate_([\d.]+)MHz', csv_file)

    if fft_size_match and sample_rate_match:
        fft_size = int(fft_size_match.group(1))
        sample_rate = float(sample_rate_match.group(1))
        sample_rate *= 1e6
        unique_name = ""
    else:
        fft_size = int(input("Enter fft_size: "))
        sample_rate = float(input("Enter sample_rate in MHz: "))
        sample_rate *= 1e6
        unique_name = "_" + csv_file.rstrip('.csv').split('/')[-1]

    freq = np.linspace((-sample_rate / 2)+.5, (sample_rate / 2)-.5, int(fft_size))
    upper_freq = dist_to_freq(max_dist)
    lower_freq = dist_to_freq(min_dist)

    # Read the CSV file and filter the data
    filtered_data = defaultdict(list)
    with open(csv_file, mode='r') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in reader:
            t_since_start = float(row[0])
            frequency = float(row[1])
            if lower_freq < frequency < upper_freq:
                filtered_data[t_since_start].append(row)

    # Get the count of values for the first time_since_start
    first_t_start = sorted(filtered_data.keys())[0]
    num_per_sample = len(filtered_data[first_t_start])
    num_samples = len(filtered_data.keys())
    
    # Write the filtered data to a new CSV file
    output_file = "DataExports/FilteredData/filtered_fft_" + str(fft_size) + "_sample_rate_" + str(sample_rate/1e6) + "MHz_Sample_Size_" + str(num_per_sample) + "_" + str(num_samples) + unique_name + ".csv"
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for time_since_start in sorted(filtered_data.keys()):
            for row in filtered_data[time_since_start]:
                writer.writerow(row)

    print(f"Filtered data written to {output_file}")
    