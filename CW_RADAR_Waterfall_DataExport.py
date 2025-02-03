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
#     Sets up a PyQt5 GUI to display the FFT and waterfall plots of the received signal.
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
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from pyqtgraph.Qt import QtCore, QtGui
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

sample_rate = 0.6e6  # Sample rate
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

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive FFT")  # Set window title
        self.setGeometry(100, 100, 800, 800)  # Set window geometry (x, y, width, height)
        self.setFixedWidth(1600)  # Set fixed width
        self.num_rows = 12  # Number of rows
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)  # Remove close button
        self.UiComponents()  # Initialize UI components
        self.show()  # Show window

    # method for components
    def UiComponents(self):
        widget = QWidget()  # Create widget

        global layout
        layout = QGridLayout()  # Create grid layout

        # Control Panel
        control_label = QLabel("PHASER Simple CW Radar")  # Create control label
        font = control_label.font()  # Get font
        font.setPointSize(24)  # Set font size
        control_label.setFont(font)  # Apply font
        font.setPointSize(12)  # Set font size
        control_label.setAlignment(Qt.AlignHCenter)  # Center align | Qt.AlignVCenter
        layout.addWidget(control_label, 0, 0, 1, 2)  # Add to layout

        # Buttons        
        self.quit_button = QPushButton("Quit")  # Create quit button
        self.quit_button.pressed.connect(self.end_program)  # Connect to end_program
        layout.addWidget(self.quit_button, 30, 0, 4, 4)  # Add to layout

        # Waterfall level slider
        self.low_slider = QSlider(Qt.Horizontal)  # Create low slider
        self.low_slider.setMinimum(-100)  # Set minimum value
        self.low_slider.setMaximum(0)  # Set maximum value
        self.low_slider.setValue(-66)  # Set initial value
        self.low_slider.setTickInterval(20)  # Set tick interval
        self.low_slider.setMaximumWidth(200)  # Set maximum width
        self.low_slider.setTickPosition(QSlider.TicksBelow)  # Set tick position
        self.low_slider.valueChanged.connect(self.get_water_levels)  # Connect to get_water_levels
        layout.addWidget(self.low_slider, 8, 0)  # Add to layout

        self.high_slider = QSlider(Qt.Horizontal)  # Create high slider
        self.high_slider.setMinimum(-100)  # Set minimum value
        self.high_slider.setMaximum(0)  # Set maximum value
        self.high_slider.setValue(-42)  # Set initial value
        self.high_slider.setTickInterval(20)  # Set tick interval
        self.high_slider.setMaximumWidth(200)  # Set maximum width
        self.high_slider.setTickPosition(QSlider.TicksBelow)  # Set tick position
        self.high_slider.valueChanged.connect(self.get_water_levels)  # Connect to get_water_levels
        layout.addWidget(self.high_slider, 10, 0)  # Add to layout

        self.water_label = QLabel("Waterfall Intensity Levels")  # Create water label
        self.water_label.setFont(font)  # Apply font
        self.water_label.setAlignment(Qt.AlignCenter)  # Center align
        self.water_label.setMinimumWidth(300)  # Set minimum width
        layout.addWidget(self.water_label, 7, 0)  # Add to layout
        self.low_label = QLabel("LOW LEVEL: %0.0f" % (self.low_slider.value()))  # Create low label
        self.low_label.setFont(font)  # Apply font
        self.low_label.setAlignment(Qt.AlignLeft)  # Left align
        self.low_label.setMinimumWidth(100)  # Set minimum width
        layout.addWidget(self.low_label, 8, 1)  # Add to layout
        self.high_label = QLabel("HIGH LEVEL: %0.0f" % (self.high_slider.value()))  # Create high label
        self.high_label.setFont(font)  # Apply font
        self.high_label.setAlignment(Qt.AlignLeft)  # Left align
        self.high_label.setMinimumWidth(100)  # Set minimum width
        layout.addWidget(self.high_label, 10, 1)  # Add to layout

        # FFT plot
        self.fft_plot = pg.plot()  # Create FFT plot
        self.fft_plot.setMinimumWidth(600)  # Set minimum width
        self.fft_curve = self.fft_plot.plot(freq, pen={'color':'y', 'width':2})  # Create FFT curve
        title_style = {"size": "20pt"}  # Title style
        label_style = {"color": "#FFF", "font-size": "14pt"}  # Label style
        self.fft_plot.setLabel("bottom", text="Frequency", units="Hz", **label_style)  # Set bottom label
        self.fft_plot.setLabel("left", text="Magnitude", units="dB", **label_style)  # Set left label
        self.fft_plot.setTitle("Received Signal - Frequency Spectrum", **title_style)  # Set title
        layout.addWidget(self.fft_plot, 0, 2, self.num_rows, 1)  # Add to layout
        self.fft_plot.setYRange(-60, 0)  # Set Y range
        self.fft_plot.setXRange(99e3, 101e3)  # Set X range

        # Waterfall plot
        self.waterfall = pg.PlotWidget()  # Create waterfall plot
        self.imageitem = pg.ImageItem()  # Create image item
        self.waterfall.addItem(self.imageitem)  # Add image item to waterfall plot
        # Use a viridis colormap
        pos = np.array([0.0, 0.25, 0.5, 0.75, 1.0])  # Color positions
        color = np.array([[68, 1, 84,255], [59, 82, 139,255], [33, 145, 140,255], [94, 201, 98,255], [253, 231, 37,255]], dtype=np.ubyte)  # Colors
        lut = pg.ColorMap(pos, color).getLookupTable(0.0, 1.0, 256)  # Create lookup table
        self.imageitem.setLookupTable(lut)  # Set lookup table
        self.imageitem.setLevels([0,1])  # Set levels
        # self.imageitem.scale(0.35, sample_rate / (N))  # this is deprecated -- we have to use setTransform instead
        tr = QtGui.QTransform()  # Create transform
        tr.translate(0,-sample_rate/2)  # Translate
        tr.scale(0.35, sample_rate / (N))  # Scale
        self.imageitem.setTransform(tr)  # Set transform
        zoom_freq = 0.3e3  # Zoom frequency
        self.waterfall.setRange(yRange=(signal_freq - zoom_freq, signal_freq + zoom_freq))  # Set range
        self.waterfall.setTitle("Waterfall Spectrum", **title_style)  # Set title
        self.waterfall.setLabel("left", "Frequency", units="Hz", **label_style)  # Set left label
        self.waterfall.setLabel("bottom", "Time", units="sec", **label_style)  # Set bottom label
        layout.addWidget(self.waterfall, 0 + self.num_rows + 1, 2, self.num_rows, 1)  # Add to layout
        self.img_array = np.ones((num_slices, fft_size)) * (-100)  # Initialize image array

        widget.setLayout(layout)  # Set layout
        # setting this widget as central widget of the main window
        self.setCentralWidget(widget)  # Set central widget

    def get_water_levels(self):
        """ Updates the waterfall intensity levels
        Returns:
            None
        """
        if self.low_slider.value() > self.high_slider.value():
            self.low_slider.setValue(self.high_slider.value())  # Adjust low slider value
        self.low_label.setText("LOW LEVEL: %0.0f" % (self.low_slider.value()))  # Update low label
        self.high_label.setText("HIGH LEVEL: %0.0f" % (self.high_slider.value()))  # Update high label

    def end_program(self):
        """ Gracefully shutsdown the program and Pluto
        Returns:
            None
        """
        my_sdr.tx_destroy_buffer()  # Destroy Tx buffer
        self.close()  # Close window

