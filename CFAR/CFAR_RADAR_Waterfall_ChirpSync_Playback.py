# CFAR_RADAR_Waterfall_ChirpSync_Playback.py
#
# Usage: python3 CFAR_RADAR_Waterfall_ChirpSync_Playback.py <data_file path/name>
#  
# Description:
#     This script reads in a CSV file containing CFAR data and displays the data in a waterfall plot.
#     The script also allows the user to toggle between displaying the CFAR threshold and applying the CFAR threshold.
#     The user can also adjust the CFAR bias, number of guard cells, and number of reference cells.
#     The user can also adjust the intensity levels of the waterfall plot.
#     The script also displays the time since the start of the data playback.
#
# Written by Nathan Griffin
# Derived from CFAR_RADAR_Waterfall_ChirpSync.py by Jon Kraft
# Other contributors: Github Copilot
#
# See the LICENSE file for the license.

# Imports
import sys
import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QElapsedTimer, QCoreApplication
from PyQt5.QtWidgets import *
from pyqtgraph.Qt import QtCore, QtGui
import csv
import argparse
from target_detection_dbfs import cfar
import time

# Global variables
sample_rate = 0.682e6
center_freq = 2.1e9
signal_freq = 100e3
rx_gain = 20   # must be between -3 and 70
output_freq = 10e9
default_chirp_bw = 750e6
ramp_time = 500      # ramp time in us
num_slices = 400     # this sets how much time will be displayed on the waterfall plot
fft_size = 1022
# fft_size = 8192  
plot_freq = 200e3    # x-axis freq range to plot
max_dist = 6
min_dist = -1

last_error_time = None
previous_time_since_start = 0
old_freq = []
freq_overwrite = False


vco_freq = int(output_freq + signal_freq + center_freq)
BW = default_chirp_bw
num_steps = int(ramp_time)    # in general it works best if there is 1 step per us

c = 3e8
wavelength = c / output_freq

N = int(2**18)
fc = int(signal_freq)
ts = 1 / float(sample_rate)
t = np.arange(0, N * ts, ts)
i = np.cos(2 * np.pi * t * fc) * 2 ** 14
q = np.sin(2 * np.pi * t * fc) * 2 ** 14
iq = 1 * (i + 1j * q)

ramp_time_s = ramp_time / 1e6
slope = BW / ramp_time_s
upper_freq = (max_dist * 2 * slope / c) + signal_freq + 1
lower_freq = (min_dist * 2 * slope / c) + signal_freq + 1
freq = np.linspace(lower_freq, upper_freq , int(fft_size))
# freq = np.linspace(-sample_rate / 2, sample_rate / 2, int(fft_size))
dist = (freq - signal_freq) * c / (2 * slope)
plot_dist = False


