import os
import tempfile
import zipfile
import pytest
from pathlib import Path
from src.audio_browser.zip.zip_manager import ZipManager

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

@pytest.fixture
def invalid_zip(temp_dir):
    """Create an invalid ZIP file."""
    zip_path = os.path.join(temp_dir, "invalid.zip")
    with open(zip_path, 'w') as f:
        f.write("This is not a valid ZIP file")
    return zip_path

@pytest.fixture
def zip_manager():
    """Create a ZipManager instance."""
    return ZipManager()

def test_load_valid_zip(zip_manager, sample_zip):
    """Test loading a valid ZIP file."""
    zip_manager.load_zip(sample_zip)
    assert zip_manager.current_zip is not None
    assert zip_manager.current_zip.filename == sample_zip

def test_load_invalid_zip(zip_manager, invalid_zip):
    """Test loading an invalid ZIP file."""
    with pytest.raises(ValueError):
        zip_manager.load_zip(invalid_zip)

def test_list_audio_files(zip_manager, sample_zip):
    """Test listing audio files from ZIP."""
    zip_manager.load_zip(sample_zip)
    audio_files = zip_manager.list_audio_files()
    
    # Should find 3 audio files
    assert len(audio_files) == 3
    assert any(f.endswith('.wav') for f in audio_files)
    assert any(f.endswith('.mp3') for f in audio_files)
    assert any(f.endswith('.ogg') for f in audio_files)
    
    # Should not include non-audio files
    assert not any(f.endswith('.txt') for f in audio_files)
    assert not any(f.endswith('.jpg') for f in audio_files)

def test_extract_file(zip_manager, sample_zip, temp_dir):
    """Test extracting a single file from ZIP."""
    zip_manager.load_zip(sample_zip)
    extracted_path = zip_manager.extract_file("audio1.wav", temp_dir)
    
    assert os.path.exists(extracted_path)
    assert os.path.getsize(extracted_path) > 0

def test_extract_files(zip_manager, sample_zip, temp_dir):
    """Test extracting multiple files from ZIP."""
    zip_manager.load_zip(sample_zip)
    files_to_extract = ["audio1.wav", "audio2.mp3"]
    extracted_paths = zip_manager.extract_files(files_to_extract, temp_dir)
    
    assert len(extracted_paths) == 2
    for path in extracted_paths:
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

def test_cleanup(zip_manager, sample_zip, temp_dir):
    """Test cleanup of temporary files."""
    zip_manager.load_zip(sample_zip)
    extracted_path = zip_manager.extract_file("audio1.wav", temp_dir)
    
    # Verify file was extracted
    assert os.path.exists(extracted_path)
    
    # Cleanup
    zip_manager.cleanup()
    
    # Verify temporary files were removed
    assert not os.path.exists(extracted_path)

def test_stream_file(zip_manager, sample_zip):
    """Test streaming a file from the ZIP without extraction."""
    zip_manager.load_zip(sample_zip)
    file_name = "audio1.wav"
    expected_content = b"fake wav content"
    chunks = list(zip_manager.stream_file(file_name))
    assert b''.join(chunks) == expected_content 