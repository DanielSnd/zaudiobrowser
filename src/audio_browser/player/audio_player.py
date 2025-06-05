from PySide6.QtCore import QObject, Signal, QUrl, Slot, QBuffer, QIODevice, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import QPalette
import logging
import sys
import os
import io
import wave
import numpy as np
from .waveform_widget import WaveformWidget

# Set up logging to stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class AudioPlayer(QWidget):
    """Audio player component for handling audio playback."""
    
    DEBUG = False
    
    # Signals
    state_changed = Signal(str)  # Emits the new state
    progress_updated = Signal(int)  # Emits progress percentage
    error_occurred = Signal(str)  # Emits error message
    duration_changed = Signal(int)  # Emits duration in milliseconds
    position_changed = Signal(int)  # Emits current position in milliseconds
    queued_position_changed = -1
    
    def __init__(self):
        """Initialize the audio player."""
        super().__init__()
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create waveform widget
        self.waveform = WaveformWidget()
        self.layout.addWidget(self.waveform)
        
        # Create media player and audio output
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Store signal connections for cleanup
        self._connections = []
        
        # Initialize state
        self._current_file = None
        self._is_playing = False
        self._media_loaded = False
        self._pending_play = False
        # Connect signals
        self._connections.extend([
            self.media_player.playbackStateChanged.connect(self._handle_state_change),
            self.media_player.positionChanged.connect(self._handle_position_change),
            self.media_player.durationChanged.connect(self._handle_duration_change),
            self.media_player.errorOccurred.connect(self._handle_error),
            self.media_player.mediaStatusChanged.connect(self._handle_media_status)
        ])
        
        logger.debug("AudioPlayer initialized")

    def closeEvent(self, event):
        """Handle widget close event."""
        try:
            self.stop()
            if hasattr(self, 'media_player'):
                self.media_player.setSource(QUrl())
            if hasattr(self, '_buffer'):
                self._buffer.close()
                self._buffer.deleteLater()
            # Disconnect all signals
            for connection in self._connections:
                try:
                    connection.disconnect()
                except Exception:
                    pass
            self._connections.clear()
            event.accept()
        except Exception as e:
            logger.error(f"Error during closeEvent: {e}")
            event.accept()

    def __del__(self):
        """Clean up Qt resources."""
        try:
            if hasattr(self, 'media_player') and self.media_player is not None:
                try:
                    self.media_player.stop()
                    self.media_player.setSource(QUrl())
                except Exception:
                    pass
                # Disconnect all signals
                for connection in getattr(self, '_connections', []):
                    try:
                        connection.disconnect()
                    except Exception:
                        pass
                self._connections.clear()
                try:
                    self.media_player.deleteLater()
                except Exception:
                    pass
            if hasattr(self, 'audio_output') and self.audio_output is not None:
                try:
                    self.audio_output.deleteLater()
                except Exception:
                    pass
            if hasattr(self, '_buffer'):
                try:
                    self._buffer.close()
                    self._buffer.deleteLater()
                except Exception:
                    pass
        except Exception as e:
            try:
                logger.error(f"Error during cleanup: {e}")
            except Exception:
                pass
    
    def play(self, file_path=None, zip_stream=None):
        """Play the audio file.
        
        Args:
            file_path (str, optional): Path to the audio file. If None, resumes current file.
            zip_stream (bytes, optional): Audio data stream from ZIP file.
        """
        logger.debug(f"Play called with file_path: {file_path}, has_stream: {zip_stream is not None}")
        
        # Stop current playback and clean up
        self.stop()
        if hasattr(self, '_buffer'):
            try:
                self._buffer.close()
                self._buffer.deleteLater()
            except Exception as e:
                logger.warning(f"Error cleaning up previous buffer: {e}")
            self._buffer = None
        
        # Reset media player
        self.media_player.setSource(QUrl())
        
        if zip_stream is not None:
            try:
                # Create a buffer for the stream data
                self._buffer = QBuffer()
                self._buffer.setData(zip_stream)
                self._buffer.open(QIODevice.ReadOnly)
                
                # Set the buffer as the media source
                self.media_player.setSourceDevice(self._buffer)
                
                # Update waveform visualization in a separate thread
                try:
                    # Use QTimer to defer waveform update
                    QTimer.singleShot(0, lambda: self.waveform.set_audio_data(zip_stream))
                except Exception as e:
                    logger.warning(f"Failed to update waveform: {e}")
                
                logger.debug("Set buffer as media source")
                
            except Exception as e:
                logger.error(f"Error setting up stream playback: {e}")
                self.error_occurred.emit(f"Error setting up playback: {e}")
                return
                
        elif file_path:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                self.error_occurred.emit(f"File not found: {file_path}")
                return
                
            try:
                self._current_file = file_path
                url = QUrl.fromLocalFile(file_path)
                logger.debug(f"Setting source to: {url.toString()}")
                self.media_player.setSource(url)
                
                # Update waveform visualization in a separate thread
                try:
                    # Use QTimer to defer waveform update
                    QTimer.singleShot(0, lambda: self._update_waveform_from_file(file_path))
                except Exception as e:
                    logger.warning(f"Failed to update waveform: {e}")
                    
            except Exception as e:
                logger.error(f"Error setting up file playback: {e}")
                self.error_occurred.emit(f"Error setting up playback: {e}")
                return
        
        # Start playback
        self.media_player.play()
    
    def _update_waveform_from_file(self, file_path):
        """Update waveform from file in a separate thread."""
        try:
            with open(file_path, 'rb') as f:
                self.waveform.set_audio_data(f.read())
        except Exception as e:
            logger.warning(f"Failed to update waveform from file: {e}")
    
    def pause(self):
        """Pause the current playback."""
        if self.DEBUG: logger.debug("Pause called")
        self.media_player.pause()
    
    def stop(self):
        """Stop the current playback."""
        if self.DEBUG: logger.debug("Stop called")
        self.media_player.stop()
    
    def set_volume(self, volume):
        """Set the playback volume.
        
        Args:
            volume (int): Volume level (0-100)
        """
        if self.DEBUG: logger.debug(f"Setting volume to: {volume}")
        self.audio_output.setVolume(volume / 100.0)
    
    def get_volume(self):
        """Get the current volume level.
        
        Returns:
            int: Current volume level (0-100)
        """
        return int(self.audio_output.volume() * 100)
    
    def get_position(self):
        """Get the current playback position.
        
        Returns:
            int: Current position in milliseconds
        """
        return self.media_player.position()
    
    def get_duration(self):
        """Get the total duration of the current file.
        
        Returns:
            int: Total duration in milliseconds
        """
        return self.media_player.duration()
    
    def set_position(self, position):
        """Set the playback position.
        
        Args:
            position (int): Position in milliseconds
        """
        if self.DEBUG: logger.debug(f"Setting position to: {position}")
        if self.media_player.mediaStatus() == QMediaPlayer.LoadedMedia:
            self.media_player.setPosition(position)
        else:
            self.queued_position_changed = position
    
    def resume(self, position=None):
        """Resume playback from a specific position.
        
        Args:
            position (int, optional): Position in milliseconds to resume from.
        """
        if self.DEBUG: logger.debug(f"Resume called with position: {position}")
        if self.media_player.mediaStatus() == QMediaPlayer.LoadedMedia:
            if position is not None:
                self.media_player.setPosition(position)
            self.media_player.play()
            self._is_playing = True
            self.state_changed.emit("playing")
        else:
            logger.error("Cannot resume: No media loaded")
    
    @Slot()
    def _handle_state_change(self, state):
        """Handle media player state changes."""
        logger.debug(f"State changed to: {state}")
        state_map = {
            QMediaPlayer.PlayingState: "playing",
            QMediaPlayer.PausedState: "paused",
            QMediaPlayer.StoppedState: "stopped"
        }
        state_str = state_map.get(state, "unknown")
        logger.debug(f"Emitting state_changed signal with: {state_str}")
        self.state_changed.emit(state_str)
        # Update waveform playing state
        self.waveform.set_playing_state(state == QMediaPlayer.PlayingState or state == QMediaPlayer.PausedState)
        if state == QMediaPlayer.PlayingState and self.queued_position_changed != -1:
            self.media_player.setPosition(self.queued_position_changed)
            self.queued_position_changed = -1
    
    @Slot()
    def _handle_position_change(self, position):
        """Handle position changes during playback."""
        
        if self.DEBUG: logger.debug(f"Position changed to: {position}")
        # Emit the actual position in milliseconds
        self.position_changed.emit(position)
        self.waveform.set_position(position)
        
        # Calculate and emit progress percentage
        duration = self.media_player.duration()
        if duration > 0:
            progress = int((position / duration) * 100)
            if self.DEBUG: logger.debug(f"Emitting progress: {progress}%")
            self.progress_updated.emit(progress)
    
    @Slot()
    def _handle_dragged_tracker_position_change(self, position):
        """Handle dragged tracker position changes."""
        if self.DEBUG: logger.debug(f"Dragged tracker position changed to: {position}")
        self.waveform.is_dragging = True
        self.waveform.set_position(position)
    
    @Slot()
    def _handle_duration_change(self, duration):
        """Handle duration changes."""
        if self.DEBUG: logger.debug(f"Duration changed to: {duration}")
        self.duration_changed.emit(duration)
    
    @Slot()
    def _handle_error(self, error, error_string):
        """Handle playback errors."""
        logger.error(f"Error occurred: {error} - {error_string}")
        self.error_occurred.emit(f"Error {error}: {error_string}")
        self.stop()
    
    @Slot()
    def _handle_media_status(self, status):
        """Handle media status changes."""
        if self.DEBUG: logger.debug(f"Media status changed to: {status}")
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self._media_loaded = True
            if self._pending_play:
                if self.DEBUG: logger.debug("Media loaded, starting playback")
                self.media_player.play()
                self._is_playing = True
                self._pending_play = False
                self.state_changed.emit("playing")
            elif self._is_playing and self.queued_position_changed != -1:
                self.media_player.setPosition(self.queued_position_changed)
                self.queued_position_changed = -1
        elif status == QMediaPlayer.MediaStatus.BufferedMedia:
            pass
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._is_playing = False
            self._pending_play = False
            self.state_changed.emit("stopped")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            if self.DEBUG: logger.error("Invalid media")
            self._media_loaded = False
            self._pending_play = False
            self.state_changed.emit("error")
            # Add more detailed error message
            if self._current_file and not os.path.exists(self._current_file):
                self.error_occurred.emit(f"File no longer exists: {self._current_file}")
            else:
                self.error_occurred.emit("Invalid media file") 