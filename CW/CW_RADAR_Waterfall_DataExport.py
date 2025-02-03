# CW_RADAR_Waterfall_DataExport.py
#
# Usage: python3 CW_RADAR_Waterfall_DataExport.py
#  
# Description:
#     Initializes the SDR and Phaser devices.
#     Configures the devices for CW radar signal acquisition.
#     Sets up the Raspberry Pi GPIO states.
#     Configures the SDR for both Rx and Tx operations.
#     Creates a sinewave waveform for transmission.
#     Continuously updates the FFT and waterfall plots with the received data.
# Output:
#     This script initializes and configures a Software Defined Radio (SDR) and a Phaser device to perform Continuous Wave (CW) radar signal acquisition. 
#     It displays an interactive FFT and waterfall plot of the received signal using PyQt5 and pyqtgraph.
#
# Written by Nathan Griffin
# Derived from CW_RADAR_Waterfall.py by Jon Kraft
# Other contributors: Github Copilot
#
# See the LICENSE file for the license.

#type: ignore

# Imports
import adi

import sys
import os
import time
import datetime
import matplotlib.pyplot as plt
import numpy as np
import csv  # Add CSV import

# Instantiate all the Devices
rpi_ip = "ip:phaser.local"  # IP address of the Raspberry Pi
sdr_ip = "ip:192.168.2.1"  # IP address of the Transceiver Block 192.168.2.1 or pluto.local
my_sdr = adi.ad9361(uri=sdr_ip)  # Initialize SDR
my_phaser = adi.CN0566(uri=rpi_ip, sdr=my_sdr)  # Initialize Phaser

# Time start for log exports
start_time = datetime.datetime.now()  # Get start time

# Initialize both ADAR1000s, set gains to max, and all phases to 0
my_phaser.configure(device_mode="rx")  # Configure Phaser in Rx mode
my_phaser.load_gain_cal()  # Load gain calibration
my_phaser.load_phase_cal()  # Load phase calibration
for i in range(0, 8):
    my_phaser.set_chan_phase(i, 0)  # Set phase to 0 for all channels

gain_list = [8, 34, 84, 127, 127, 84, 34, 8]  # Blackman taper
for i in range(0, len(gain_list)):
    my_phaser.set_chan_gain(i, gain_list[i], apply_cal=True)  # Set gain for all channels

# Setup Raspberry Pi GPIO states
try:
    my_phaser._gpios.gpio_tx_sw = 0  # Set TX switch (0 = TX_OUT_2, 1 = TX_OUT_1)
    my_phaser._gpios.gpio_vctrl_1 = 1  # 1 = Use onboard PLL/LO source 0 = disable PLL and VCO, and set switch to use external LO input
    my_phaser._gpios.gpio_vctrl_2 = 1  # 1 = Send LO to transmit circuitry, 0 = disable Tx path, and send LO to LO_OUT
except:
    my_phaser.gpios.gpio_tx_sw = 0  # Set TX switch (0 = TX_OUT_2, 1 = TX_OUT_1)
    my_phaser.gpios.gpio_vctrl_1 = 1  # 1= Use onboard PLL/LO source 0 = disable PLL and VCO, and set switch to use external LO input
    my_phaser.gpios.gpio_vctrl_2 = 1  # 1 = Send LO to transmit circuitry 0 = disable Tx path, and send LO to LO_OUT

sample_rate = 0.6e6  # Increased sample rate
center_freq = 2.2e9  # Center frequency
signal_freq = 100e3  # Signal frequency
num_slices = 50  # Number of slices for waterfall plot
fft_size = 1024 * 64  # FFT size
img_array = np.ones((num_slices, fft_size)) * (-100)  # Initialize image array

# Configure SDR Rx
my_sdr.sample_rate = int(sample_rate)  # Set sample rate 
my_sdr.rx_lo = int(center_freq)  # Set Rx LO frequency (set this to output_freq - the freq of the HB100)
my_sdr.rx_enabled_channels = [0, 1]  # Enable Rx channels (Rx1 (voltage0), Rx2 (voltage1))
my_sdr.rx_buffer_size = int(fft_size)  # Set Rx buffer size
my_sdr.gain_control_mode_chan0 = "manual"  # Set gain control mode for channel 0 (manual or slow_attack)
my_sdr.gain_control_mode_chan1 = "manual"  # Set gain control mode for channel 1 (manual or slow_attack)
my_sdr.rx_hardwaregain_chan0 = int(30)  # Set hardware gain for channel 0 (rage of -3 to 70)
my_sdr.rx_hardwaregain_chan1 = int(30)  # Set hardware gain for channel 1 (rage of -3 to 70)

