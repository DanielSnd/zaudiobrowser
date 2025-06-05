import os
from typing import List, Dict, Any
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QBrush, QColor

class AudioFileModel(QAbstractItemModel):
    """Data model for organizing audio files in a hierarchical structure."""
    
    def __init__(self):
        super().__init__()
        self.files: List[Dict[str, Any]] = []  # List of all files
        self.folder_states: Dict[str, bool] = {}  # Track if folders are expanded
        self.folder_files: Dict[str, List[Dict[str, Any]]] = {}  # Files grouped by folder
        self.checked_files: set = set()  # Set of checked file paths
        
    def data(self, index, role=Qt.DisplayRole):
        """Return data for the given role and index."""
        if not index.isValid():
            return None
            
        if role == Qt.BackgroundRole:
            # Get the item's row
            row = index.row()
            # Return alternating colors for even/odd rows
            if row % 2 == 0:
                return QBrush(QColor("#f0f0f0"))  # Light gray for even rows
            return QBrush(QColor("#ffffff"))  # White for odd rows
            
        return None
        
    def add_file(self, file_path: str, file_bytes=None, zip_path=None, file_metadata=None, zip_manager=None):
        """Add a file to the model."""
        file_data = {
            'path': file_path,
            'folder': os.path.dirname(file_path),
            'zip_path': zip_path,
            'metadata': file_metadata or {},
            'file_bytes': file_bytes,
            'zip_manager': zip_manager
        }
        self.files.append(file_data)
        
        # Add to folder grouping
        folder = file_data['folder']
        if folder not in self.folder_files:
            self.folder_files[folder] = []
        self.folder_files[folder].append(file_data)
        
        # Initialize folder state if new
        if folder not in self.folder_states:
            self.folder_states[folder] = False
    
    def sort_files(self):
        """Sort files within each folder."""
        # Sort files within each folder
        for folder in self.folder_files:
            self.folder_files[folder].sort(key=lambda x: os.path.basename(x['path']).lower())
        
        # Sort the folder list itself
        self.folder_files = dict(sorted(self.folder_files.items(), key=lambda x: x[0].lower()))
    
    def get_folder_files(self, folder: str) -> List[Dict[str, Any]]:
        """Get files in a specific folder."""
        return self.folder_files.get(folder, [])
    
    def get_folders(self) -> List[str]:
        """Get list of all folders."""
        return sorted(self.folder_files.keys(), key=str.lower)
    
    def toggle_folder(self, folder: str) -> bool:
        """Toggle folder expansion state."""
        if folder in self.folder_states:
            self.folder_states[folder] = not self.folder_states[folder]
            return self.folder_states[folder]
        return False
    
    def is_folder_expanded(self, folder: str) -> bool:
        """Check if a folder is expanded."""
        return self.folder_states.get(folder, False)
    
    def get_checked_files(self) -> List[str]:
        """Get list of checked file paths."""
        return list(self.checked_files)
    
    def set_file_checked(self, file_path: str, checked: bool):
        """Set a file's checked state."""
        if checked:
            self.checked_files.add(file_path)
        else:
            self.checked_files.discard(file_path)
    
    def clear(self):
        """Clear all data."""
        self.files.clear()
        self.folder_states.clear()
        self.folder_files.clear()
        self.checked_files.clear()
    
    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows under the given parent."""
        if not parent.isValid():
            return len(self.folder_files)
        return 0  # For now, we don't support nested items
        
    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns for the given parent."""
        return 3  # Name, Duration, Size
        
    def index(self, row, column, parent=QModelIndex()):
        """Return the index of the item in the model."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        return self.createIndex(row, column)
        
    def parent(self, index):
        """Return the parent of the model index."""
        return QModelIndex()  # We don't have a parent-child relationship yet
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return the header data for the given section."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            headers = ["Name", "Duration", "Size"]
            if 0 <= section < len(headers):
                return headers[section]
        return None 