plot_threshold = False
cfar_toggle = False
class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive FFT")
        self.setGeometry(0, 0, 400, 400)  # (x,y, width, height)
        #self.setFixedWidth(600)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.num_rows = 12
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False) #remove the window's close button
        self.UiComponents()
        self.show()

    # method for components
    def UiComponents(self):
        widget = QWidget()

        global layout, signal_freq, plot_freq
        layout = QGridLayout()

        # Control Panel
        control_label = QLabel("PHASER CFAR Targeting")
        font = control_label.font()
        font.setPointSize(24)
        control_label.setFont(font)
        font.setPointSize(12)
        control_label.setAlignment(Qt.AlignHCenter)  # | Qt.AlignVCenter)
        layout.addWidget(control_label, 0, 0, 1, 2)

        # Check boxes
        self.thresh_check = QCheckBox("Plot CFAR Threshold")
        font = self.thresh_check.font()
        font.setPointSize(10)
        self.thresh_check.setFont(font)
        self.thresh_check.stateChanged.connect(self.change_thresh)
        layout.addWidget(self.thresh_check, 2, 0)
        
        self.cfar_check = QCheckBox("Apply CFAR Threshold")
        font = self.cfar_check.font()
        self.cfar_check.setFont(font)
        self.cfar_check.stateChanged.connect(self.change_cfar)
        layout.addWidget(self.cfar_check, 2, 1)
        
        self.quit_button = QPushButton("Quit")
        self.quit_button.pressed.connect(self.end_program)
        layout.addWidget(self.quit_button, 30, 0, 4, 4)
        
        self.x_axis_check = QCheckBox("Convert to Distance")
        font = self.x_axis_check.font()
        font.setPointSize(10)
        self.x_axis_check.setFont(font)

        self.x_axis_check.stateChanged.connect(self.change_x_axis)
        layout.addWidget(self.x_axis_check, 4, 0)
        
        #CFAR Sliders
        self.cfar_bias = QSlider(Qt.Horizontal)
        self.cfar_bias.setMinimum(0)
        self.cfar_bias.setMaximum(100)
        self.cfar_bias.setValue(11)
        self.cfar_bias.setTickInterval(5)
        self.cfar_bias.setMaximumWidth(200)
        self.cfar_bias.setTickPosition(QSlider.TicksBelow)
        self.cfar_bias.valueChanged.connect(self.get_cfar_values)
        layout.addWidget(self.cfar_bias, 8, 0)
        self.cfar_bias_label = QLabel("CFAR Bias (dB): %0.0f" % (self.cfar_bias.value()))
        self.cfar_bias_label.setFont(font)
        self.cfar_bias_label.setAlignment(Qt.AlignLeft)
        self.cfar_bias_label.setMinimumWidth(100)
        self.cfar_bias_label.setMaximumWidth(200)
        layout.addWidget(self.cfar_bias_label, 8, 1)
        
        self.cfar_guard = QSlider(Qt.Horizontal)
        self.cfar_guard.setMinimum(1)
        self.cfar_guard.setMaximum(40)
        self.cfar_guard.setValue(8)
        self.cfar_guard.setTickInterval(4)
        self.cfar_guard.setMaximumWidth(200)
        self.cfar_guard.setTickPosition(QSlider.TicksBelow)
        self.cfar_guard.valueChanged.connect(self.get_cfar_values)
        layout.addWidget(self.cfar_guard, 10, 0)
        self.cfar_guard_label = QLabel("Num Guard Cells: %0.0f" % (self.cfar_guard.value()))
        self.cfar_guard_label.setFont(font)
        self.cfar_guard_label.setAlignment(Qt.AlignLeft)
        self.cfar_guard_label.setMinimumWidth(100)
        self.cfar_guard_label.setMaximumWidth(200)
        layout.addWidget(self.cfar_guard_label, 10, 1)
        
        self.cfar_ref = QSlider(Qt.Horizontal)
        self.cfar_ref.setMinimum(1)
        self.cfar_ref.setMaximum(100)
        self.cfar_ref.setValue(16)
        self.cfar_ref.setTickInterval(10)
        self.cfar_ref.setMaximumWidth(200)
        self.cfar_ref.setTickPosition(QSlider.TicksBelow)
        self.cfar_ref.valueChanged.connect(self.get_cfar_values)
        layout.addWidget(self.cfar_ref, 12, 0)
        self.cfar_ref_label = QLabel("Num Ref Cells: %0.0f" % (self.cfar_ref.value()))
        self.cfar_ref_label.setFont(font)
        self.cfar_ref_label.setAlignment(Qt.AlignLeft)
        self.cfar_ref_label.setMinimumWidth(100)
        self.cfar_ref_label.setMaximumWidth(200)
        layout.addWidget(self.cfar_ref_label, 12, 1)

        # waterfall level slider
        self.low_slider = QSlider(Qt.Horizontal)
        self.low_slider.setMinimum(-100)
        self.low_slider.setMaximum(20)
        self.low_slider.setValue(-100)
        self.low_slider.setTickInterval(5)
        self.low_slider.setMaximumWidth(200)
        self.low_slider.setTickPosition(QSlider.TicksBelow)
        self.low_slider.valueChanged.connect(self.get_water_levels)
        layout.addWidget(self.low_slider, 16, 0)

        self.high_slider = QSlider(Qt.Horizontal)
        self.high_slider.setMinimum(-100)
        self.high_slider.setMaximum(20)
        self.high_slider.setValue(20)
        self.high_slider.setTickInterval(5)
        self.high_slider.setMaximumWidth(200)
        self.high_slider.setTickPosition(QSlider.TicksBelow)
        self.high_slider.valueChanged.connect(self.get_water_levels)
        layout.addWidget(self.high_slider, 18, 0)

        self.water_label = QLabel("Waterfall Intensity Levels")
        self.water_label.setFont(font)
        self.water_label.setAlignment(Qt.AlignCenter)
        self.water_label.setMinimumWidth(100)
        self.water_label.setMaximumWidth(200)
        layout.addWidget(self.water_label, 15, 0,1,1)
        self.low_label = QLabel("LOW LEVEL: %0.0f" % (self.low_slider.value()))
        self.low_label.setFont(font)
        self.low_label.setAlignment(Qt.AlignLeft)
        self.low_label.setMinimumWidth(100)
        self.low_label.setMaximumWidth(200)
        layout.addWidget(self.low_label, 16, 1)
        self.high_label = QLabel("HIGH LEVEL: %0.0f" % (self.high_slider.value()))
        self.high_label.setFont(font)
        self.high_label.setAlignment(Qt.AlignLeft)
        self.high_label.setMinimumWidth(100)
        self.high_label.setMaximumWidth(200)
        layout.addWidget(self.high_label, 18, 1)

        # FFT plot
        self.fft_plot = pg.plot()
        self.fft_plot.setMinimumWidth(600)
        self.fft_curve = self.fft_plot.plot(freq, pen={'color':'y', 'width':2})
        self.fft_threshold = self.fft_plot.plot(freq, pen={'color':'r', 'width':2})
        title_style = {"size": "20pt"}
        label_style = {"color": "#FFF", "font-size": "14pt"}
        self.fft_plot.setLabel("bottom", text="Frequency", units="Hz", **label_style)
        self.fft_plot.setLabel("left", text="Magnitude", units="dB", **label_style)
        self.fft_plot.setTitle("Received Signal - Frequency Spectrum", **title_style)
        layout.addWidget(self.fft_plot, 0, 2, self.num_rows, 1)
        self.fft_plot.setYRange(-60, 0)
        self.fft_plot.setXRange(lower_freq, upper_freq)
        
        # Time since start label
        self.time_label = QLabel("Time Since Start: 0.0 s")  # Create time label
        self.time_label.setFont(font)  # Apply font
        self.time_label.setAlignment(Qt.AlignCenter)  # Center align
        layout.addWidget(self.time_label, 1, 0, 1, 2)  # Add to layout
        
        # Waterfall plot
        self.waterfall = pg.PlotWidget()
        self.imageitem = pg.ImageItem()
        self.waterfall.addItem(self.imageitem)
        
        # Use a viridis colormap
        pos = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        color = np.array([[68, 1, 84,255], [59, 82, 139,255], [33, 145, 140,255], [94, 201, 98,255], [253, 231, 37,255]], dtype=np.ubyte)
        lut = pg.ColorMap(pos, color).getLookupTable(0.0, 1.0, 256)
        self.imageitem.setLookupTable(lut)
        self.imageitem.setLevels([0,1])
        tr = QtGui.QTransform()
        tr.translate(0,lower_freq)
        tr.scale(1, (upper_freq - lower_freq) / fft_size)
        self.imageitem.setTransform(tr)
        zoom_freq = 35e3
        self.waterfall.setRange(yRange=(lower_freq, upper_freq))
        self.waterfall.setTitle("Waterfall Spectrum", **title_style)
        self.waterfall.setLabel("left", "Frequency", units="Hz", **label_style)
        self.waterfall.setLabel("bottom", "Time", units="sec", **label_style)
        layout.addWidget(self.waterfall, 0 + self.num_rows + 1, 2, self.num_rows, 1)
        self.img_array = np.ones((num_slices, fft_size))*(-100)

        widget.setLayout(layout)
        # setting this widget as central widget of the main window
        self.setCentralWidget(widget)

    def get_range_res(self):
        """ Updates the slider bar label with Chirp bandwidth and range resolution
		Returns:
			None
		"""
        bw = self.bw_slider.value() * 1e6
        range_res = c / (2 * bw)

    def get_cfar_values(self):
        """ Updates the cfar values
		Returns:
			None
		"""
        self.cfar_bias_label.setText("CFAR Bias (dB): %0.0f" % (self.cfar_bias.value()))
        self.cfar_guard_label.setText("Num Guard Cells: %0.0f" % (self.cfar_guard.value()))
        self.cfar_ref_label.setText("Num Ref Cells: %0.0f" % (self.cfar_ref.value()))


    def get_water_levels(self):
        """ Updates the waterfall intensity levels
		Returns:
			None
		"""
        if self.low_slider.value() > self.high_slider.value():
            self.low_slider.setValue(self.high_slider.value())
        self.low_label.setText("LOW LEVEL: %0.0f" % (self.low_slider.value()))
        self.high_label.setText("HIGH LEVEL: %0.0f" % (self.high_slider.value()))

    def end_program(self):
        """ Gracefully shutsdown the program and Pluto
		"""
        self.close()

    def change_thresh(self, state):
        """ Toggles between showing cfar threshold values
		Args:
			state (QtCore.Qt.Checked) : State of check box
		Returns:
			None
		"""
        global plot_threshold
        plot_state = win.fft_plot.getViewBox().state
        if state == QtCore.Qt.Checked:
            plot_threshold = True
        else:
            plot_threshold = False

    def change_cfar(self, state):
        """ Toggles between enabling/disabling CFAR
		Args:
			state (QtCore.Qt.Checked) : State of check box
		Returns:
			None
		"""
        global cfar_toggle
        if state == QtCore.Qt.Checked:
            cfar_toggle = True
        else:
            cfar_toggle = False
    
    def change_x_axis(self, state):
        """ Toggles between showing frequency and range for the x-axis
		"""
        global plot_dist, slope, signal_freq, plot_freq
        plot_state = win.fft_plot.getViewBox().state
        if state == QtCore.Qt.Checked:
            plot_dist = True
            range_x = (plot_freq) * c / (2 * slope)
            self.fft_plot.setXRange(0, range_x)
        else:
            plot_dist = False
            self.fft_plot.setXRange(signal_freq, signal_freq+plot_freq)

