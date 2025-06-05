from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider,
    QLabel, QVBoxLayout
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
import traceback

class ControlPanel(QWidget):
    """Control panel widget with playback controls and progress bar."""
    
    # Signals
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    volume_changed = Signal(int)
    position_changed = Signal(int)
    dragged_tracker_position_changed = Signal(int)
    desired_position_changed = Signal(int)
    was_playing_when_dragging = False
    
    def __init__(self, parent=None):
        """Initialize the control panel."""
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        self._is_playing = False
        self._current_position = 0
        self._current_duration = 0
        self._duration = 0  # For percentage calculations
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Play button
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_button.setToolTip("Play/Pause (Space)")
        layout.addWidget(self.play_button)

        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_button.setToolTip("Stop (S)")
        layout.addWidget(self.stop_button)

        # Progress bar
        self.progress_bar = QSlider(Qt.Horizontal)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setToolTip("Playback progress")
        self.progress_bar.mousePressEvent = self._handle_progress_bar_click
        layout.addWidget(self.progress_bar, stretch=2)

        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        layout.addWidget(self.time_label)

        # Volume control (smaller, right-aligned)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setToolTip("Volume (Up/Down arrows)")
        self.volume_slider.setFixedWidth(80)
        layout.addWidget(self.volume_slider)

        # layout.addStretch(1)
    
    def _connect_signals(self):
        """Connect widget signals to slots."""
        self.play_button.clicked.connect(self._handle_play_click)
        self.stop_button.clicked.connect(self.stop_clicked)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        self.progress_bar.sliderMoved.connect(self._handle_slider_moved)
        self.progress_bar.sliderReleased.connect(self._handle_slider_released)
    
    def _handle_play_click(self):
        """Handle play button click."""
        if self._is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()
    
    def _handle_slider_moved(self, value):
        """Handle slider movement - only update the time label."""
        _desired_position = int((value / 100.0) * getattr(self, '_duration', 0))
        self.update_time_label(position=_desired_position)
        self.dragged_tracker_position_changed.emit(_desired_position)
        if self._is_playing:
            self.pause_clicked.emit()
            self._is_playing = False
            self.was_playing_when_dragging = True
    
    def _handle_slider_released(self):
        """Handle slider release - emit the actual position in milliseconds."""
        value = self.progress_bar.value()
        _desired_position = int((value / 100.0) * getattr(self, '_duration', 0))
        print(f"[DEBUG] Desired position changed to: {_desired_position}")
        self.desired_position_changed.emit(_desired_position)
        if self.was_playing_when_dragging:
            self.play_clicked.emit()
            self.was_playing_when_dragging = False
    
    @Slot(int)
    def update_progress(self, value):
        """Update progress bar value (as percentage).
        
        Args:
            value (int): Progress value as percentage (0-100)
        """
        # Only update if the slider is not being dragged
        if not self.progress_bar.isSliderDown():
            self.progress_bar.setValue(value)
            # Calculate actual position in ms based on percentage and stored duration
            position = int((value / 100.0) * getattr(self, '_duration', 0))
            self.update_time_label(position=position)
    
    @Slot(str)
    def update_time(self, time_str):
        """Update time display.
        
        Args:
            time_str (str): Time string to display
        """
        # This method is no longer used in the new implementation
        pass
    
    def set_position(self, position):
        """Set the progress bar position (in ms)."""
        self.update_time_label(position=position)
    
    def set_duration(self, duration):
        """Set the progress bar duration (in ms)."""
        # Store the duration for time calculations
        self._duration = duration
        # Set progress bar range to 0-100 for percentage-based updates
        self.progress_bar.setRange(0, 100)
        self.update_time_label(duration=duration)
    
    def set_volume(self, volume):
        """Set the volume slider value."""
        self.volume_slider.setValue(volume)
    
    def reset(self):
        """Reset control panel state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        self.update_time_label(position=0, duration=0)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Space:
            # Let the event propagate to parent window
            event.ignore()
        elif event.key() == Qt.Key_S:
            self.stop_clicked.emit()
        elif event.key() == Qt.Key_Left:
            # Seek backward 5 seconds
            current_pos = self.progress_bar.value()
            new_pos = max(0, current_pos - 5)
            self.progress_bar.setValue(new_pos)
            self.position_changed.emit(new_pos)
        elif event.key() == Qt.Key_Right:
            # Seek forward 5 seconds
            current_pos = self.progress_bar.value()
            new_pos = min(self.progress_bar.maximum(), current_pos + 5)
            self.progress_bar.setValue(new_pos)
            self.position_changed.emit(new_pos)
        elif event.key() == Qt.Key_Up:
            # Increase volume
            current_vol = self.volume_slider.value()
            new_vol = min(100, current_vol + 5)
            self.volume_slider.setValue(new_vol)
            self.volume_changed.emit(new_vol)
        elif event.key() == Qt.Key_Down:
            # Decrease volume
            current_vol = self.volume_slider.value()
            new_vol = max(0, current_vol - 5)
            self.volume_slider.setValue(new_vol)
            self.volume_changed.emit(new_vol)
        else:
            super().keyPressEvent(event)
    
    def set_playback_state(self, state):
        """Update play button icon based on playback state ('playing', 'paused', 'stopped')."""
        if state == "playing":
            self._is_playing = True
            self.play_button.setIcon(QIcon.fromTheme("media-playback-pause"))
        else:
            self._is_playing = False
            self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
    
    def update_time_label(self, position=None, duration=None):
        """Update the time label with current position and duration."""
        if position is not None:
            self._current_position = position
        if duration is not None:
            self._current_duration = duration
            
        # Format time strings directly without using ms_to_mmss
        def format_time(ms):
            if ms is None:
                return "00:00.000"
            total_seconds = ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            milliseconds = ms % 1000
            return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            
        self.time_label.setText(f"{format_time(self._current_position)} / {format_time(self._current_duration)}") 
    
    def _handle_progress_bar_click(self, event):
        """Handle clicks on the progress bar track."""
        if event.button() == Qt.LeftButton:
            # Get the click position relative to the slider
            pos = event.position().x()
            
            # Check if click is on the slider's grabber
            slider_handle_width = 16  # Approximate width of the slider handle
            slider_pos = self.progress_bar.sliderPosition()
            slider_range = self.progress_bar.maximum() - self.progress_bar.minimum()
            handle_pos = (slider_pos / slider_range) * self.progress_bar.width()
            
            # If click is within the handle area, let the default slider behavior handle it
            if abs(pos - handle_pos) <= slider_handle_width / 2:
                QSlider.mousePressEvent(self.progress_bar, event)
                return
                
            # Calculate value based on click position and slider width
            value = self.progress_bar.minimum() + (pos / self.progress_bar.width()) * slider_range
            # Set the slider value
            self.progress_bar.setValue(int(value))
            
            if self._is_playing:
                self.was_playing_when_dragging = True
                self.pause_clicked.emit()
                self._is_playing = False
            
            # Emit the desired position
            _desired_position = int((value / 100.0) * getattr(self, '_duration', 0))
            self.desired_position_changed.emit(_desired_position)
            # If we were playing, resume playback
            if self.was_playing_when_dragging:
                self.play_clicked.emit()
                self.was_playing_when_dragging = False
        else:
            # Call the original mousePressEvent for other buttons
            QSlider.mousePressEvent(self.progress_bar, event)