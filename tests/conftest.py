import pytest
from PySide6.QtCore import QUrl, QTimer, QCoreApplication
from PySide6.QtWidgets import QApplication
from src.audio_browser.player.audio_player import AudioPlayer

# Create a Qt application for the entire test session
@pytest.fixture(scope="session")
def qapp():
    """Create a Qt application for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # # Clean up any remaining events
    # app.processEvents()
    # app.exit()
    
@pytest.fixture
def audio_player(qapp, qtbot, request):
    """Fixture providing an AudioPlayer instance."""
    player = AudioPlayer()
    qtbot.addWidget(player)  # Ensure proper Qt cleanup
    
    def cleanup():
        try:
            # Stop playback and clear source
            if hasattr(player, 'stop'):
                player.stop()
            if hasattr(player, 'media_player'):
                player.media_player.setSource(QUrl())
            
            # Process events
            qapp.processEvents()
            qtbot.wait(100)
            
            # Hide and close the widget
            if not player.isHidden():
                player.hide()
            player.close()
            
            # Process events again
            qapp.processEvents()
            qtbot.wait(100)
            
            # Delete the widget
            player.deleteLater()
            
            # Final event processing
            qapp.processEvents()
            qtbot.wait(100)
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    request.addfinalizer(cleanup)
    return player

@pytest.fixture
def sample_audio_file():
    """Fixture providing the path to test audio file."""
    import os
    return os.path.join(os.path.dirname(__file__), "test_data", "test.wav")
