import os
import zipfile
import tempfile
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Callable, Dict, Tuple
from PySide6.QtWidgets import QApplication
import time
import traceback

from audio_browser.cache.cache_manager import CacheManager

class ZipManager:
    """Manages ZIP file operations for audio files."""
    
    # Supported audio file extensions
    AUDIO_EXTENSIONS = {'.wav', '.mp3', '.ogg'}
    
    DEBUG = False
    
    def __init__(self):
        """Initialize the ZipManager."""
        self.open_zips: Dict[str, zipfile.ZipFile] = {}  # Map of zip_path -> ZipFile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.extracted_files: List[str] = []
        self._progress_callback: Optional[Callable[[str, int], None]] = None
        self.cache_manager = CacheManager()
    
    def set_progress_callback(self, callback: Callable[[str, int], None]):
        """Set a callback function for progress updates.
        
        Args:
            callback: Function that takes a status message and progress value (0-100)
        """
        self._progress_callback = callback
    
    def _update_progress(self, status: str, progress: int):
        """Update progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(status, progress)
            QApplication.processEvents()  # Force UI update
    
    def _validate_zip(self, zip_path: str) -> Tuple[Optional[str], Optional[zipfile.ZipFile]]:
        """Validate ZIP file integrity with progress reporting.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Tuple of (error message if invalid, ZipFile object if valid)
        """
        try:
            # Quick validation of ZIP structure
            zip_file = zipfile.ZipFile(zip_path, 'r')
            
            # Just check if we can read the central directory
            try:    
                # Get list of audio files
                audio_files = [
                    zinfo for zinfo in zip_file.filelist
                    if Path(zinfo.filename).suffix.lower() in self.AUDIO_EXTENSIONS
                ]
                
                if not audio_files:
                    self._update_progress("No audio files found in ZIP", 100)
                    return "No audio files found", None
                
                self._update_progress(f"Found {len(audio_files)} audio files", 100)
                
            except Exception as e:
                return f"Could not read ZIP directory: {e}", None
            
            return None, zip_file
                
        except zipfile.BadZipFile as e:
            logging.error(f"Invalid ZIP file: {e}")
            return "ZIP file is invalid", None
        except Exception as e:
            logging.error(f"Error validating ZIP: {e}")
            return str(e), None

    def load_zip(self, zip_path: str) -> dict:
        """
        Load and validate a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            dict: Dictionary containing timing information
            
        Raises:
            ValueError: If the file is not a valid ZIP file
            FileNotFoundError: If the file doesn't exist
        """
        start_time = time.time()
        timing_info = {
            'total_time': 0,
            'used_cache': False,
            'steps': {}
        }
        
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        try:
            self._update_progress("Checking cache...", 0)
            cache_start = time.time()
            
            # Try to get cached metadata
            cached_metadata = self.cache_manager.get_cached_metadata(zip_path)
            cache_time = time.time() - cache_start
            timing_info['steps']['cache_lookup'] = cache_time
            if self.DEBUG: print(f"[DEBUG] Cache lookup took {cache_time:.2f} seconds")
            
            if cached_metadata is not None:
                # We have valid cached metadata, no need to open the ZIP
                timing_info['used_cache'] = True
                timing_info['total_time'] = time.time() - start_time
                if self.DEBUG:
                    print("\n[DEBUG] ZIP Loading Performance Summary:")
                    print(f"Total time: {timing_info['total_time']:.2f} seconds")
                    print(f"- Cache lookup: {timing_info['steps']['cache_lookup']:.2f} seconds")
                    print("(Using cached metadata)")
                return timing_info
            
            # If we don't have valid cache, proceed with opening and validating the ZIP
            self._update_progress("Opening and validating ZIP file...", 0)
            open_start = time.time()
            
            # Check if ZIP is already open
            if zip_path in self.open_zips:
                self._update_progress("ZIP file already loaded", 100)
                return {'total_time': 0, 'used_cache': True, 'steps': {'opening': 0}}
            
            # Validate and get the ZipFile object in one step
            validate_start = time.time()
            error, zip_file = self._validate_zip(zip_path)
            if error:
                raise ValueError(error)
            
            # Store the validated ZipFile object
            self.open_zips[zip_path] = zip_file
            
            validate_time = time.time() - validate_start
            timing_info['steps']['validation'] = validate_time
            if self.DEBUG: print(f"[DEBUG] ZIP validation took {validate_time:.2f} seconds")
            
            # Get list of audio files (already sorted)
            list_start = time.time()
            audio_files = self.list_audio_files(zip_path)
            list_time = time.time() - list_start
            timing_info['steps']['listing'] = list_time
            if self.DEBUG: print(f"[DEBUG] Listing audio files took {list_time:.2f} seconds")
            
            # Extract metadata for each audio file
            metadata_start = time.time()
            file_metadata = {}
            total_files = len(audio_files)
            
            # Process files in batches for better performance
            BATCH_SIZE = 50
            for i in range(0, total_files, BATCH_SIZE):
                batch = audio_files[i:i + BATCH_SIZE]
                for file_path in batch:
                    try:
                        # Get basic metadata from ZIP info without reading the file
                        zip_info = self.open_zips[zip_path].getinfo(file_path)
                        file_metadata[file_path] = {
                            'size': zip_info.file_size,
                            'timestamp': zip_info.date_time
                        }
                        
                        # Get duration for the file
                        duration = self.get_audio_duration(zip_path, file_path)
                        if duration is not None:
                            file_metadata[file_path]['duration_ms'] = duration
                            
                    except Exception as e:
                        logging.warning(f"Failed to get metadata for {file_path}: {e}")
                        continue
                
                # Update progress for batch
                progress = int((i + len(batch)) / total_files * 100)
                self._update_progress(f"Extracting metadata ({i + len(batch)}/{total_files})...", progress)
            
            metadata_time = time.time() - metadata_start
            timing_info['steps']['metadata'] = metadata_time
            if self.DEBUG: print(f"[DEBUG] Extracting metadata took {metadata_time:.2f} seconds")
            
            # Cache the metadata with durations
            cache_write_start = time.time()
            self.cache_manager.cache_metadata(zip_path, {
                'audio_files': audio_files,  # Already sorted
                'total_files': len(self.open_zips[zip_path].filelist),
                'file_metadata': file_metadata
            })
            cache_write_time = time.time() - cache_write_start
            timing_info['steps']['cache_write'] = cache_write_time
            if self.DEBUG: print(f"[DEBUG] Writing cache took {cache_write_time:.2f} seconds")
            
            self._update_progress("ZIP file loaded successfully", 100)
            
            total_time = time.time() - start_time
            timing_info['total_time'] = total_time
            
            if self.DEBUG:
                print("\n[DEBUG] ZIP Loading Performance Summary:")
                print(f"Total time: {total_time:.2f} seconds")
                print(f"- Cache lookup: {timing_info['steps']['cache_lookup']:.2f} seconds")
                print(f"- ZIP validation: {timing_info['steps']['validation']:.2f} seconds")
                print(f"- Listing files: {timing_info['steps']['listing']:.2f} seconds")
                print(f"- Extracting metadata: {timing_info['steps']['metadata']:.2f} seconds")
                print(f"- Writing cache: {timing_info['steps']['cache_write']:.2f} seconds")
                print(f"- Total time: {total_time:.2f} seconds")
            
            return timing_info
            
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid ZIP file: {zip_path}")
    
    def list_audio_files(self, zip_path: str) -> List[str]:
        """
        List all audio files in a ZIP.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            List of audio file names in the ZIP, sorted by folder and filename
            
        Raises:
            RuntimeError: If the ZIP file is not loaded and no cache is available
        """
        # Try to get from cache first
        cached_metadata = self.cache_manager.get_cached_metadata(zip_path)
        if cached_metadata and 'audio_files' in cached_metadata:
            return cached_metadata['audio_files']
        
        # If no cache, ensure ZIP is open and get files
        self._ensure_zip_open(zip_path)
        
        self._update_progress("Scanning for audio files...", 0)
        all_files = self.open_zips[zip_path].namelist()
        total_files = len(all_files)
        
        # Group files by folder for better organization
        files_by_folder = {}
        for name in all_files:
            # Skip system files
            if name.startswith('__MACOSX') or name.startswith('._'):
                continue
                
            if Path(name).suffix.lower() in self.AUDIO_EXTENSIONS:
                folder = os.path.dirname(name)
                if folder not in files_by_folder:
                    files_by_folder[folder] = []
                files_by_folder[folder].append(name)
        
        # Sort folders and files within folders
        sorted_folders = sorted(files_by_folder.keys(), key=str.lower)
        audio_files = []
        
        # Add files in sorted order
        for folder in sorted_folders:
            # Sort files within each folder
            files_by_folder[folder].sort(key=lambda x: os.path.basename(x).lower())
            audio_files.extend(files_by_folder[folder])
        
        self._update_progress(f"Found {len(audio_files)} audio files", 100)
        return audio_files
    
    def _ensure_zip_open(self, zip_path: str):
        """Ensure a ZIP file is open, opening it if necessary.
        
        Args:
            zip_path: Path to the ZIP file
            
        Raises:
            ValueError: If the file is not a valid ZIP file
            FileNotFoundError: If the file doesn't exist
        """
        if zip_path not in self.open_zips:
            if not os.path.exists(zip_path):
                raise FileNotFoundError(f"ZIP file not found: {zip_path}")
            
            try:
                self.open_zips[zip_path] = zipfile.ZipFile(zip_path, 'r')
            except zipfile.BadZipFile:
                raise ValueError(f"Invalid ZIP file: {zip_path}")
    
    def read_file(self, zip_path: str, file_name: str) -> bytes:
        """
        Read entire file contents from a ZIP into memory.
        
        Args:
            zip_path: Path to the ZIP file
            file_name: Name of the file to read
            
        Returns:
            File contents as bytes
            
        Raises:
            RuntimeError: If the ZIP file is not loaded
            KeyError: If the file doesn't exist in the ZIP
            OSError: If file reading fails
        """
        self._ensure_zip_open(zip_path)
        
        if file_name not in self.open_zips[zip_path].namelist():
            raise KeyError(f"File not found in ZIP: {file_name}")
        
        try:
            with self.open_zips[zip_path].open(file_name) as file:
                return file.read()
        except Exception as e:
            raise OSError(f"Error reading file {file_name}: {str(e)}")
    
    def stream_file(self, zip_path: str, file_name: str, chunk_size: int = 8192):
        """
        Stream a file from a ZIP archive without extracting it.
        
        Args:
            zip_path: Path to the ZIP file
            file_name: Name of the file to stream
            chunk_size: Size of each chunk to yield
            
        Yields:
            Chunks of file data
            
        Raises:
            RuntimeError: If the ZIP file is not loaded
            KeyError: If the file doesn't exist in the ZIP
        """
        self._ensure_zip_open(zip_path)
        
        if file_name not in self.open_zips[zip_path].namelist():
            raise KeyError(f"File not found in ZIP: {file_name}")
        
        with self.open_zips[zip_path].open(file_name) as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    def extract_file(self, zip_path: str, file_name: str, output_dir: str) -> str:
        """
        Extract a single file from a ZIP.
        
        Args:
            zip_path: Path to the ZIP file
            file_name: Name of the file to extract
            output_dir: Directory to extract the file to
            
        Returns:
            Path to the extracted file
            
        Raises:
            RuntimeError: If the ZIP file is not loaded
            KeyError: If the file doesn't exist in the ZIP
            OSError: If file extraction fails
        """
        self._ensure_zip_open(zip_path)
        
        if file_name not in self.open_zips[zip_path].namelist():
            raise KeyError(f"File not found in ZIP: {file_name}")
        
        try:
            # Get just the filename without any directory structure
            base_name = os.path.basename(file_name)
            output_path = os.path.join(output_dir, base_name)
            
            logging.info(f"Extracting {file_name} to {output_path}")
            
            # Extract the file
            with self.open_zips[zip_path].open(file_name) as source:
                with open(output_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
            
            # Verify the file was extracted successfully
            if not os.path.exists(output_path):
                logging.error(f"File was not extracted successfully: {output_path}")
                raise OSError(f"Failed to extract file: {file_name}")
                
            # Track extracted file
            self.extracted_files.append(output_path)
            logging.info(f"Successfully extracted {file_name} to {output_path}")
            
            return output_path
        except Exception as e:
            logging.error(f"Error extracting file {file_name}: {str(e)}", exc_info=True)
            raise OSError(f"Error extracting file {file_name}: {str(e)}")
    
    def extract_files(self, zip_path: str, file_names: List[str], output_dir: str) -> List[str]:
        """
        Extract multiple files from a ZIP.
        
        Args:
            zip_path: Path to the ZIP file
            file_names: List of file names to extract
            output_dir: Directory to extract the files to
            
        Returns:
            List of paths to the extracted files
            
        Raises:
            RuntimeError: If the ZIP file is not loaded
            KeyError: If any file doesn't exist in the ZIP
        """
        logging.info(f"Starting batch extraction of {len(file_names)} files to {output_dir}")
        extracted_paths = []
        
        for i, name in enumerate(file_names):
            try:
                path = self.extract_file(zip_path, name, output_dir)
                extracted_paths.append(path)
                logging.info(f"Progress: {i+1}/{len(file_names)} files extracted")
            except Exception as e:
                logging.error(f"Failed to extract {name}: {str(e)}", exc_info=True)
                raise
        
        logging.info(f"Completed batch extraction. Successfully extracted {len(extracted_paths)} files")
        return extracted_paths
    
    def cleanup(self) -> None:
        """Clean up temporary files and close all ZIP files."""
        # Remove extracted files
        for file_path in self.extracted_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass  # Ignore errors during cleanup
        
        self.extracted_files.clear()
        
        # Close and cleanup temporary directory
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None
        
        # Close all ZIP files
        for zip_file in self.open_zips.values():
            try:
                zip_file.close()
            except Exception:
                pass
        
        self.open_zips.clear()
    
    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()
    
    def close_zip(self, zip_path: str):
        """Close a specific ZIP file.
        
        Args:
            zip_path: Path to the ZIP file to close
        """
        if zip_path in self.open_zips:
            try:
                self.open_zips[zip_path].close()
            except Exception:
                pass
            del self.open_zips[zip_path]
    
    def get_open_zips(self) -> List[str]:
        """Get list of currently open ZIP files.
        
        Returns:
            List of paths to open ZIP files
        """
        return list(self.open_zips.keys())
    
    def get_file_duration(self, zip_path: str, file_name: str) -> Optional[int]:
        """
        Get the duration of a file, using cache if available.
        
        Args:
            zip_path: Path to the ZIP file
            file_name: Name of the audio file in the ZIP
            
        Returns:
            Duration in milliseconds, or None if duration couldn't be determined
        """
        print(f"\n[DEBUG] Getting duration for {file_name}")
        
        # Try to get from cache first
        cached_metadata = self.cache_manager.get_cached_metadata(zip_path)
        if cached_metadata and 'file_metadata' in cached_metadata:
            file_metadata = cached_metadata['file_metadata'].get(file_name, {})
            if 'duration_ms' in file_metadata:
                if self.DEBUG: print(f"[DEBUG] Found duration in cache: {file_metadata['duration_ms']}ms")
                return file_metadata['duration_ms']
            else:
                if self.DEBUG: print(f"[DEBUG] No duration in cache for {file_name}")
        else:
            if self.DEBUG: print(f"[DEBUG] No cache found for {zip_path}")
        
        # If not in cache, get it and cache it
        if self.DEBUG: print(f"[DEBUG] Getting duration from file...")
        duration = self.get_audio_duration(zip_path, file_name)
        if duration is not None:
            if self.DEBUG: print(f"[DEBUG] Got duration: {duration}ms")
            # Update cache with duration
            if cached_metadata is None:
                if self.DEBUG: print(f"[DEBUG] Creating new cache structure")
                cached_metadata = {
                    'audio_files': self.list_audio_files(zip_path),
                    'total_files': len(self.open_zips[zip_path].filelist),
                    'file_metadata': {}
                }
            
            if 'file_metadata' not in cached_metadata:
                if self.DEBUG: print(f"[DEBUG] Creating file_metadata dictionary")
                cached_metadata['file_metadata'] = {}
            
            if file_name not in cached_metadata['file_metadata']:
                if self.DEBUG: print(f"[DEBUG] Adding basic metadata for {file_name}")
                # Get basic metadata from ZIP info
                zip_info = self.open_zips[zip_path].getinfo(file_name)
                cached_metadata['file_metadata'][file_name] = {
                    'size': zip_info.file_size,
                    'timestamp': zip_info.date_time
                }
            
            # Add duration to metadata
            if self.DEBUG: print(f"[DEBUG] Adding duration to cache")
            cached_metadata['file_metadata'][file_name]['duration_ms'] = duration
            
            # Save updated cache
            if self.DEBUG: print(f"[DEBUG] Saving updated cache")
            self.cache_manager.cache_metadata(zip_path, cached_metadata)
        else:
            if self.DEBUG: print(f"[DEBUG] Could not get duration for {file_name}")
        
        return duration

    def get_full_audio_metadata(self, zip_path: str, file_name: str, max_header_size: int = 1024 * 1024) -> Optional[dict]:
        """
        Get full audio metadata for a file.
        
        Args:
            zip_path: Path to the ZIP file
            file_name: Name of the audio file in the ZIP
            max_header_size: Maximum number of bytes to read for header (default 1MB)
            
        Returns:
            Dictionary containing all available metadata, or None if metadata couldn't be determined
            
        Raises:
            RuntimeError: If the ZIP file is not loaded and no cache is available
            KeyError: If the file doesn't exist in the ZIP
        """
        if self.DEBUG: print(f"[DEBUG] Getting full audio metadata for {file_name}")
        
        # Try to get from cache first
        cached_metadata = self.cache_manager.get_cached_metadata(zip_path)
        if cached_metadata and 'file_metadata' in cached_metadata:
            file_metadata = cached_metadata['file_metadata'].get(file_name, {})
            if 'full_metadata' in file_metadata:
                if self.DEBUG: print(f"[DEBUG] Got full metadata from cache")
                return file_metadata['full_metadata']
        
        # If not in cache, ensure ZIP is open and get metadata
        self._ensure_zip_open(zip_path)
        
        if file_name not in self.open_zips[zip_path].namelist():
            raise KeyError(f"File not found in ZIP: {file_name}")
        
        try:
            from tinytag import TinyTag
            from io import BytesIO
            
            time_start = time.time()
            
            # Get file info to check size
            zip_info = self.open_zips[zip_path].getinfo(file_name)
            
            # For very small files, read the whole thing
            if zip_info.file_size <= max_header_size:
                if self.DEBUG: print(f"[DEBUG] {file_name} File size: {zip_info.file_size} bytes. Reading entire file (small file)")
                with self.open_zips[zip_path].open(file_name) as zip_file:
                    file_data = zip_file.read()
            else:
                # For larger files, only read the header portion
                if self.DEBUG: print(f"[DEBUG] {file_name} File size: {zip_info.file_size} bytes. Reading header only (max {max_header_size} bytes)")
                with self.open_zips[zip_path].open(file_name) as zip_file:
                    file_data = zip_file.read(max_header_size)
            
            # Create a BytesIO object and use it with file_obj parameter
            file_obj = BytesIO(file_data)
            tag = TinyTag.get(file_obj=file_obj)
            if tag is not None:
                metadata = {}
                
                # Basic file info
                if tag.filesize:
                    metadata['filesize'] = tag.filesize
                
                # Audio format info
                if tag.duration is not None:
                    metadata['duration_ms'] = int(tag.duration * 1000)
                if tag.channels is not None:
                    metadata['channels'] = tag.channels
                if tag.bitrate is not None:
                    metadata['bitrate'] = tag.bitrate
                if tag.bitdepth is not None:
                    metadata['bit_depth'] = tag.bitdepth
                if tag.samplerate is not None:
                    metadata['sample_rate'] = tag.samplerate
                
                # Music metadata
                if tag.artist:
                    metadata['artist'] = tag.artist
                if tag.albumartist:
                    metadata['album_artist'] = tag.albumartist
                if tag.composer:
                    metadata['composer'] = tag.composer
                if tag.album:
                    metadata['album'] = tag.album
                if tag.disc is not None:
                    metadata['disc'] = tag.disc
                if tag.disc_total is not None:
                    metadata['disc_total'] = tag.disc_total
                if tag.title:
                    metadata['title'] = tag.title
                if tag.track is not None:
                    metadata['track'] = tag.track
                if tag.track_total is not None:
                    metadata['track_total'] = tag.track_total
                if tag.genre:
                    metadata['genre'] = tag.genre
                if tag.year:
                    metadata['year'] = tag.year
                if tag.comment:
                    metadata['comment'] = tag.comment
                # Add any other fields that might be present
                if hasattr(tag, 'other') and tag.other:
                    for key, value in tag.other.items():
                        if value:
                            metadata[key] = str(value)
                
                if self.DEBUG: print(f"[DEBUG] Got full metadata. Time took {time.time() - time_start:.2f} seconds. Metadata: {metadata}")
                
                # Update cache with full metadata
                if cached_metadata is None:
                    cached_metadata = {
                        'audio_files': self.list_audio_files(zip_path),
                        'total_files': len(self.open_zips[zip_path].filelist),
                        'file_metadata': {}
                    }
                
                if 'file_metadata' not in cached_metadata:
                    cached_metadata['file_metadata'] = {}
                
                if file_name not in cached_metadata['file_metadata']:
                    cached_metadata['file_metadata'][file_name] = {
                        'size': zip_info.file_size,
                        'timestamp': zip_info.date_time
                    }
                
                # Add full metadata to cache
                cached_metadata['file_metadata'][file_name]['full_metadata'] = metadata
                
                # Save updated cache
                self.cache_manager.cache_metadata(zip_path, cached_metadata)
                
                return metadata
            
            if self.DEBUG: print(f"[DEBUG] Could not get metadata for {file_name}")
            return None
            
        except Exception as e:
            if self.DEBUG: print(f"[DEBUG] Error getting metadata: {str(e)}")
            return None

    def get_audio_duration(self, zip_path: str, file_name: str, max_header_size: int = 1024 * 1024) -> Optional[int]:
        """
        Get audio duration in milliseconds without extracting the file.
        Only reads the header portion of the file to get duration.
        
        Args:
            zip_path: Path to the ZIP file
            file_name: Name of the audio file in the ZIP
            max_header_size: Maximum number of bytes to read for header (default 1MB)
            
        Returns:
            Duration in milliseconds, or None if duration couldn't be determined
            
        Raises:
            RuntimeError: If the ZIP file is not loaded and no cache is available
            KeyError: If the file doesn't exist in the ZIP
        """
        if self.DEBUG: print(f"[DEBUG] Getting audio duration for {file_name}")
        
        # Try to get from cache first
        cached_metadata = self.cache_manager.get_cached_metadata(zip_path)
        if cached_metadata and 'file_metadata' in cached_metadata:
            file_metadata = cached_metadata['file_metadata'].get(file_name, {})
            if 'duration_ms' in file_metadata:
                if self.DEBUG: print(f"[DEBUG] Got duration from cache: {file_metadata['duration_ms']}ms")
                return file_metadata['duration_ms']
        
        # If not in cache, ensure ZIP is open and get duration
        self._ensure_zip_open(zip_path)
        
        if file_name not in self.open_zips[zip_path].namelist():
            raise KeyError(f"File not found in ZIP: {file_name}")
        
        try:
            import mutagen
            from io import BytesIO
            
            time_start = time.time()
            
            # Get file info to check size
            zip_info = self.open_zips[zip_path].getinfo(file_name)
            
            # For very small files, read the whole thing
            if zip_info.file_size <= max_header_size:
                if self.DEBUG: print(f"[DEBUG] {file_name} File size: {zip_info.file_size} bytes. Reading entire file (small file)")
                with self.open_zips[zip_path].open(file_name) as zip_file:
                    file_data = zip_file.read()
            else:
                # For larger files, only read the header portion
                if self.DEBUG: print(f"[DEBUG] {file_name} File size: {zip_info.file_size} bytes. Reading header only (max {max_header_size} bytes)")
                with self.open_zips[zip_path].open(file_name) as zip_file:
                    file_data = zip_file.read(max_header_size)
            
            # Create a BytesIO object for mutagen
            file_obj = BytesIO(file_data)
            
            # Use mutagen to get the duration
            audio = mutagen.File(file_obj)
            if audio is not None and hasattr(audio.info, 'length'):
                duration = int(audio.info.length * 1000)  # Convert to milliseconds
                if self.DEBUG: print(f"[DEBUG] Got duration from header: {duration}ms. Time took {time.time() - time_start:.2f} seconds")
                return duration
            
            # If we couldn't get duration from header, try reading more
            if zip_info.file_size > max_header_size:
                if self.DEBUG: print(f"[DEBUG] Could not get duration from header, trying full file")
                with self.open_zips[zip_path].open(file_name) as zip_file:
                    file_data = zip_file.read()
                file_obj = BytesIO(file_data)
                audio = mutagen.File(file_obj)
                if audio is not None and hasattr(audio.info, 'length'):
                    duration = int(audio.info.length * 1000)
                    if self.DEBUG: print(f"[DEBUG] Got duration from full file: {duration}ms. Time took {time.time() - time_start:.2f} seconds")
                    return duration
                
        except Exception as e:
            if self.DEBUG: print(f"[DEBUG] Error getting duration: {e}")
            logging.warning(f"Failed to get duration for {file_name}: {e}")
        
        if self.DEBUG: print(f"[DEBUG] Could not determine duration")
        return None 