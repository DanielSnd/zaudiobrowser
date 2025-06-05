from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QPalette
import numpy as np
import io
import wave
import struct

class WaveformWidget(QWidget):
    """Widget for displaying audio waveform visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.waveform_data = None
        self.current_position = 0
        self.duration = 0
        self.is_playing = False
        self.is_dragging = False
        self.setBackgroundRole(QPalette.Base)
        self.setAutoFillBackground(True)
        
        palette = self.palette()
        # Colors
        self.waveform_color = palette.color(QPalette.Highlight) 
        self.progress_color = palette.color(QPalette.HighlightedText)
        self.background_color = palette.color(QPalette.Base)
        self.inactive_color_dragging = palette.color(QPalette.Mid).lighter(140)  # Color for inactive state
        self.inactive_color = palette.color(QPalette.Mid)  # Color for inactive state
        
    def set_playing_state(self, is_playing):
        """Set the playing state of the widget.
        
        Args:
            is_playing (bool): Whether the audio is currently playing
        """
        self.is_playing = is_playing
        self.is_dragging = False
        self.update()
        
    def set_audio_data(self, audio_data):
        """Set the audio data for visualization.
        
        Args:
            audio_data (bytes): Raw audio data in WAV format
        """
        try:
            # Read WAV data
            with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                # Get audio parameters
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                
                # Read all frames
                frames = wav_file.readframes(n_frames)
                
                # Convert to numpy array
                if sample_width == 2:  # 16-bit
                    dtype = np.int16
                else:  # 8-bit
                    dtype = np.int8
                
                # Convert to numpy array
                audio_array = np.frombuffer(frames, dtype=dtype)
                
                # If stereo, convert to mono by averaging channels
                if n_channels == 2:
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1)
                
                # Normalize to -1 to 1
                audio_array = audio_array.astype(np.float32) / np.iinfo(dtype).max
                
                # Downsample for visualization (take max absolute value in each segment)
                num_points = 1000  # Number of points to display
                segment_size = len(audio_array) // num_points
                if segment_size > 0:
                    segments = audio_array[:num_points * segment_size].reshape(-1, segment_size)
                    self.waveform_data = np.max(np.abs(segments), axis=1)
                else:
                    self.waveform_data = np.abs(audio_array)
                
                self.duration = n_frames / wav_file.getframerate() * 1000  # Convert to milliseconds
                self.update()
                
        except Exception as e:
            print(f"Error processing audio data: {e}")
            self.waveform_data = None
            self.update()
    
    def set_position(self, position):
        """Set the current playback position.
        
        Args:
            position (int): Position in milliseconds
        """
        self.current_position = position
        self.update()
    
    def paintEvent(self, event):
        """Paint the waveform visualization."""
        if self.waveform_data is None:
            return
            
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Get widget dimensions
            width = self.width()
            height = self.height()
            
            # Draw background
            painter.fillRect(self.rect(), self.background_color)
            
            # Calculate scaling factors
            x_scale = width / len(self.waveform_data)
            y_scale = height / 2
            
            # Calculate progress position
            progress_x = int((self.current_position / self.duration) * width) if self.duration > 0 else 0
            
            # Draw waveform segments
            for i in range(len(self.waveform_data)):
                x = int(i * x_scale)
                
                # if self.is_playing and progress_x > 0 and progress_x < width:
                # Convert amplitude to integer and ensure it's within bounds
                amplitude = int(self.waveform_data[i] * y_scale)
                amplitude = min(max(amplitude, 0), height // 2)  # Clamp to valid range
                # else:
                #     # When not playing, use a small fixed amplitude
                #     amplitude = 1
                
                # Choose color based on position and state
                if self.is_dragging:
                    if x < progress_x:
                        painter.setPen(QPen(self.inactive_color_dragging, 1))
                    else:
                        painter.setPen(QPen(self.inactive_color, 1))
                elif not self.is_playing:
                    painter.setPen(QPen(self.inactive_color, 1))
                elif x < progress_x:
                    painter.setPen(QPen(self.progress_color, 1))
                else:
                    painter.setPen(QPen(self.waveform_color, 1))
                
                # Draw line from center
                center_y = height // 2
                painter.drawLine(x, center_y - amplitude, x, center_y + amplitude)
        finally:
            painter.end()  # Ensure painter is always ended 