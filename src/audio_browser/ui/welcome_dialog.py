from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
import os

class WelcomeDialog(QDialog):
    """Welcome dialog shown when no file is loaded."""
    
    # Signals
    recent_file_selected = Signal(str)  # Emits selected file path
    recent_library_selected = Signal(str)  # Emits selected library path
    recent_folder_selected = Signal(str)  # Emits selected folder path
    open_zip_clicked = Signal()  # Emitted when Open ZIP button is clicked
    open_library_clicked = Signal()  # Emitted when Open Library button is clicked
    open_folder_clicked = Signal()  # Emitted when Open Folder button is clicked
    
    def __init__(self, recent_files, recent_libraries, recent_folders, parent=None):
        """Initialize the welcome dialog.
        
        Args:
            recent_files (list): List of recent file paths
            recent_libraries (list): List of recent library paths
            recent_folders (list): List of recent folder paths
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Welcome to Audio Browser")
        self.setMinimumWidth(400)
        self._setup_ui(recent_files, recent_libraries, recent_folders)
        
    def _setup_ui(self, recent_files, recent_libraries, recent_folders):
        """Set up the user interface.
        
        Args:
            recent_files (list): List of recent file paths
            recent_libraries (list): List of recent library paths
            recent_folders (list): List of recent folder paths
        """
        layout = QVBoxLayout(self)
        
        # Welcome message
        welcome_label = QLabel("Welcome to Audio Browser!")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(welcome_label)
        
        # Description
        desc_label = QLabel(
            "This application allows you to browse, preview, and extract "
            "audio files from ZIP archives."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Recent files section
        if recent_files:
            layout.addSpacing(10)
            recent_label = QLabel("Recent Files:")
            recent_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(recent_label)
            
            self.recent_files_list = QListWidget()
            for file_path in recent_files:
                item = QListWidgetItem(os.path.basename(file_path))
                item.setToolTip(file_path)
                item.setData(Qt.UserRole, file_path)
                self.recent_files_list.addItem(item)
            
            self.recent_files_list.itemDoubleClicked.connect(self._handle_recent_file)
            layout.addWidget(self.recent_files_list)
        
        # Recent libraries section
        if recent_libraries:
            layout.addSpacing(10)
            libraries_label = QLabel("Recent Libraries:")
            libraries_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(libraries_label)
            
            self.recent_libraries_list = QListWidget()
            for file_path in recent_libraries:
                item = QListWidgetItem(os.path.basename(file_path))
                item.setToolTip(file_path)
                item.setData(Qt.UserRole, file_path)
                self.recent_libraries_list.addItem(item)
            
            self.recent_libraries_list.itemDoubleClicked.connect(self._handle_recent_library)
            layout.addWidget(self.recent_libraries_list)
        
        # Recent folders section
        if recent_folders:
            layout.addSpacing(10)
            folders_label = QLabel("Recent Folders:")
            folders_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(folders_label)
            
            self.recent_folders_list = QListWidget()
            for folder_path in recent_folders:
                item = QListWidgetItem(os.path.basename(folder_path))
                item.setToolTip(folder_path)
                item.setData(Qt.UserRole, folder_path)
                self.recent_folders_list.addItem(item)
            
            self.recent_folders_list.itemDoubleClicked.connect(self._handle_recent_folder)
            layout.addWidget(self.recent_folders_list)
        
        # Show message if no recent items
        if not (recent_files or recent_libraries or recent_folders):
            no_recent_label = QLabel("No recent items")
            layout.addWidget(no_recent_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Open ZIP button
        open_zip_button = QPushButton("Open ZIP File")
        open_zip_button.clicked.connect(self._handle_open_zip)
        button_layout.addWidget(open_zip_button)
        
        # Open Library button
        open_library_button = QPushButton("Open Library")
        open_library_button.clicked.connect(self._handle_open_library)
        button_layout.addWidget(open_library_button)
        
        # Open Folder button
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.clicked.connect(self._handle_open_folder)
        button_layout.addWidget(open_folder_button)
        
        layout.addLayout(button_layout)
        
        # Close button in its own layout
        close_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        close_layout.addStretch()  # Push close button to the right
        close_layout.addWidget(close_button)
        layout.addLayout(close_layout)
    
    def _handle_recent_file(self, item):
        """Handle selection of a recent file.
        
        Args:
            item: The selected list item
        """
        file_path = item.data(Qt.UserRole)
        self.recent_file_selected.emit(file_path)
        self.accept()
    
    def _handle_recent_library(self, item):
        """Handle selection of a recent library.
        
        Args:
            item: The selected list item
        """
        file_path = item.data(Qt.UserRole)
        self.recent_library_selected.emit(file_path)
        self.accept()
    
    def _handle_recent_folder(self, item):
        """Handle selection of a recent folder.
        
        Args:
            item: The selected list item
        """
        folder_path = item.data(Qt.UserRole)
        self.recent_folder_selected.emit(folder_path)
        self.accept()
    
    def _handle_open_zip(self):
        """Handle clicking the Open ZIP File button."""
        self.open_zip_clicked.emit()
        self.accept()
        
    def _handle_open_library(self):
        """Handle clicking the Open Library button."""
        self.open_library_clicked.emit()
        self.accept()
        
    def _handle_open_folder(self):
        """Handle clicking the Open Folder button."""
        self.open_folder_clicked.emit()
        self.accept() 