# Configure SDR Tx
my_sdr.tx_lo = int(center_freq)  # Set Tx LO frequency 
my_sdr.tx_enabled_channels = [0, 1]  # Enable Tx channels
my_sdr.tx_cyclic_buffer = True  # Enable cyclic buffer (must set true for the tdd burst mode, otherwise Tx will turn on and off randomly)
my_sdr.tx_hardwaregain_chan0 = -88  # Set hardware gain for Tx channel 0 (0 to -88)
my_sdr.tx_hardwaregain_chan1 = -0  # Set hardware gain for Tx channel 1 (0 to -88)

# Configure the ADF4159 Rampling PLL
output_freq = 12.2e9  # Output frequency 
my_phaser.frequency = int(output_freq / 4)  # Set output frequency divided by 4
my_phaser.ramp_mode = "disabled"  # options: "diabled", "continuous_sawtooth", "continuous_triangular", "single_sawtooth_burst", "single_ramp_burst"
my_phaser.enable = 0  # 0 = Enable PLL

# Create a sinewave waveform
fs = int(my_sdr.sample_rate)  # Sample rate
N = int(my_sdr.rx_buffer_size)  # Buffer size
fc = int(signal_freq / (fs / N)) * (fs / N)  # Calculate frequency
ts = 1 / float(fs)  # Time step
t = np.arange(0, N * ts, ts)  # Time array
i = np.cos(2 * np.pi * t * fc) * 2 ** 14  # I component
q = np.sin(2 * np.pi * t * fc) * 2 ** 14  # Q component
iq = 1 * (i + 1j * q)  # IQ data

# Send data
my_sdr._ctx.set_timeout(0)  # Set timeout
my_sdr.tx([iq * 0.5, iq])  # Transmit data (only to 2nd channel since that's all we need)

c = 3e8  # Speed of light
N_frame = fft_size  # Frame size
freq = np.linspace(-fs / 2, fs / 2, int(N_frame))  # Frequency array

index = 0  # Initialize index

def export_raw_data_to_csv(data):
    """ Exports the received data to a CSV file
    Args:
        data (np.array): The data to export
    Returns:
        None
    """
    current_time = datetime.datetime.now()  # Get current time
    time_since_start = (current_time - start_time).total_seconds()  # Calculate time since start in seconds
    filename = "raw_data_" + str(start_time) + ".csv"  # Create filename
    file_exists = os.path.isfile(filename)  # Check if file exists
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Time Since Start (s)","Index", "Value"])
        for index, value in enumerate(data):
            writer.writerow([current_time, time_since_start, index, value])

def export_fft_data_to_csv(freq, s_dbfs):
    """ Exports the frequency and FFT magnitude data to a CSV file
    Args:
        freq (np.array): The frequency data
        s_dbfs (np.array): The FFT magnitude data in dBFS
    Returns:
        None
    """
    current_time = datetime.datetime.now()  # Get current time
    time_since_start = (current_time - start_time).total_seconds()  # Calculate time since start in seconds
    filename = "fft_data_" + str(start_time) + ".csv"  # Create filename
    file_exists = os.path.isfile(filename)  # Check if file exists
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Time Since Start (s)", "Frequency (Hz)", "Magnitude (dBFS)"])
        for f, mag in zip(freq, s_dbfs):
            writer.writerow([current_time, time_since_start, f, mag])

def update():
    """ Updates the FFT in the window
    Returns:
        None
    """
    global index, freq, dist

    data = my_sdr.rx()  # Receive data
    data = data[0] + data[1]  # Combine channels
    
    win_funct = np.blackman(len(data))  # Apply Blackman window
    y = data * win_funct  # Apply window function
    sp = np.absolute(np.fft.fft(y))  # Compute FFT
    sp = np.fft.fftshift(sp)  # Shift FFT
    s_mag = np.abs(sp) / np.sum(win_funct)  # Compute magnitude
    s_mag = np.maximum(s_mag, 10 ** (-15))  # Avoid log of zero
    s_dbfs = 20 * np.log10(s_mag / (2 ** 11))  # Convert to dBFS
    
    export_raw_data_to_csv(data)  # Export raw data to CSV
    export_fft_data_to_csv(freq, s_dbfs)  # Export FFT data to CSV

    index = index + 1  # Increment index

def end_program():
    """ Gracefully shutsdown the program and Pluto
    Returns:
        None
    """
    my_sdr.tx_destroy_buffer()  # Destroy Tx buffer

# Main loop
try: 
    while True:
        update()
        time.sleep(0.1)  # Adjust sleep time as needed
except KeyboardInterrupt:
    print("Shutting down...")
    end_program()
    sys.exit(0)