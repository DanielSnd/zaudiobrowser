import pytest
from PySide6.QtWidgets import QApplication, QListWidgetItem
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from src.audio_browser.ui.audio_file_list import AudioFileListWidget
from src.audio_browser.ui.control_panel import ControlPanel
from src.audio_browser.ui.status_bar import StatusBar
from src.audio_browser.ui.settings_dialog import SettingsDialog

# AudioFileListWidget Tests
def test_audio_file_list_creation(qapp, qtbot):
    """Test creation of AudioFileListWidget."""
    widget = AudioFileListWidget()
    qtbot.addWidget(widget)
    assert widget is not None
    assert isinstance(widget, AudioFileListWidget)

def test_audio_file_list_add_item(qapp, qtbot):
    """Test adding items to AudioFileListWidget."""
    widget = AudioFileListWidget()
    qtbot.addWidget(widget)
    
    # Add test item
    item = QListWidgetItem("test.wav")
    widget.addItem(item)
    
    assert widget.count() == 1
    assert widget.item(0).text() == "test.wav"

def test_audio_file_list_selection(qapp, qtbot):
    """Test selection handling in AudioFileListWidget."""
    widget = AudioFileListWidget()
    qtbot.addWidget(widget)
    
    # Add test items
    item1 = QListWidgetItem("test1.wav")
    item2 = QListWidgetItem("test2.mp3")
    widget.addItem(item1)
    widget.addItem(item2)
    
    # Select first item
    widget.setCurrentItem(item1)
    assert widget.currentItem() == item1
    assert widget.currentItem().text() == "test1.wav"

# ControlPanel Tests
def test_control_panel_creation(qapp, qtbot):
    """Test creation of ControlPanel."""
    widget = ControlPanel()
    qtbot.addWidget(widget)
    assert widget is not None
    assert isinstance(widget, ControlPanel)

def test_control_panel_buttons(qapp, qtbot):
    """Test control panel buttons."""
    widget = ControlPanel()
    qtbot.addWidget(widget)
    
    # Check if buttons exist
    assert widget.play_button is not None
    assert widget.stop_button is not None
    assert widget.volume_slider is not None
    assert widget.progress_bar is not None

def test_control_panel_keyboard_shortcuts(qapp, qtbot):
    """Test control panel keyboard shortcuts."""
    widget = ControlPanel()
    qtbot.addWidget(widget)
    
    # Test Space key (play/pause)
    qtbot.keyClick(widget, Qt.Key_Space)
    assert widget._is_playing
    
    # Test S key (stop)
    qtbot.keyClick(widget, Qt.Key_S)
    assert not widget._is_playing
    
    # Test Left/Right keys (seek)
    widget.progress_bar.setValue(50)
    qtbot.keyClick(widget, Qt.Key_Left)
    assert widget.progress_bar.value() == 45  # 5 seconds back
    
    qtbot.keyClick(widget, Qt.Key_Right)
    assert widget.progress_bar.value() == 50  # 5 seconds forward
    
    # Test Up/Down keys (volume)
    widget.volume_slider.setValue(50)
    qtbot.keyClick(widget, Qt.Key_Up)
    assert widget.volume_slider.value() == 55  # Increase by 5
    
    qtbot.keyClick(widget, Qt.Key_Down)
    assert widget.volume_slider.value() == 50  # Decrease by 5

def test_control_panel_tooltips(qapp, qtbot):
    """Test control panel tooltips."""
    widget = ControlPanel()
    qtbot.addWidget(widget)
    
    # Check tooltips
    assert widget.play_button.toolTip() == "Play/Pause (Space)"
    assert widget.pause_button.toolTip() == "Pause (Space)"
    assert widget.stop_button.toolTip() == "Stop (S)"
    assert widget.volume_slider.toolTip() == "Volume (Up/Down arrows)"
    assert widget.progress_bar.toolTip() == "Playback progress"

# StatusBar Tests
def test_status_bar_creation(qapp, qtbot):
    """Test creation of StatusBar."""
    widget = StatusBar()
    qtbot.addWidget(widget)
    assert widget is not None
    assert isinstance(widget, StatusBar)

def test_status_bar_messages(qapp, qtbot):
    """Test status bar message display."""
    widget = StatusBar()
    qtbot.addWidget(widget)
    
    # Test message display
    test_message = "Test message"
    widget.showMessage(test_message)
    assert widget.currentMessage() == test_message

# SettingsDialog Tests
def test_settings_dialog_creation(qapp, qtbot):
    """Test creation of SettingsDialog."""
    dialog = SettingsDialog()
    qtbot.addWidget(dialog)
    assert dialog is not None
    assert isinstance(dialog, SettingsDialog)

def test_settings_dialog_controls(qapp, qtbot):
    """Test settings dialog controls."""
    dialog = SettingsDialog()
    qtbot.addWidget(dialog)
    
    # Check if controls exist
    assert dialog.volume_spinbox is not None
    assert dialog.theme_combobox is not None
    assert dialog.file_associations_list is not None 