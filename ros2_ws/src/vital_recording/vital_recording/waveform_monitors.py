#!/usr/bin/env python3
"""
Waveform monitoring classes for vital parameter recording.

This module contains the base WaveformMonitor class and its specialized
implementations for different types of waveform data (Pleth, ECG1, Resp, INVP1).
"""

import os
import time
from abc import ABC, abstractmethod


class WaveformMonitor(ABC):
    """Base class for waveform monitoring"""
    
    def __init__(self, name: str, file_path: str, sampling_rate: float, buffer_size: int, logger):
        """
        Initialize a waveform monitor.
        
        Args:
            name: Display name for the monitor (e.g., "Pleth", "ECG1")
            file_path: Path to the CSV file to monitor
            sampling_rate: Sampling rate in Hz
            buffer_size: Maximum number of samples to keep in buffer
            logger: Logger instance for error reporting
        """
        self.name = name
        self.file_path = file_path
        self.sampling_rate = sampling_rate  # Hz
        self.sample_period = 1.0 / sampling_rate  # seconds per sample
        self.buffer_size = buffer_size  # maximum number of samples to keep
        self.logger = logger
        
        # Data buffers
        self.time_buffer = []
        self.value_buffer = []
        
        # Tracking variables
        self.file_position = 0
        self.sample_index = 0
        
        # Latest data for publishing
        self.latest_value = None
        self.latest_timestamp = None
        
        # Monitoring state
        self.is_monitoring = False
    
    def reset(self):
        """Reset all buffers and tracking variables"""
        self.time_buffer.clear()
        self.value_buffer.clear()
        self.file_position = 0
        self.sample_index = 0
        self.latest_value = None
        self.latest_timestamp = None
    
    def monitor_file(self, monitoring_flag_func):
        """
        Monitor the waveform file for new data.
        
        Args:
            monitoring_flag_func: Function that returns True while monitoring should continue
        """
        while monitoring_flag_func():
            try:
                if os.path.exists(self.file_path):
                    with open(self.file_path, 'r') as f:
                        f.seek(self.file_position)
                        lines = f.readlines()
                        self.file_position = f.tell()
                    
                    for line in lines:
                        if not monitoring_flag_func():
                            break
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            try:
                                value = float(parts[1])
                                timestamp = self.sample_index * self.sample_period
                                self.sample_index += 1
                                
                                # Add to buffers
                                self.time_buffer.append(timestamp)
                                self.value_buffer.append(value)
                                
                                # Update latest data for publishing
                                self.latest_value = value
                                self.latest_timestamp = time.time()
                                
                                # Maintain buffer size
                                if len(self.time_buffer) > self.buffer_size:
                                    self.time_buffer = self.time_buffer[-self.buffer_size:]
                                    self.value_buffer = self.value_buffer[-self.buffer_size:]
                                
                            except ValueError:
                                continue
                
                time.sleep(self.sample_period)
            except Exception as e:
                if monitoring_flag_func():
                    self.logger.error(f"{self.name} monitor error: {e}")
                time.sleep(0.1)


class PlethMonitor(WaveformMonitor):
    """Plethysmography waveform monitor (100 Hz, 15 seconds buffer)"""
    
    def __init__(self, file_path: str, logger):
        """
        Initialize Plethysmography monitor.
        
        Args:
            file_path: Path to the pleth CSV file
            logger: Logger instance
        """
        super().__init__("Pleth", file_path, 100.0, 1500, logger)


class ECG1Monitor(WaveformMonitor):
    """ECG waveform monitor (250 Hz, 15 seconds buffer)"""
    
    def __init__(self, file_path: str, logger):
        """
        Initialize ECG1 monitor.
        
        Args:
            file_path: Path to the ECG1 CSV file
            logger: Logger instance
        """
        super().__init__("ECG1", file_path, 250.0, 3750, logger)


class RespMonitor(WaveformMonitor):
    """Respiration waveform monitor (25 Hz, 15 seconds buffer)"""
    
    def __init__(self, file_path: str, logger):
        """
        Initialize Respiration monitor.
        
        Args:
            file_path: Path to the respiration CSV file
            logger: Logger instance
        """
        super().__init__("Resp", file_path, 25.0, 375, logger)


class INVP1Monitor(WaveformMonitor):
    """Invasive pressure waveform monitor (125 Hz, 15 seconds buffer)"""
    
    def __init__(self, file_path: str, logger):
        """
        Initialize INVP1 monitor.
        
        Args:
            file_path: Path to the INVP1 CSV file
            logger: Logger instance
        """
        super().__init__("INVP1", file_path, 125.0, 1875, logger)


def create_waveform_monitors(file_paths: dict, logger) -> list:
    """
    Factory function to create all waveform monitors.
    
    Args:
        file_paths: Dictionary with keys 'pleth', 'ecg1', 'resp', 'invp1' 
                   and corresponding file paths as values
        logger: Logger instance
        
    Returns:
        List of WaveformMonitor instances
    """
    monitors = [
        PlethMonitor(file_paths['pleth'], logger),
        ECG1Monitor(file_paths['ecg1'], logger),
        RespMonitor(file_paths['resp'], logger),
        INVP1Monitor(file_paths['invp1'], logger)
    ]
    return monitors
