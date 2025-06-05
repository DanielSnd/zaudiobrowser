from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Slot
import traceback

class StatusBar(QStatusBar):
    """Custom status bar with progress indicator and message display."""
    
    def __init__(self, parent=None):
        """Initialize the status bar."""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setMinimumHeight(28)
        self.setMaximumHeight(32)
        # Create a container widget for the left side
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        left_layout.addWidget(self.error_label)
        left_layout.addStretch()
        
        # Add the left widget to the status bar
        self.addWidget(left_widget)
        
        # File info label (right-aligned)
        self.file_info = QLabel()
        self.addPermanentWidget(self.file_info)
    
    @Slot(int)
    def update_progress(self, value):
        """Update progress indicator.
        
        Args:
            value (int): Progress value (0-100)
        """
        if value > 0:
            self.progress_bar.setValue(value)
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
    
    @Slot(str)
    def update_file_info(self, info):
        """Update file information display.
        
        Args:
            info (str): File information to display
        """
        self.file_info.setText(info)
    
    @Slot(str)
    def show_error(self, message):
        """Show error message.
        
        Args:
            message (str): Error message to display
        """
        self.error_label.setText(message)
        print(f"Showing error: {message} stacktrace: {traceback.format_exc()}")
        self.error_label.show()
    
    def clear_error(self):
        """Clear error message."""
        self.error_label.clear()
        self.error_label.hide()
    
    def reset(self):
        """Reset status bar state."""
        self.progress_bar.hide()
        self.file_info.clear()
        self.error_label.clear()
        self.error_label.hide() 