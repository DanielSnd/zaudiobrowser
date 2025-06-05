import os
import tempfile
import zipfile
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QUrl
from src.audio_browser.main import MainWindow
from PySide6.QtMultimedia import QMediaPlayer

@pytest.fixture(scope="session")
def app():
    """Create a single QApplication instance for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Cleanup will happen automatically when the session ends

@pytest.fixture
def main_window(app):
    """Create a new MainWindow instance for each test."""
    window = MainWindow()
    window.show()
    yield window
    window.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir

@pytest.fixture
def sample_zip(temp_dir):
    """Create a sample ZIP file with audio and non-audio files."""
    zip_path = os.path.join(temp_dir, "sample.zip")
    
    # Create a ZIP file with various files
    with zipfile.ZipFile(zip_path, 'w') as zf:
        # Add audio files
        zf.writestr("audio1.wav", b"fake wav content")
        zf.writestr("audio2.mp3", b"fake mp3 content")
        zf.writestr("audio3.ogg", b"fake ogg content")
        
        # Add non-audio files
        zf.writestr("text.txt", b"text content")
        zf.writestr("image.jpg", b"fake image content")
    
    return zip_path

def test_window_title(main_window):
    """Test window title."""
    assert main_window.windowTitle() == "Audio Browser"

def test_window_size(main_window):
    """Test window size."""
    assert main_window.width() >= 800
    assert main_window.height() >= 600

def test_initial_state(main_window):
    """Test initial window state."""
    # Check if components are initialized
    assert main_window.file_list is not None
    assert main_window.control_panel is not None
    assert main_window.status_bar is not None
    assert main_window.audio_player is not None
    assert main_window.zip_manager is not None
    
    # Check if file list is empty
    assert main_window.file_list.count() == 0

def test_open_zip(main_window, sample_zip, monkeypatch):
    """Test opening a ZIP file."""
    # Mock file dialog to return sample ZIP
    def mock_get_open_file_name(*args, **kwargs):
        return sample_zip, ""
    
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", mock_get_open_file_name)
    
    # Trigger open ZIP action
    main_window._handle_open_zip()
    
    # Check if files were loaded
    assert main_window.file_list.count() == 3  # Only audio files
    assert any("audio1.wav" in main_window.file_list.item(i).text() for i in range(main_window.file_list.count()))
    assert any("audio2.mp3" in main_window.file_list.item(i).text() for i in range(main_window.file_list.count()))
    assert any("audio3.ogg" in main_window.file_list.item(i).text() for i in range(main_window.file_list.count()))

def test_extract_selected(main_window, sample_zip, temp_dir, monkeypatch):
    """Test extracting selected files."""
    # Mock file dialogs
    def mock_get_open_file_name(*args, **kwargs):
        return sample_zip, ""
    
    def mock_get_existing_directory(*args, **kwargs):
        return temp_dir
    
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", mock_get_open_file_name)
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", mock_get_existing_directory)
    
    # Load ZIP file
    main_window._handle_open_zip()
    
    # Select first two files
    main_window.file_list.item(0).setSelected(True)
    main_window.file_list.item(1).setSelected(True)
    
    # Extract selected files
    main_window._handle_extract_selected()
    
    # Check if files were extracted
    assert os.path.exists(os.path.join(temp_dir, "audio1.wav"))
    assert os.path.exists(os.path.join(temp_dir, "audio2.mp3"))

def test_extract_all(main_window, sample_zip, temp_dir, monkeypatch):
    """Test extracting all files."""
    # Mock file dialogs
    def mock_get_open_file_name(*args, **kwargs):
        return sample_zip, ""
    
    def mock_get_existing_directory(*args, **kwargs):
        return temp_dir
    
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", mock_get_open_file_name)
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", mock_get_existing_directory)
    
    # Load ZIP file
    main_window._handle_open_zip()
    
    # Extract all files
    main_window._handle_extract_all()
    
    # Check if all audio files were extracted
    assert os.path.exists(os.path.join(temp_dir, "audio1.wav"))
    assert os.path.exists(os.path.join(temp_dir, "audio2.mp3"))
    assert os.path.exists(os.path.join(temp_dir, "audio3.ogg"))

def test_play_file(main_window, sample_zip, monkeypatch):
    """Test playing a file."""
    # Mock file dialog
    def mock_get_open_file_name(*args, **kwargs):
        return sample_zip, ""
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", mock_get_open_file_name)
    # Load ZIP file
    main_window._handle_open_zip()
    # Get first file
    file_path = main_window.file_list.item(0).data(Qt.UserRole)
    # Play file
    main_window._handle_play_requested(file_path)
    # Skip if QMediaPlayer cannot play (headless/CI)
    if main_window.audio_player.media_player.playbackState() != QMediaPlayer.PlayingState:
        pytest.skip("QMediaPlayer cannot play in this environment.")
    assert main_window.audio_player._is_playing

def test_drag_drop(main_window, sample_zip):
    """Test drag and drop functionality."""
    # Simulate drop event
    class DummyEvent:
        def mimeData(self):
            class DummyMime:
                def hasUrls(self): return True
                def urls(self):
                    from PySide6.QtCore import QUrl
                    return [QUrl.fromLocalFile(sample_zip)]
            return DummyMime()
    event = DummyEvent()
    main_window.dropEvent(event)
    assert main_window.file_list.count() == 3  # Only audio files

def test_error_handling(main_window, tmp_path):
    """Test error handling."""
    # Try to open a non-existent file
    main_window.zip_manager.cleanup()
    main_window.zip_manager.current_zip = None
    main_window._handle_play_requested("nonexistent.wav")
    # The error label should be set
    assert main_window.status_bar.error_label.text() != ""

def test_cleanup(main_window, sample_zip, monkeypatch):
    """Test resource cleanup."""
    # Mock file dialog
    def mock_get_open_file_name(*args, **kwargs):
        return sample_zip, ""
    
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", mock_get_open_file_name)
    
    # Load ZIP file
    main_window._handle_open_zip()
    
    # Close window
    main_window.close()
    
    # Check if resources were cleaned up
    assert main_window.zip_manager.current_zip is None
    assert main_window.zip_manager.temp_dir is None

def test_keyboard_shortcuts(main_window, qtbot):
    """Test keyboard shortcuts functionality."""
    qtbot.keyClick(main_window, Qt.Key_F1)
    qtbot.wait(100)
    dialog = QMessageBox.activeModalWidget()
    assert dialog is not None
    assert dialog.windowTitle() == "Keyboard Shortcuts"
    qtbot.keyClick(dialog, Qt.Key_Escape)

def test_about_dialog(main_window, qtbot):
    """Test about dialog."""
    main_window._show_about()
    qtbot.wait(100)
    dialog = QMessageBox.activeModalWidget()
    assert dialog is not None
    assert dialog.windowTitle() == "About Audio Browser"
    assert "Audio Browser v" in dialog.text()
    qtbot.keyClick(dialog, Qt.Key_Escape)

def test_menu_tooltips(main_window):
    """Test menu action tooltips."""
    file_menu = main_window.menuBar().actions()[0].menu()
    help_menu = main_window.menuBar().actions()[1].menu()
    # Check file menu actions while menu is open
    file_menu.show()
    open_action = file_menu.actions()[0]
    assert open_action.toolTip() == "Open a ZIP file containing audio files"
    extract_selected = file_menu.actions()[1].menu().actions()[0]
    assert extract_selected.toolTip() == "Extract selected audio files from the ZIP"
    extract_all = file_menu.actions()[1].menu().actions()[1]
    assert extract_all.toolTip() == "Extract all audio files from the ZIP"
    settings_action = file_menu.actions()[3]
    assert settings_action.toolTip() == "Configure application settings"
    exit_action = file_menu.actions()[5]
    assert exit_action.toolTip() == "Exit the application"
    help_menu.show()
    shortcuts_action = help_menu.actions()[0]
    assert shortcuts_action.toolTip() == "Show keyboard shortcuts"
    about_action = help_menu.actions()[2]
    assert about_action.toolTip() == "Show application information" 