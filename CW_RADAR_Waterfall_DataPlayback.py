# CW_RADAR_Waterfall_DataPlayback.py
#
# Usage: python3 CW_RADAR_Waterfall_DataPlayback.py <raw_data_file path/name> <fft_data_file path/name>
#  
# Description:
#     Reads the exported data from CSV files and plays it back in the same GUI as the original script.
#     Displays an interactive FFT and waterfall plot of the recorded signal using PyQt5 and pyqtgraph.
#
# Written by Nathan Griffin
# Derived from CW_RADAR_Waterfall.py by Jon Kraft
# Other contributors: Github Copilot
#
# See the LICENSE file for the license.

# Imports
import sys
import os
import datetime
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from pyqtgraph.Qt import QtCore, QtGui
import csv
import argparse  # Add argparse import

# Global variables
sample_rate = 0.6e6  # Sample rate
signal_freq = 100e3  # Signal frequency
num_slices = 50  # Number of slices for waterfall plot
fft_size = 1024 * 64  # FFT size
img_array = np.ones((num_slices, fft_size)) * (-100)  # Initialize image array
freq = np.linspace(-sample_rate / 2, sample_rate / 2, int(fft_size))  # Frequency array

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive FFT Playback")  # Set window title
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
        control_label = QLabel("PHASER Simple CW Radar Playback")  # Create control label
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
        tr = QtGui.QTransform()  # Create transform
        tr.translate(0,-sample_rate/2)  # Translate
        tr.scale(0.35, sample_rate / (fft_size))  # Scale
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
        """ Gracefully shuts down the program
        Returns:
            None
        """
        self.close()  # Close window

def read_csv_data(filename):
    """ Reads data from a CSV file
    Args:
        filename (str): The filename of the CSV file
    Returns:
        list: A list of rows from the CSV file
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist")  # Raise error if file does not exist
    data = []  # Initialize data
    with open(filename, mode='r') as file: # Open CSV file
        reader = csv.reader(file) # Create CSV reader
        next(reader)  # Skip header
        for row in reader: # Iterate through rows
            data.append(row) # Append row to data
    return data # Return data

def update():
    """ Updates the FFT and waterfall plots in the window
    Returns:
        None
    """
    global index, freq, dist, raw_data, fft_data # Global variables
    label_style = {"color": "#FFF", "font-size": "14pt"}  # Label style

    if index < len(fft_data): # Check if index is less than length of FFT data
        current_fft = fft_data[index] # Get current FFT data
        s_dbfs = [float(mag) for mag in current_fft[3:]]  # Extract magnitude data from CSV row

        win.fft_curve.setData(freq, s_dbfs)  # Update FFT curve
        win.fft_plot.setLabel("bottom", text="Frequency", units="Hz", **label_style)  # Update label

        win.img_array = np.roll(win.img_array, 1, axis=0)  # Roll image array
        win.img_array[0] = s_dbfs  # Update image array
        win.imageitem.setLevels([win.low_slider.value(), win.high_slider.value()])  # Update levels
        win.imageitem.setImage(win.img_array, autoLevels=False)  # Update image

        if index == 1: # Check if index is 1
            win.fft_plot.enableAutoRange("xy", False)  # Disable auto range
        index += 1  # Increment index

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CW RADAR Waterfall Data Playback")  # Create argument parser
    parser.add_argument("raw_data_file", type=str, help="Filename for raw data CSV")  # Add raw_data_file argument
    parser.add_argument("fft_data_file", type=str, help="Filename for FFT data CSV")  # Add fft_data_file argument
    args = parser.parse_args()  # Parse arguments

    # create pyqt5 app
    App = QApplication(sys.argv)  # Create application

    # create the instance of our Window
    win = Window()  # Create window instance
    win.setWindowState(QtCore.Qt.WindowMaximized)  # Maximize window
    index = 0  # Initialize index

    # Read data from CSV files
    raw_data = read_csv_data(args.raw_data_file)
    fft_data = read_csv_data(args.fft_data_file)

    timer = QtCore.QTimer()  # Create timer
    timer.timeout.connect(update)  # Connect timer to update
    timer.start(100)  # Start timer with 100 ms interval

    # start the app
    sys.exit(App.exec())  # Execute application