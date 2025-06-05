import pytest
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer
from src.audio_browser.player.audio_player import AudioPlayer
import os

@pytest.fixture(autouse=True)
def cleanup_after_test(audio_player, qtbot):
    yield
    # Ensure player is stopped and source is cleared
    audio_player.stop()
    audio_player.media_player.setSource(QUrl())
    # Give Qt time to clean up resources
    qtbot.wait(500)

def test_player_initialization(audio_player):
    assert audio_player is not None
    assert isinstance(audio_player.media_player, QMediaPlayer)
    assert audio_player.media_player.playbackState() == QMediaPlayer.StoppedState

def test_play_functionality_preloaded_media(audio_player, sample_audio_file, qtbot):
    # Set up the media source
    audio_player.media_player.setSource(QUrl.fromLocalFile(sample_audio_file))
    print(f"File path: {sample_audio_file}")
    # Wait for media to be loaded
    qtbot.waitUntil(lambda: audio_player.media_player.mediaStatus() == QMediaPlayer.LoadedMedia, timeout=5000)
    
    # Verify media is loaded
    assert audio_player.media_player.mediaStatus() == QMediaPlayer.LoadedMedia
    
    # Play the media
    audio_player.play()
    
    # Add debug prints
    print(f"Media Status: {audio_player.media_player.mediaStatus()}")
    print(f"Playback State: {audio_player.media_player.playbackState()}")
    print(f"Is Playing: {audio_player._is_playing}")
    print(f"Media Loaded: {audio_player._media_loaded}")
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)

    audio_player.stop()
    audio_player.media_player.setSource(QUrl())
    qtbot.wait(100)
    

def test_play_functionality_by_path(audio_player, sample_audio_file, qtbot):
    # Play the media
    audio_player.play(sample_audio_file)
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)

    audio_player.stop()
    audio_player.media_player.setSource(QUrl())
    qtbot.wait(100)

def test_pause_functionality(audio_player, sample_audio_file, qtbot):
    # Set up the media source
    audio_player.media_player.setSource(QUrl.fromLocalFile(sample_audio_file))
    
    # Wait for media to be loaded
    qtbot.waitUntil(lambda: audio_player.media_player.mediaStatus() == QMediaPlayer.LoadedMedia, timeout=5000)
    
    # Play the media
    audio_player.play()
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)
    
    # Pause the media
    audio_player.pause()
    
    # Wait for paused state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PausedState, timeout=5000)

def test_stop_functionality(audio_player, sample_audio_file, qtbot):
    # Set up the media source
    audio_player.media_player.setSource(QUrl.fromLocalFile(sample_audio_file))
    
    # Wait for media to be loaded
    qtbot.waitUntil(lambda: audio_player.media_player.mediaStatus() == QMediaPlayer.LoadedMedia, timeout=5000)
    
    # Play the media
    audio_player.play()
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)
    
    # Stop the media
    audio_player.stop()
    
    # Wait for stopped state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.StoppedState, timeout=5000)

def test_volume_control(audio_player):
    test_volume = 75
    audio_player.set_volume(test_volume)
    assert audio_player.get_volume() == test_volume

def test_progress_tracking(audio_player, sample_audio_file, qtbot):
    # Set up the media source
    audio_player.media_player.setSource(QUrl.fromLocalFile(sample_audio_file))
    
    # Wait for media to be loaded
    qtbot.waitUntil(lambda: audio_player.media_player.mediaStatus() == QMediaPlayer.LoadedMedia, timeout=5000)
    
    # Play the media
    audio_player.play()
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)
    
    # Wait for position to change
    qtbot.waitUntil(lambda: audio_player.get_position() > 0, timeout=5000)

def test_error_handling(audio_player, qtbot):
    # Use a non-existent file
    non_existent = "/tmp/does_not_exist.wav"
    audio_player.media_player.setSource(QUrl.fromLocalFile(non_existent))
    
    def play_and_check_error():
        audio_player.play()
        # Error should be emitted immediately
    
    # Schedule the operation
    QTimer.singleShot(0, play_and_check_error)
    
    # Wait for error state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.StoppedState, timeout=5000)

def test_format_support_wav(audio_player, qtbot):
    # Get the test file path
    sample_file = os.path.join(os.path.dirname(__file__), "test_data", "test.wav")
    
    # Play the media
    audio_player.play(sample_file)
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)

    # Give enough time for playback to start
    qtbot.wait(500)
    audio_player.stop()
    audio_player.media_player.setSource(QUrl())
    qtbot.wait(500)
        

def test_format_support_ogg(audio_player, qtbot):
    # Get the test file path
    sample_file = os.path.join(os.path.dirname(__file__), "test_data", "test.ogg")
    
    # Play the media
    audio_player.play(sample_file)
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)

    # Give enough time for playback to start
    qtbot.wait(500)
    audio_player.stop()
    audio_player.media_player.setSource(QUrl())
    qtbot.wait(500)
        
def test_format_support_mp3(audio_player, qtbot):
    # Get the test file path
    sample_file = os.path.join(os.path.dirname(__file__), "test_data", "test.mp3")
    
    # Play the media
    audio_player.play(sample_file)
    
    # Wait for playing state
    qtbot.waitUntil(lambda: audio_player.media_player.playbackState() == QMediaPlayer.PlayingState, timeout=5000)
    
    # Give enough time for playback to start
    qtbot.wait(500)
    audio_player.stop()
    audio_player.media_player.setSource(QUrl())
    qtbot.wait(500)