# create pyqt5 app
App = QApplication(sys.argv)  # Create application

# create the instance of our Window
win = Window()  # Create window instance
win.setWindowState(QtCore.Qt.WindowMaximized)  # Maximize window
index = 0  # Initialize index

def export_raw_data_to_csv(data):
    """ Exports the received data to a CSV file
    Args:
        data (np.array): The data to export
        filename (str): The filename for the CSV file
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
        filename (str): The filename for the CSV file
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
    label_style = {"color": "#FFF", "font-size": "14pt"}  # Label style

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

    win.fft_curve.setData(freq, s_dbfs)  # Update FFT curve
    win.fft_plot.setLabel("bottom", text="Frequency", units="Hz", **label_style)  # Update label
    
    win.img_array = np.roll(win.img_array, 1, axis=0)  # Roll image array
    win.img_array[0] = s_dbfs  # Update image array
    win.imageitem.setLevels([win.low_slider.value(), win.high_slider.value()])  # Update levels
    win.imageitem.setImage(win.img_array, autoLevels=False)  # Update image

    if index == 1:
        win.fft_plot.enableAutoRange("xy", False)  # Disable auto range
    index = index + 1  # Increment index

timer = QtCore.QTimer()  # Create timer
timer.timeout.connect(update)  # Connect timer to update
timer.start(0)  # Start timer

# start the app
sys.exit(App.exec())  # Execute application
