import json
import os
from pathlib import Path
from typing import List, Dict, Any

class ConfigManager:
    """Manages application configuration and settings."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / '.config' / 'audio_browser'
        self.config_file = self.config_dir / 'config.json'
        self.config: Dict[str, Any] = {
            'recent_files': [],
            'recent_libraries': [],
            'recent_folders': [],
            'max_recent_files': 10,
            'volume': 100,
            'theme': 'System',
            'file_associations': ['.wav', '.mp3', '.ogg']
        }
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception:
            # If loading fails, use default config
            pass
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            # If saving fails, continue with in-memory config
            pass
    
    def add_recent_file(self, file_path: str):
        """Add a file to the recent files list.
        
        Args:
            file_path: Path to the file to add
        """
        # Remove if already exists
        if file_path in self.config['recent_files']:
            self.config['recent_files'].remove(file_path)
        
        # Add to front of list
        self.config['recent_files'].insert(0, file_path)
        
        # Trim list if too long
        if len(self.config['recent_files']) > self.config['max_recent_files']:
            self.config['recent_files'] = self.config['recent_files'][:self.config['max_recent_files']]
        
        self._save_config()
    
    def add_recent_library(self, file_path: str):
        """Add a library to the recent libraries list.
        
        Args:
            file_path: Path to the library file to add
        """
        # Remove if already exists
        if file_path in self.config['recent_libraries']:
            self.config['recent_libraries'].remove(file_path)
        
        # Add to front of list
        self.config['recent_libraries'].insert(0, file_path)
        
        # Trim list if too long
        if len(self.config['recent_libraries']) > self.config['max_recent_files']:
            self.config['recent_libraries'] = self.config['recent_libraries'][:self.config['max_recent_files']]
        
        self._save_config()

    def add_recent_folder(self, folder_path: str):
        """Add a folder to the recent folders list.
        
        Args:
            folder_path: Path to the folder to add
        """
        # Remove if already exists
        if folder_path in self.config['recent_folders']:
            self.config['recent_folders'].remove(folder_path)
        
        # Add to front of list
        self.config['recent_folders'].insert(0, folder_path)
        
        # Trim list if too long
        if len(self.config['recent_folders']) > self.config['max_recent_files']:
            self.config['recent_folders'] = self.config['recent_folders'][:self.config['max_recent_files']]
        
        self._save_config()

    def get_recent_files(self) -> List[str]:
        """Get the list of recently opened files.
        
        Returns:
            List of recently opened file paths
        """
        return self.config['recent_files']
    
    def get_recent_libraries(self) -> List[str]:
        """Get the list of recently opened libraries.
        
        Returns:
            List of recently opened library paths
        """
        return self.config['recent_libraries']
    
    def get_recent_folders(self) -> List[str]:
        """Get the list of recently opened folders.
        
        Returns:
            List of recently opened folder paths
        """
        return self.config['recent_folders']
    
    def clear_recent_files(self):
        """Clear all recent items lists."""
        self.config['recent_files'] = []
        self.config['recent_libraries'] = []
        self.config['recent_folders'] = []
        self._save_config()
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all application settings.
        
        Returns:
            Dictionary containing all settings
        """
        return {
            'volume': self.config['volume'],
            'theme': self.config['theme'],
            'file_associations': self.config['file_associations']
        }
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update application settings.
        
        Args:
            settings: Dictionary containing settings to update
        """
        self.config.update(settings)
        self._save_config() 