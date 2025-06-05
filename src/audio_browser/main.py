#!/usr/bin/env python3

import sys
import os
import logging
import time
import json
import argparse
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QLineEdit, QLabel,
    QDialog
)
from PySide6.QtCore import Qt, QUrl, QObject, QEvent
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence, QShortcut, QPalette
import mutagen
import io

from audio_browser.ui.audio_file_tree_widget import AudioFileTreeWidget
from audio_browser.ui.control_panel import ControlPanel
from audio_browser.ui.status_bar import StatusBar
from audio_browser.ui.settings_dialog import SettingsDialog
from audio_browser.ui.welcome_dialog import WelcomeDialog
from audio_browser.player.audio_player import AudioPlayer
from audio_browser.zip.zip_manager import ZipManager
from audio_browser.config.config_manager import ConfigManager
from audio_browser import __version__

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Browser")
        self.setMinimumSize(1280, 720)
        self._playback_state = "stopped"
        self._last_played_file = None
        self.welcome_dialog = None  # Initialize welcome_dialog attribute
        
        # Set focus policy to receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Initialize components
        self._init_components()
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def _init_components(self):
        """Initialize all UI components."""
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create UI components
        self.file_list = AudioFileTreeWidget()
        self.control_panel = ControlPanel()
        self.status_bar = StatusBar()
        self.audio_player = AudioPlayer()
        self.zip_manager = ZipManager()
        self.config_manager = ConfigManager()
        
        # Set up status bar
        self.setStatusBar(self.status_bar)
        
        # Set up progress callback for zip manager
        self.zip_manager.set_progress_callback(self._handle_zip_progress)
        
        # Add spacebar shortcut
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.space_shortcut.activated.connect(self.control_panel._handle_play_click)
        self.space_shortcut.setAutoRepeat(False)
        
        self.c_shortcut = QShortcut(QKeySequence(Qt.Key_C), self)
        self.c_shortcut.activated.connect(self.file_list.toggle_current_selection)
        self.c_shortcut.setAutoRepeat(False)
    
    def _setup_ui(self):
        """Set up the main UI layout."""
        # Add components to layout
        self.layout.addWidget(self.file_list)
        self.layout.addWidget(self.audio_player)  # Add audio player with waveform
        self.layout.addWidget(self.control_panel)
        
        # Set layout spacing
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 0)
    
    def _setup_menu(self):
        """Set up the menu bar."""
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Open ZIP action
        open_action = QAction("Open ZIP", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setToolTip("Open a ZIP file containing audio files")
        open_action.triggered.connect(self._handle_open_zip_from_menu)
        file_menu.addAction(open_action)
        
        # Open Folder action
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.setToolTip("Open a folder containing ZIP files")
        open_folder_action.triggered.connect(self._handle_open_folder_from_menu)
        file_menu.addAction(open_folder_action)
        
        # Open Library action
        open_library_action = QAction("Open Library", self)
        open_library_action.setShortcut("Ctrl+L")
        open_library_action.setToolTip("Open a saved audio library file")
        open_library_action.triggered.connect(self._handle_open_library_from_menu)
        file_menu.addAction(open_library_action)
        
        # Save Library action
        save_library_action = QAction("Save Library", self)
        save_library_action.setShortcut("Ctrl+S")
        save_library_action.setToolTip("Save current audio library")
        save_library_action.triggered.connect(self._handle_save_library)
        file_menu.addAction(save_library_action)
        
        # Recent files menu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()
        
        file_menu.addSeparator()
        
        # Extract menu
        extract_menu = file_menu.addMenu("Extract")
        
        # Extract selected action
        extract_selected = QAction("Extract Selected", self)
        extract_selected.setShortcut("Ctrl+E")
        extract_selected.setToolTip("Extract selected audio files from the ZIP")
        extract_selected.triggered.connect(self._handle_extract_selected)
        extract_menu.addAction(extract_selected)
        
        # Extract all action
        extract_all = QAction("Extract All", self)
        extract_all.setShortcut("Ctrl+Shift+E")
        extract_all.setToolTip("Extract all audio files from the ZIP")
        extract_all.triggered.connect(self._handle_extract_all)
        extract_menu.addAction(extract_all)
        
        file_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.setToolTip("Configure application settings")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setToolTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Add search bar to menu bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files...")
        self.search_bar.setMaximumWidth(400)
        self.search_bar.textChanged.connect(self._handle_search)
        
        # Style the search bar to match system theme
        palette = self.search_bar.palette()
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: %s;
                color: %s;
                border: 1px solid %s;
                border-radius: 3px;
                padding: 2px 5px;
            }
        """ % (
            palette.color(QPalette.Base).name(),
            palette.color(QPalette.Text).name(),
            palette.color(QPalette.Mid).name()
        ))
        
        menubar.setCornerWidget(self.search_bar)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        # Keyboard shortcuts action
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.setToolTip("Show keyboard shortcuts")
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction("About", self)
        about_action.setToolTip("Show application information")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Connect all component signals."""
        # File list signals
        self.file_list.file_selected.connect(self._handle_file_selected)
        self.file_list.play_requested.connect(self._handle_play_requested)
        self.file_list.extract_requested.connect(self._handle_extract_requested)
        self.file_list.status_update.connect(self.status_bar.update_file_info)
        self.file_list.progress_update.connect(self.status_bar.update_progress)
        
        # Control panel signals
        self.control_panel.play_clicked.connect(self._handle_play_button_click)
        self.control_panel.pause_clicked.connect(self.audio_player.pause)
        self.control_panel.stop_clicked.connect(self.audio_player.stop)
        self.control_panel.volume_changed.connect(self.audio_player.set_volume)
        self.control_panel.position_changed.connect(self.audio_player.set_position)
        self.control_panel.desired_position_changed.connect(self.audio_player.set_position)
        self.control_panel.dragged_tracker_position_changed.connect(self.audio_player._handle_dragged_tracker_position_change)
        
        # Audio player signals
        self.audio_player.state_changed.connect(self._handle_player_state)
        self.audio_player.progress_updated.connect(self.control_panel.update_progress)
        self.audio_player.error_occurred.connect(self._handle_player_error)
        self.audio_player.duration_changed.connect(self.control_panel.set_duration)
        self.audio_player.position_changed.connect(self.control_panel.set_position)
    
    def _update_recent_files_menu(self):
        """Update the recent files menu."""
        self.recent_menu.clear()
        
        # Get all recent items
        recent_files = self.config_manager.get_recent_files()
        recent_libraries = self.config_manager.get_recent_libraries()
        recent_folders = self.config_manager.get_recent_folders()
        
        if not (recent_files or recent_libraries or recent_folders):
            self.recent_menu.setEnabled(False)
            return
        
        self.recent_menu.setEnabled(True)
        
        # Add recent files section
        if recent_files:
            files_menu = self.recent_menu.addMenu("Recent Files")
            for file_path in recent_files:
                action = QAction(os.path.basename(file_path), self)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, path=file_path: self._handle_recent_file(path))
                files_menu.addAction(action)
        
        # Add recent libraries section
        if recent_libraries:
            libraries_menu = self.recent_menu.addMenu("Recent Libraries")
            for file_path in recent_libraries:
                action = QAction(os.path.basename(file_path), self)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, path=file_path: self._handle_recent_library(path))
                libraries_menu.addAction(action)
        
        # Add recent folders section
        if recent_folders:
            folders_menu = self.recent_menu.addMenu("Recent Folders")
            for folder_path in recent_folders:
                action = QAction(os.path.basename(folder_path), self)
                action.setToolTip(folder_path)
                action.triggered.connect(lambda checked, path=folder_path: self._handle_recent_folder(path))
                folders_menu.addAction(action)
        
        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent Items", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)
    
    def _load_zip_file(self, zip_path, show_status=True, resort_after_load=False):
        """Load a ZIP file and update the UI accordingly.
        
        Args:
            zip_path (str): Path to the ZIP file to load
            show_status (bool): Whether to show status updates in the UI
            
        Returns:
            bool: True if the ZIP was loaded successfully, False otherwise
        """
        try:
            if show_status:
                self.status_bar.update_file_info(f"Loading {os.path.basename(zip_path)}...")
                self._update_window_title(f"Loading {os.path.basename(zip_path)}...")
            
            # Load the ZIP file
            timing_info = self.zip_manager.load_zip(zip_path)
            
            # Update status bar with timing information
            cache_status = " (cached)" if timing_info['used_cache'] else ""
            if show_status:
                self.status_bar.update_file_info(f"Loaded: {os.path.basename(zip_path)}{cache_status} in {timing_info['total_time']:.2f}s")
            
            set_audio_start = time.time()
            # Add audio files to the list
            self.file_list.set_audio_files(
                self.zip_manager.list_audio_files(zip_path),
                self.zip_manager,
                zip_path,
                resort_after_load
            )
            
            set_audio_time = time.time() - set_audio_start
            if show_status:
                self.status_bar.update_file_info(f"Fully Loaded: {os.path.basename(zip_path)}{cache_status} in {(timing_info['total_time']+set_audio_time):.2f}s")
            
            # Add to recent files
            self.config_manager.add_recent_file(zip_path)
            
            return True
            
        except Exception as e:
            if show_status:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
            return False

    def _handle_recent_file(self, file_path):
        """Handle opening a recent file.
        
        Args:
            file_path: Path to the file to open
        """
        if os.path.exists(file_path):
            try:
                if self.welcome_dialog:
                    self.welcome_dialog.close()
                self._load_zip_file(file_path, resort_after_load=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
        else:
            QMessageBox.warning(self, "Warning", f"File not found: {file_path}")
            # Remove from recent files
            self.config_manager.add_recent_file(file_path)  # This will remove it since it doesn't exist
            self._update_recent_files_menu()
    
    def _handle_recent_library(self, file_path):
        """Handle opening a recent library file.
        
        Args:
            file_path: Path to the library file to open
        """
        if os.path.exists(file_path):
            try:
                if self.welcome_dialog:
                    self.welcome_dialog.close()
                self._handle_open_library(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
        else:
            QMessageBox.warning(self, "Warning", f"File not found: {file_path}")
            # Remove from recent libraries
            self.config_manager.add_recent_library(file_path)  # This will remove it since it doesn't exist
            self._update_recent_files_menu()
    
    def _handle_recent_folder(self, folder_path):
        """Handle opening a recent folder.
        
        Args:
            folder_path: Path to the folder to open
        """
        if os.path.exists(folder_path):
            try:
                if self.welcome_dialog:
                    self.welcome_dialog.close()
                self._handle_open_folder(folder_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
        else:
            QMessageBox.warning(self, "Warning", f"Folder not found: {folder_path}")
            # Remove from recent folders
            self.config_manager.add_recent_folder(folder_path)  # This will remove it since it doesn't exist
            self._update_recent_files_menu()
    
    def _clear_recent_files(self):
        """Clear the recent files list."""
        self.config_manager.clear_recent_files()
        self._update_recent_files_menu()
    
    def _handle_open_zip_from_menu(self):
        self._handle_open_zip()
        
    def _handle_open_zip(self, _file_path=None):
        """Handle opening a ZIP file."""
        if _file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Browse Other Files",
                "",
                "ZIP Files (*.zip)"
            )
            if not file_path:  # User cancelled
                return
        else:
            file_path = _file_path
        
        if file_path:
            self._load_zip_file(file_path, resort_after_load=True)
            self._update_recent_files_menu()
    
    def _handle_extract_selected(self):
        """Handle extracting selected files."""
        file_names = self.file_list.get_checked_files()
        if not file_names:
            QMessageBox.warning(self, "Warning", "No files selected")
            return
        
        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if output_dir:
            try:
                # Group files by ZIP
                files_by_zip = {}
                for file_path in file_names:
                    zip_path = self.file_list.get_zip_path(file_path)
                    if not zip_path:
                        raise RuntimeError(f"Could not determine ZIP file for {file_path}")
                    if zip_path not in files_by_zip:
                        files_by_zip[zip_path] = []
                    files_by_zip[zip_path].append(file_path)
                
                # Extract files from each ZIP
                total_extracted = 0
                for zip_path, files in files_by_zip.items():
                    extracted_paths = self.zip_manager.extract_files(zip_path, files, output_dir)
                    total_extracted += len(extracted_paths)
                
                # Update status
                self.status_bar.update_file_info(
                    f"Extracted {total_extracted} files to {output_dir}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
    
    def _handle_extract_all(self):
        """Handle extracting all files."""
        if not self.file_list.file_items:
            QMessageBox.warning(self, "Warning", "No files to extract")
            return
        
        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if output_dir:
            try:
                # Group files by ZIP
                files_by_zip = {}
                for file_path in self.file_list.file_items.keys():
                    zip_path = self.file_list.get_zip_path(file_path)
                    if not zip_path:
                        raise RuntimeError(f"Could not determine ZIP file for {file_path}")
                    if zip_path not in files_by_zip:
                        files_by_zip[zip_path] = []
                    files_by_zip[zip_path].append(file_path)
                
                # Extract files from each ZIP
                total_extracted = 0
                for zip_path, files in files_by_zip.items():
                    extracted_paths = self.zip_manager.extract_files(zip_path, files, output_dir)
                    total_extracted += len(extracted_paths)
                
                # Update status
                self.status_bar.update_file_info(
                    f"Extracted {total_extracted} files to {output_dir}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
    
    def _handle_file_selected(self, file_path):
        """Handle file selection."""
        try:
            # Update status bar with file info
            self.status_bar.update_file_info(f"Selected: {os.path.basename(file_path)}")
            
            # Get duration from cached data
            duration_ms = self.file_list.get_file_duration(file_path)
            if duration_ms is not None:
                self.control_panel.set_duration(duration_ms)
            else:
                self.control_panel.set_duration(0)
                
        except Exception as e:
            # Use print instead of logging to avoid recursion
            print(f"File selection failed: {str(e)}")
            self.status_bar.update_file_info(f"Selected: {os.path.basename(file_path)}")
    
    def _handle_play_requested(self, file_path):
        """Handle play request for a file."""
        try:
            # Get the ZIP path from the file path
            zip_path = self.file_list.get_zip_path(file_path)
            if not zip_path:
                raise RuntimeError("Could not determine ZIP file for audio file")
            
            file_data = self.zip_manager.read_file(zip_path, file_path)
            try:
                audio = mutagen.File(io.BytesIO(file_data))
                if audio is not None and audio.info.length:
                    duration_ms = int(audio.info.length)
                    self.control_panel.set_duration(duration_ms)
            except Exception as e:
                import logging
                logging.warning(f"Mutagen duration probe failed: {e}")
            self.audio_player.play(zip_stream=file_data)
            self._last_played_file = file_path
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_bar.show_error(str(e))
    
    def _handle_extract_requested(self, file_path):
        """Handle extract request for a file."""
        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if output_dir:
            try:
                # Get the ZIP path from the file path
                zip_path = self.file_list.get_zip_path(file_path)
                if not zip_path:
                    raise RuntimeError("Could not determine ZIP file for audio file")
                
                # Extract the file
                extracted_path = self.zip_manager.extract_file(zip_path, file_path, output_dir)
                
                # Update status
                self.status_bar.update_file_info(
                    f"Extracted {os.path.basename(file_path)} to {output_dir}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
    
    def _handle_player_state(self, state):
        """Handle audio player state changes."""
        self._playback_state = state
        self.control_panel.set_playback_state(state)
        if state == "playing":
            self.status_bar.update_file_info("Playing")
        elif state == "paused":
            self.status_bar.update_file_info("Paused")
        elif state == "stopped":
            self.status_bar.update_file_info("Stopped")
        elif state == "error":
            self.status_bar.show_error("Playback error")
    
    def _handle_player_error(self, error):
        """Handle audio player errors."""
        self.status_bar.show_error(error)
    
    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            # Apply settings
            self.audio_player.set_volume(settings["volume"])
            # TODO: Apply theme and file associations
    
    def _show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts = {
            "File Operations": [
                ("Ctrl+O", "Open ZIP file"),
                ("Ctrl+E", "Extract selected files"),
                ("Ctrl+Shift+E", "Extract all files"),
                ("Ctrl+,", "Open settings"),
                ("Ctrl+Q", "Exit application")
            ],
            "Playback": [
                ("Space", "Play/Pause"),
                ("S", "Stop"),
                ("Left", "Seek backward"),
                ("Right", "Seek forward"),
                ("Up", "Increase volume"),
                ("Down", "Decrease volume")
            ],
            "Navigation": [
                ("F1", "Show keyboard shortcuts"),
                ("Esc", "Close dialog/cancel operation")
            ]
        }
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        
        # Format shortcuts text
        text = ""
        for category, items in shortcuts.items():
            text += f"<h3>{category}</h3>"
            for shortcut, description in items:
                text += f"<b>{shortcut}</b>: {description}<br>"
            text += "<br>"
        
        dialog.setText(text)
        dialog.setInformativeText("These shortcuts can be used throughout the application.")
        dialog.exec()
    
    def _show_about(self):
        """Show about dialog."""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("About Audio Browser")
        dialog.setText(f"Audio Browser v{__version__}")
        dialog.setInformativeText(
            "A desktop application for browsing, previewing, and extracting "
            "audio files from ZIP archives."
        )
        dialog.exec()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            
            # Handle different file types
            if os.path.isdir(file_path):
                # If it's a directory, handle it as a folder
                self._handle_open_folder(file_path)
            elif file_path.lower().endswith('.zip'):
                # If it's a ZIP file, handle it as a single ZIP
                self._handle_open_zip(file_path)
            elif file_path.lower().endswith('.audiolibrary'):
                # If it's an audio library file, handle it as a library
                self._handle_open_library(file_path)
            else:
                # Skip unsupported file types
                continue
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up resources
        self.zip_manager.cleanup()
        event.accept()

    def keyPressEvent(self, event):
        """Handle key press events."""
        super().keyPressEvent(event)

    def _handle_play_button_click(self):
        """Handle play button click in control panel."""
        logging.debug("Play button handler called")
        
        # Get currently selected file
        selected_items = self.file_list.selectedItems()
        selected_file = None
        if selected_items:
            # Find the file path for the selected item
            for path, file_item in self.file_list.file_items.items():
                if file_item == selected_items[0]:
                    selected_file = path
                    break
        
        # If paused and a different file is selected, play the new file
        if self._playback_state == "paused" and selected_file and selected_file != self._last_played_file:
            logging.debug(f"Different file selected while paused, playing: {selected_file}")
            self.audio_player.queued_position_changed = -1
            self._handle_play_requested(selected_file)
            return
            
        # If paused and same file or no new selection, resume playback
        if self._playback_state == "paused":
            logging.debug("Resuming paused playback. Is Seekable? %s", self.audio_player.media_player.isSeekable())
            self.audio_player.media_player.play()
            return
            
        # If a file is selected, play it
        if selected_file:
            logging.debug(f"Playing selected file: {selected_file}")
            self._handle_play_requested(selected_file)
        # If nothing selected but we have a last played file, resume it
        elif self._last_played_file:
            logging.debug(f"Resuming last played file: {self._last_played_file}")
            self._handle_play_requested(self._last_played_file)
        else:
            # If no file is selected or played, do nothing
            logging.debug("No file selected or previously played")
            pass

    def _handle_zip_progress(self, status: str, progress: int):
        """Handle progress updates from the zip manager."""
        self.status_bar.update_file_info(status)
        self.status_bar.update_progress(progress)

    def _handle_search(self, text):
        """Handle search text changes."""
        self.file_list.apply_search_filter(text)

    def _toggle_folder(self, folder_path):
        """Toggle folder expansion state."""
        self.folder_states[folder_path] = not self.folder_states.get(folder_path, True)
        
        # Update toggle arrow
        header_row = self.folder_rows[folder_path]
        header_widget = self.cellWidget(header_row, 0)
        toggle_label = header_widget.findChild(QLabel, "toggle_arrow")
        toggle_label.setText("▼" if self.folder_states[folder_path] else "▶")
        
        # Show/hide rows based on both folder state and current search
        current_search = getattr(self, '_current_search', '')
        for row, data in self.file_data.items():
            if data['folder'] == folder_path:
                # Check if the file matches the current search
                matches_search = not current_search or current_search in data['path'].lower()
                # Show the row only if it matches search AND folder is expanded
                self.setRowHidden(row, not (matches_search and self.folder_states[folder_path]))
        
        # Update all row colors after toggling
        self._update_all_row_colors()

    def _handle_save_library(self):
        """Handle saving the current audio library."""
        if not self.zip_manager.get_open_zips():
            QMessageBox.warning(self, "Warning", "No ZIP files loaded to save")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audio Library",
            "",
            "Audio Library Files (*.audiolibrary)"
        )
        
        if file_path:
            # Ensure .audiolibrary extension
            if not file_path.lower().endswith('.audiolibrary'):
                file_path += '.audiolibrary'
                
            try:
                # Create library data
                library_data = {
                    'version': '1.0',
                    'zip_files': self.zip_manager.get_open_zips(),
                    'timestamp': time.time()
                }
                
                # Save to file
                with open(file_path, 'w') as f:
                    json.dump(library_data, f, indent=2)
                
                # Update status
                self.status_bar.update_file_info(f"Saved library to {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.status_bar.show_error(str(e))
    
    
    def _handle_open_library_from_menu(self):
        self._handle_open_library()
        
    def _handle_open_library(self, _file_path=None):
        """Handle opening an audio library file."""
        if _file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Audio Library",
                "",
                "Audio Library Files (*.audiolibrary)"
            )
            if not file_path:  # User cancelled
                return
        else:
            file_path = _file_path
            
        # Ensure file_path is a string
        file_path = str(file_path)
        
        try:
            # Load library data
            with open(file_path, 'r') as f:
                library_data = json.load(f)
            
            # Validate library data
            if not isinstance(library_data, dict) or 'zip_files' not in library_data:
                raise ValueError("Invalid library file format")
            
            # Close any currently open ZIPs
            self.zip_manager.cleanup()
            
            # Get list of valid ZIP files
            valid_zip_files = [
                str(zip_path) for zip_path in library_data['zip_files']
                if os.path.exists(str(zip_path))
            ]
            
            if not valid_zip_files:
                QMessageBox.warning(self, "Warning", "No valid ZIP files found in library")
                return
            
            # Load each ZIP file
            loaded_count = 0
            total_files = len(valid_zip_files)
            
            for i, zip_path in enumerate(valid_zip_files):
                # Update status with remaining files
                remaining = total_files - i
                status_text = f"Loading {os.path.basename(zip_path)} ({remaining} more to go)..."
                self.status_bar.update_file_info(status_text)
                self._update_window_title(status_text)
                
                if self._load_zip_file(zip_path, show_status=False):
                    loaded_count += 1
            
            # Add to recent libraries
            self.config_manager.add_recent_library(file_path)
            self.file_list.sort_groups_and_files()
            # Update UI
            self._update_recent_files_menu()
            self.status_bar.update_file_info(
                f"Loaded {loaded_count} ZIP files from library: {os.path.basename(file_path)}"
            )
            self._update_window_title()  # Reset to default title
            
            # Sort the rows after loading is complete
            self.file_list.sortItems(0, Qt.AscendingOrder)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_bar.show_error(str(e))
            self._update_window_title()  # Reset to default title

    def _handle_open_folder_from_menu(self):
        self._handle_open_folder()
        
    def _handle_open_folder(self, _folder_path=None):
        """Handle opening a folder of ZIP files."""
        if _folder_path is None:
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Folder with ZIP Files",
                ""
            )
            if not folder_path:  # User cancelled
                return
        else:
            folder_path = _folder_path
        
        # Ensure folder_path is a string
        folder_path = str(folder_path)
        
        try:
            # Find all ZIP files in the folder
            zip_files = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.zip'):
                        zip_files.append(os.path.join(root, file))
            
            if not zip_files:
                QMessageBox.warning(self, "Warning", "No ZIP files found in selected folder")
                return
            
            # Close any currently open ZIPs
            self.zip_manager.cleanup()
            
            # Load each ZIP file
            loaded_count = 0
            total_files = len(zip_files)
            
            for i, zip_path in enumerate(zip_files):
                # Update status with remaining files
                remaining = total_files - i
                status_text = f"Loading {os.path.basename(zip_path)} ({remaining} more to go)..."
                self.status_bar.update_file_info(status_text)
                self._update_window_title(status_text)
                
                if self._load_zip_file(zip_path, show_status=False):
                    loaded_count += 1
            
            # Add to recent folders
            self.config_manager.add_recent_folder(folder_path)
            self.file_list.sort_groups_and_files()
            # Update UI
            self._update_recent_files_menu()
            self.status_bar.update_file_info(
                f"Loaded {loaded_count} ZIP files from {os.path.basename(folder_path)}"
            )
            self._update_window_title()  # Reset to default title
            
            # Sort the rows after loading is complete
            self.file_list.sortItems(0, Qt.AscendingOrder)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_bar.show_error(str(e))
            self._update_window_title()  # Reset to default title

    def _update_window_title(self, title=None):
        """Update the window title.
        
        Args:
            title (str, optional): Custom title to append. If None, resets to default.
        """
        if title:
            self.setWindowTitle(f"Audio Browser - {title}")
        else:
            self.setWindowTitle("Audio Browser")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Audio Browser - Browse and play audio files from ZIP archives')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # Set debug mode in relevant classes
    if args.debug:
        ZipManager.DEBUG = True
        AudioPlayer.DEBUG = True
        AudioFileTreeWidget.DEBUG = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Show welcome dialog
    recent_files = window.config_manager.get_recent_files()
    recent_libraries = window.config_manager.get_recent_libraries()
    recent_folders = window.config_manager.get_recent_folders()
    window.welcome_dialog = WelcomeDialog(recent_files, recent_libraries, recent_folders, window)
    window.welcome_dialog.recent_file_selected.connect(window._handle_recent_file)
    window.welcome_dialog.recent_library_selected.connect(window._handle_recent_library)
    window.welcome_dialog.recent_folder_selected.connect(window._handle_recent_folder)
    window.welcome_dialog.open_zip_clicked.connect(window._handle_open_zip_from_menu)
    window.welcome_dialog.open_library_clicked.connect(window._handle_open_library_from_menu)
    window.welcome_dialog.open_folder_clicked.connect(window._handle_open_folder_from_menu)
    
    window.welcome_dialog.exec()
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(main()) 