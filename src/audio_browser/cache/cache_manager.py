import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
import mutagen
import io
import numpy as np
import wave

class CacheManager:
    """Manages caching of ZIP file metadata for faster loading."""
    
    DEBUG = False
    
    def __init__(self, cache_dir: str = None):
        """Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files. If None, uses default location.
        """
        if cache_dir is None:
            # Use user's home directory for cache
            self.cache_dir = os.path.join(os.path.expanduser("~"), ".audio_browser", "cache")
        else:
            self.cache_dir = cache_dir
            
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache index file to track all cached ZIPs
        self.cache_index_file = os.path.join(self.cache_dir, "cache_index.json")
        
        # Load cache index
        self.cache_index = self._load_cache_index()
    
    def _get_cache_file_path(self, zip_path: str) -> str:
        """Get the cache file path for a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Path to the cache file
        """
        # Get just the filename and add .cache extension
        zip_filename = os.path.basename(zip_path)
        return os.path.join(self.cache_dir, f"{zip_filename}.cache")
    
    def _load_cache_index(self) -> Dict[str, str]:
        """Load the cache index file."""
        if not os.path.exists(self.cache_index_file):
            return {}
            
        try:
            with open(self.cache_index_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading cache index: {e}")
            return {}
    
    def _save_cache_index(self):
        """Save the cache index file."""
        try:
            with open(self.cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving cache index: {e}")
    
    def _load_cache(self, zip_path: str) -> Dict:
        """Load cache for a specific ZIP file."""
        cache_file = self._get_cache_file_path(zip_path)
        if not os.path.exists(cache_file):
            return {}
            
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading cache for {zip_path}: {e}")
            return {}
    
    def _save_cache(self, zip_path: str, cache_data: Dict):
        """Save cache for a specific ZIP file."""
        cache_file = self._get_cache_file_path(zip_path)
        try:
            if self.DEBUG: print(f"[DEBUG] Saving cache to: {cache_file}")
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            if self.DEBUG: print(f"[DEBUG] Cache saved successfully")
        except Exception as e:
            logging.error(f"Error saving cache for {zip_path}: {e}")
            if self.DEBUG: print(f"[DEBUG] Error saving cache: {e}")
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _extract_audio_metadata(self, file_bytes: bytes) -> Dict:
        """Extract metadata from audio file bytes.
        
        Args:
            file_bytes: Raw bytes of the audio file
            
        Returns:
            Dictionary containing audio metadata
        """
        metadata = {}
        try:
            # Use mutagen to get basic audio info
            audio = mutagen.File(io.BytesIO(file_bytes))
            if audio is not None:
                metadata.update({
                    'duration_ms': int(audio.info.length * 1000),
                    'sample_rate': getattr(audio.info, 'sample_rate', None),
                    'channels': getattr(audio.info, 'channels', None),
                    'bit_depth': getattr(audio.info, 'bits_per_sample', None),
                    'format': audio.info.__class__.__name__.lower()
                })
            
        except Exception as e:
            logging.warning(f"Failed to extract audio metadata: {e}")
        
        return metadata
    
    def _calculate_file_stats(self, file_path: str) -> Dict[str, int]:
        """Get file stats (size and modification time) for cache validation."""
        stats = os.stat(file_path)
        return {
            'size': stats.st_size,
            'mtime': int(stats.st_mtime)
        }
    
    def get_cached_metadata(self, zip_path: str) -> Optional[Dict]:
        """Get cached metadata for a ZIP file if it exists and is valid."""
        if zip_path not in self.cache_index:
            return None
            
        cache_data = self._load_cache(zip_path)
        if not cache_data:
            return None
            
        # Check if file still exists
        if not os.path.exists(zip_path):
            self.remove_from_cache(zip_path)
            return None
            
        # Handle both old (checksum) and new (file_stats) cache formats
        current_stats = self._calculate_file_stats(zip_path)
        
        # Check if we have the new format
        if 'file_stats' in cache_data:
            if (current_stats['size'] != cache_data['file_stats']['size'] or 
                current_stats['mtime'] != cache_data['file_stats']['mtime']):
                self.remove_from_cache(zip_path)
                return None
        # Handle old format with checksum
        elif 'checksum' in cache_data:
            # For old format, we'll just check the file size as a quick validation
            if current_stats['size'] != cache_data.get('size', 0):
                self.remove_from_cache(zip_path)
                return None
            # If size matches, update to new format
            cache_data['file_stats'] = current_stats
            self._save_cache(zip_path, cache_data)
        else:
            # Invalid cache format
            self.remove_from_cache(zip_path)
            return None
            
        return cache_data['metadata']
    
    def cache_metadata(self, zip_path: str, metadata: Dict, file_bytes: Optional[Dict[str, bytes]] = None):
        """Cache metadata for a ZIP file."""
        if self.DEBUG: print(f"[DEBUG] Caching metadata for: {zip_path}")
        file_stats = self._calculate_file_stats(zip_path)
        
        # Extract additional audio metadata if file bytes are provided
        if file_bytes is not None:
            # Process each file's bytes to extract metadata
            for file_path, bytes_data in file_bytes.items():
                if file_path in metadata.get('file_metadata', {}):
                    audio_metadata = self._extract_audio_metadata(bytes_data)
                    metadata['file_metadata'][file_path].update(audio_metadata)
        
        cache_data = {
            'file_stats': file_stats,
            'metadata': metadata,
            'timestamp': time.time()
        }
        
        # Save cache data
        self._save_cache(zip_path, cache_data)
        
        # Update cache index
        self.cache_index[zip_path] = self._get_cache_file_path(zip_path)
        self._save_cache_index()
    
    def clear_cache(self):
        """Clear all cached data."""
        # Remove all cache files
        for cache_file in self.cache_index.values():
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except Exception as e:
                logging.error(f"Error removing cache file {cache_file}: {e}")
        
        # Clear index
        self.cache_index.clear()
        self._save_cache_index()
        
    def remove_from_cache(self, zip_path: str):
        """Remove a specific ZIP file from cache."""
        if zip_path in self.cache_index:
            cache_file = self.cache_index[zip_path]
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except Exception as e:
                logging.error(f"Error removing cache file {cache_file}: {e}")
            
            del self.cache_index[zip_path]
            self._save_cache_index()
    
    def get_cache_size(self) -> int:
        """Get the total size of cached data in bytes."""
        total_size = 0
        for cache_file in self.cache_index.values():
            if os.path.exists(cache_file):
                total_size += os.path.getsize(cache_file)
        return total_size
    
    def list_cached_zips(self) -> List[str]:
        """Get a list of all cached ZIP files."""
        return list(self.cache_index.keys()) 