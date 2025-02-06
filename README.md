# ER Data Acquisition

This repository contains scripts for Continuous Wave (CW) and Frequency Modulated Continuous Wave (FMCW) radar signal acquisition using Software Defined Radio (SDR) and Phaser devices. The scripts configure the devices, acquire radar signals, and display interactive FFT and waterfall plots using PyQt5 and pyqtgraph, or simply export the data without the interactive displays. The CW and FMCW scripts also have multiple variations that incorporate enhancements, such as chirp synchronization or constant false alarm rate (CFAR) filtering.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Hardware](#hardware)
- [License](#license)

## Features

- Initializes and configures SDR and Phaser devices for radar signal acquisition.
- Configures the SDR for both Rx and Tx operations.
- Creates sinewave waveforms for transmission.
- Continuously updates FFT and waterfall plots with the received data.
- Exports raw and FFT data to CSV files.
- Provides playback functionality for recorded radar data.

## Requirements

- Python
- [Analog Devices Inc.](https://www.analog.com) components
- [PyQt5](https://pypi.org/project/PyQt5/)
- [pyqtgraph](https://pypi.org/project/pyqtgraph/)
- [NumPy](https://pypi.org/project/numpy/)
- [Matplotlib](https://pypi.org/project/matplotlib/)

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/starbelt/er-data-acquisition
   cd er-data-acquisition
   ```
2. Install the required Python packages:

## Usage

### CW Radar Waterfall

This script initializes and configures the SDR and Phaser devices to perform Continuous Wave (CW) radar signal acquisition. It displays an interactive FFT and waterfall plot of the received signal.

```sh
python CW/CW_RADAR_Waterfall.py
```

### CW Radar Waterfall Data Export

This script initializes and configures the SDR and Phaser devices to perform Continuous Wave (CW) radar signal acquisition. It exports the data to CSV files. It is practically identical to CW_RADAR_Waterfall.py, but with data exporting to a csv.
```sh
python CW/CW_RADAR_Waterfall_Export.py
```

### CW Radar Waterfall Data Playback

This script takes exported data and plays it back on the same GUI as CW_RADAR_Waterfall.py, but without the hardware needing to be connected or initialized.

```sh
python CW/CW_RADAR_Waterfall_Playback.py
```

### FMCW Radar Waterfall

This script initializes and configures the SDR and Phaser devices to perform Frequency Modulated Continuous Wave (FMCW) radar signal acquisition. It displays an interactive FFT and waterfall plot of the received signal.

```sh
python FMCW/FMCW_RADAR_Waterfall.py
```

### FMCW Radar Waterfall with Chirp Synchronization

This script initializes and configures the SDR and Phaser devices to perform Frequency Modulated Continuous Wave (FMCW) radar signal with Chirp Synch acquisition. It displays an interactive FFT and waterfall plot of the received signal.

```sh
python FMCW/FMCW_RADAR_Waterfall_ChirpSync.py
```

### CFAR Radar Waterfall

This script initializes and configures the SDR and Phaser devices to perform radar signal acquisition with Constant False Alarm Rate (CFAR) filtering. It displays an interactive FFT and waterfall plot of the received signal.

```sh
python CFAR/CFAR_RADAR_Waterfall.py
```

### CFAR Radar Waterfall with Chirp Synchronization

This script initializes and configures the SDR and Phaser devices to perform radar signal acquisition with Chirp Synch and CFAR filtering. It displays an interactive FFT and waterfall plot of the received signal.

```sh
python CFAR/CFAR_RADAR_Waterfall_ChirpSync.py
```

### CFAR Radar Waterfall with Chirp Synchronization with Data Export

This script initializes and configures the SDR and Phaser devices to perform radar signal acquisition with Chirp Synch and CFAR filtering. It displays an interactive FFT and waterfall plot of the received signal. It also creates a csv file that exports all of the data from when the script is run.

```sh
python CFAR/CFAR_RADAR_Waterfall_ChirpSync_Export.py
```

### CFAR Radar Waterfall with Chirp Synchronization Data Playback

This script plays back previously recorded data from the data export script. It displays an interactive FFT and waterfall plot of the received signal that can be filtered with CFAR.

```sh
python CFAR/CFAR_RADAR_Waterfall_ChirpSync_Playback.py
```

### Target Detection dbfs

This script performs target detection using dBFS values.

```sh
python CFAR/target_detection_dbfs.py
```

## Hardware

Utilized CN0566 Phased Array (Phaser) Development Platform. The hardware included with CN0566:

- **EVAL-CN0566-RPIZ Board:**
  - ADL8107: Low Noise Amplifier (6 - 18 GHz, 1.3 dB NF, 24 dB gain)
  - ADAR1000 Beamformer (8 - 16 GHz, 4-Channel, 360° phase adjustment with 2.8° resolution, set to receive only)
  - Raspberry Pi 4: Micro-computer for I/O control signals
  - ADALM-Pluto: Analog to Digital DAQ (send and receive)
  - LTC5548: Mixer (2.2 GHz output)
  - 16GB SD Card: With ADI Kuiper Linux Image
- **HB100: Microwave Source**
- **5 V Wall Adapter: 3 A, USB-C**
- **Tripod: For Mounting CN0566**

## License

This project is licensed under the terms of the Analog Devices License.
