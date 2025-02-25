# %%
# Copyright (C) 2024 Analog Devices, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#     - Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     - Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#     - Neither the name of Analog Devices, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#     - The use of this software may or may not infringe the patent rights
#       of one or more patent holders.  This license does not release you
#       from the requirement that you obtain separate licenses from these
#       patent holders to use this software.
#     - Use of the software either in source or binary form, must be run
#       on or directly connected to an Analog Devices Inc. component.
#
# THIS SOFTWARE IS PROVIDED BY ANALOG DEVICES "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED.
#
# IN NO EVENT SHALL ANALOG DEVICES BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, INTELLECTUAL PROPERTY
# RIGHTS, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''FMCW Range Processing Data from the Phaser (CN0566)
   Jon Kraft, Oct 2 2024'''

# Imports
import time
import matplotlib # type: ignore
import matplotlib.pyplot as plt # type: ignore
import numpy as np
import argparse
import pandas as pd # type: ignore
plt.close('all')

# Parse the input file argument
parser = argparse.ArgumentParser(description='Process FMCW Range Data')
parser.add_argument('input_file', type=str, help='Path to the input .npy file')
args = parser.parse_args()

f = args.input_file
config = np.load(f[:-4]+"_config.npy")          # these files are generated by the "Range_Doppler_Plot.py" program
all_data = np.load(f)


MTI_filter = 'none'  # choices are none, 2pulse, or 3pulse
min_scale = 4
max_scale = 6
step_thru_plots = False
time_divider = 1


# %%
""" Calculate and print summary of ramp parameters
"""
sample_rate = config[0]
signal_freq = config[1]
output_freq = config[2]
num_chirps = int(config[3])
chirp_BW = config[4]
ramp_time_s = config[5]
frame_length_ms = config[6]
max_doppler_vel = config[7] if len(config) > 7 else 1.5
max_range = config[8] if len(config) > 8 else 10
upper_freq = config[9] if len(config) > 9 else -sample_rate/2
lower_freq = config[10] if len(config) > 10 else sample_rate/2
time_data = pd.read_csv(f"{f[:-4]}_time.csv")
num_samples = len(all_data[0][0])


data_start_time = time_data.iloc[0, 0]  # Get first timestamp

PRI = frame_length_ms / 1e3
PRF = 1 / PRI

# Split into frames
N_frame = int(PRI * float(sample_rate))

# Obtain range-FFT x-axis
c = 3e8
wavelength = c / output_freq
slope = chirp_BW / ramp_time_s
freq = np.linspace(lower_freq, upper_freq, N_frame)
dist = (freq - signal_freq) * c / (2 * slope)

# Resolutions
R_res = c / (2 * chirp_BW)
print(f"Range resolution: {R_res} m")
v_res = wavelength / (2 * num_chirps * PRI)
print(f"Velocity resolution: {v_res:.2f} m/s")

# Doppler spectrum limits
max_doppler_freq = PRF / 2
# max_doppler_vel = max_doppler_freq * wavelength / 2

print("sample_rate = ", sample_rate/1e6, "MHz, ramp_time = ", int(ramp_time_s*(1e6)), "us, num_chirps = ", num_chirps, ", PRI = ", frame_length_ms, " ms")


# %%
# Function to process data
def pulse_canceller(radar_data):
    global num_chirps, num_samples
    rx_chirps = []
    rx_chirps = radar_data
    # create 2 pulse canceller MTI array
    Chirp2P = np.empty([num_chirps, num_samples])*1j
    for chirp in range(num_chirps-1):
        chirpI = rx_chirps[chirp,:]
        chirpI1 = rx_chirps[chirp+1,:]
        chirp_correlation = np.correlate(chirpI, chirpI1, 'valid')
        angle_diff = np.angle(chirp_correlation, deg=False)  # returns radians
        Chirp2P[chirp,:] = (chirpI1 - chirpI * np.exp(-1j*angle_diff[0]))
    # create 3 pulse canceller MTI array
    Chirp3P = np.empty([num_chirps, num_samples])*1j
    for chirp in range(num_chirps-2):
        chirpI = Chirp2P[chirp,:]
        chirpI1 = Chirp2P[chirp+1,:]
        Chirp3P[chirp,:] = chirpI1 - chirpI
    return Chirp2P, Chirp3P

def freq_process(data):
    rx_chirps_fft = np.fft.fftshift(abs(np.fft.fft2(data)))
    range_doppler_data = np.log10(rx_chirps_fft).T
    # or this is the longer way to do the fft2 function:
    # rx_chirps_fft = np.fft.fft(data)
    # rx_chirps_fft = np.fft.fft(rx_chirps_fft.T).T   
    # rx_chirps_fft = np.fft.fftshift(abs(rx_chirps_fft))
    range_doppler_data = np.log10(rx_chirps_fft).T
    num_good = len(range_doppler_data[:,0])   
    center_delete = 0  # delete ground clutter velocity bins around 0 m/s
    if center_delete != 0:
        for g in range(center_delete):
            end_bin = int(num_chirps/2+center_delete/2)
            range_doppler_data[:,(end_bin-center_delete+g)] = np.zeros(num_good)
    range_delete = 0   # delete the zero range bins (these are Tx to Rx leakage)
    if range_delete != 0:
        for r in range(range_delete):
            start_bin = int(len(range_doppler_data)/2)
            range_doppler_data[start_bin+r, :] = np.zeros(num_chirps)
    range_doppler_data = np.clip(range_doppler_data, min_scale, max_scale)  # clip the data to control the max spectrogram scale
    return range_doppler_data

# %%
# Plot range doppler data, loop through at the end of the data set
cmn = ''
i = 0
time_idx = 0
raw_data = freq_process(all_data[i])
# print(raw_data.shape)
# print(raw_data)
i=int((i+1) % len(all_data))
range_doppler_fig, ax = plt.subplots(1, figsize=(7,7))
extent = [-max_doppler_vel, max_doppler_vel, dist.min(), dist.max()]
cmaps = ['inferno', 'plasma']
cmn = cmaps[0]
ax.set_xlim([-max_doppler_vel, max_doppler_vel])
ax.set_ylim([0, max_range])
ax.set_yticks(np.arange(0, max_range, 1))
ax.set_ylabel('Range [m]')
ax.set_title('Range Doppler Spectrum')
ax.set_xlabel('Velocity [m/s]')
range_doppler = ax.imshow(raw_data, aspect='auto', extent=extent, origin='lower', cmap=matplotlib.colormaps.get_cmap(cmn))

print("CTRL + c to stop the loop")
if step_thru_plots == True:
    print("Press Enter key to adance to next frame")
    print("Press 0 then Enter to go back one frame")
try:
    while True:
        if MTI_filter != 'none':
            Chirp2P, Chirp3P = pulse_canceller(all_data[i])
            if MTI_filter == '3pulse':
                freq_process_data = freq_process(Chirp3P)
            else:
                freq_process_data = freq_process(Chirp2P)
        else:
            freq_process_data = freq_process(all_data[i])
        range_doppler.set_data(freq_process_data)
        plt.show(block=False)
        if time_idx == 0:
            playback_start_time = time.time()
        current_playback_time = time.time() - playback_start_time
        target_time = (time_data.iloc[time_idx, 0] - data_start_time)*time_divider
        if current_playback_time < target_time:
            plt.pause(target_time - current_playback_time)
        if step_thru_plots == True:
            val = input()
            if val == '0':
                i=int((i-1) % len(all_data))
            else:
                i=int((i+1) % len(all_data))
        else:
            time_idx = (time_idx + 1) % len(time_data)
            i=int((i+1) % len(all_data))
except KeyboardInterrupt:  # press ctrl-c to stop the loop
    pass