def read_csv_data(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist")
    data = []
    with open(filename, mode='r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            data.append([float(row[0]), float(row[1]), float(row[2])])
    return data

def update():
    global index, plot_threshold, freq, ramp_time_s, sample_rate, cfar_data, last_error_time, previous_time_since_start, freq_overwrite, plot_dist
    label_style = {"color": "#FFF", "font-size": "14pt"}

    if index >= len(cfar_data):
        index = 0
    
    current_time_since_start = cfar_data[index][0]
    s_dbfs = np.array([row[2] for row in cfar_data[index:index + 1022]])
    freq = np.array([row[1] for row in cfar_data[index:index + 1022]])
    mismatch = False
    
    if s_dbfs.shape[0] != freq.shape[0]:
        mismatch = True
        old_freq = freq
        freq_overwrite = True
        freq = freq[:s_dbfs.shape[0]]
        print("Freq changed")
        if last_error_time != current_time_since_start: #Error logging, but only for non-repeating errors
            last_error_time = current_time_since_start
            # Truncate freq to match the size of s_dbfs
            raise ValueError(f"Shape mismatch: freq has shape {freq.shape}, but s_dbfs has shape {s_dbfs.shape} at time {current_time_since_start}. Truncated freq to shape {freq.shape}")
    elif freq_overwrite:
        freq = old_freq
        freq_overwrite = False
        
    
    delta_time = (current_time_since_start - previous_time_since_start) * 1000
    previous_time_since_start = current_time_since_start
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < delta_time:
        QCoreApplication.processEvents()
    
    bias = win.cfar_bias.value()
    num_guard_cells = win.cfar_guard.value()
    num_ref_cells = win.cfar_ref.value()
    cfar_method = 'average'
    
    if (True):
        threshold, targets = cfar(s_dbfs, num_guard_cells, num_ref_cells, bias, cfar_method)
        s_dbfs_cfar = targets.filled(-200)  # fill the values below the threshold with -200 dBFS
        s_dbfs_threshold = threshold
    win.fft_threshold.setData(freq, s_dbfs_threshold)
    
    if plot_threshold:
        win.fft_threshold.setVisible(True)
    else:
        win.fft_threshold.setVisible(False)
    win.img_array = np.roll(win.img_array, 1, axis=0)
    
    if cfar_toggle:
        if plot_dist: 
            win.fft_curve.setData(dist, s_dbfs_cfar)
            win.img_array[0] = s_dbfs_cfar
            win.fft_plot.setLabel("bottom", text="Distance", units="m", **label_style)
        else:
            win.fft_curve.setData(freq, s_dbfs_cfar)
            win.img_array[0] = s_dbfs_cfar
            win.fft_plot.setLabel("bottom", text="Frequency", units="Hz", **label_style)
    else:
        if plot_dist: 
            win.fft_curve.setData(dist, s_dbfs)
            win.img_array[0] = s_dbfs
            win.fft_plot.setLabel("bottom", text="Distance", units="m", **label_style)
        else:
            win.fft_curve.setData(freq, s_dbfs)
            win.img_array[0] = s_dbfs
            win.fft_plot.setLabel("bottom", text="Frequency", units="Hz", **label_style)
    
    win.imageitem.setLevels([win.low_slider.value(), win.high_slider.value()])
    win.imageitem.setImage(win.img_array, autoLevels=False)
    win.time_label.setText(f"Time Since Start: {current_time_since_start:.2f} s")
    
    if index == 1:
        win.fft_plot.enableAutoRange("xy", False)
    index += 1022

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CFAR RADAR Waterfall Data Playback")
    parser.add_argument("data_file", type=str, help="Filename for CFAR data CSV")
    args = parser.parse_args()

    App = QApplication(sys.argv)
    win = Window()
    win.setWindowState(QtCore.Qt.WindowMaximized)
    index = 0

    cfar_data = read_csv_data(args.data_file)

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(0)

    sys.exit(App.exec())
