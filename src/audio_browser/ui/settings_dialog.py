from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QComboBox, QListWidget, QPushButton,
    QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot
from audio_browser.config.config_manager import ConfigManager

class SettingsDialog(QDialog):
    """Settings dialog for configuring application preferences."""
    
    # Signals
    settings_changed = Signal(dict)  # Emits settings dictionary
    
    def __init__(self, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config_manager = ConfigManager()
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Volume settings
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Default Volume:")
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setValue(100)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_spinbox)
        layout.addLayout(volume_layout)
        
        # Theme settings
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems(["System", "Light", "Dark"])
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combobox)
        layout.addLayout(theme_layout)
        
        # File associations
        layout.addWidget(QLabel("File Associations:"))
        self.file_associations_list = QListWidget()
        self.file_associations_list.addItems([".wav", ".mp3", ".ogg"])
        layout.addWidget(self.file_associations_list)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_settings(self):
        """Load current settings."""
        settings = self.config_manager.get_settings()
        self.volume_spinbox.setValue(settings['volume'])
        self.theme_combobox.setCurrentText(settings['theme'])
        
        # Update file associations
        self.file_associations_list.clear()
        self.file_associations_list.addItems(settings['file_associations'])
    
    def _save_settings(self):
        """Save current settings."""
        settings = {
            "volume": self.volume_spinbox.value(),
            "theme": self.theme_combobox.currentText(),
            "file_associations": [
                self.file_associations_list.item(i).text()
                for i in range(self.file_associations_list.count())
            ]
        }
        self.config_manager.update_settings(settings)
        self.settings_changed.emit(settings)
    
    def accept(self):
        """Handle dialog acceptance."""
        self._save_settings()
        super().accept()
    
    def get_settings(self):
        """Get current settings.
        
        Returns:
            dict: Current settings
        """
        return {
            "volume": self.volume_spinbox.value(),
            "theme": self.theme_combobox.currentText(),
            "file_associations": [
                self.file_associations_list.item(i).text()
                for i in range(self.file_associations_list.count())
            ]
        } 