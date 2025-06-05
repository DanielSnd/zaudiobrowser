from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QWidget, QHBoxLayout,
    QPushButton, QLabel, QApplication, QCheckBox, QStyledItemDelegate,
    QStyle, QAbstractItemView, QHeaderView, QDialog, QVBoxLayout, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QRect
from PySide6.QtGui import QIcon, QColor, QPalette, QPainter, QFont
import os
import time
from collections import defaultdict
from typing import List, Optional, Dict, Any
from audio_browser.zip.zip_manager import ZipManager
from audio_browser.ui.audio_file_model import AudioFileModel

class TreeItemDelegate(QStyledItemDelegate):
    """Custom delegate for handling alternating row colors and folder styling."""
    
    def paint(self, painter: QPainter, option, index):
        """Paint the item with alternating colors and proper styling."""
        # Get the item
        item = self.parent().itemFromIndex(index)
        if not item:
            super().paint(painter, option, index)
            return
            
        # Set up the option
        option = option.__class__(option)
        self.initStyleOption(option, index)
        
        # Get the visual row index
        tree = self.parent()
        visual_index = tree.indexFromItem(item).row()
        
        # Get the full rect including branch area
        full_rect = option.rect
        if index.column() == 0:  # Only for the first column
            # Get the indentation level
            level = 0
            parent = item.parent()
            while parent:
                level += 1
                parent = parent.parent()
            
            # Calculate the full width including branch area
            branch_width = tree.indentation() * level
            full_rect.setLeft(full_rect.left() - branch_width)
        
        # Handle folder items
        if item in tree.folder_items.values():
            # Draw background
            if option.state & QStyle.State_Selected:
                painter.fillRect(full_rect, option.palette.color(QPalette.Highlight))
            else:
                painter.fillRect(full_rect, option.palette.color(QPalette.AlternateBase).darker(120))
            
            # check if it's the name column
            if index.column() == 0:
                # Get the text and split it into name and count
                text = index.data()
                name = text
                count = ""
                # Look for the last occurrence of " *%*(" to handle folder names containing parentheses
                last_paren_idx = text.rfind(" *%*(")
                if last_paren_idx > -1:
                    potential_count = text[last_paren_idx + 5:]  # +5 to skip " *%*("
                    name = text[:last_paren_idx]
                    count = "(" + potential_count
                
                # Set up font
                font = option.font
                font.setPointSize(13)
                painter.setFont(font)
                
                # Draw the icon if present
                icon = index.data(Qt.ItemDataRole.DecorationRole)
                if icon:
                    icon_rect = QRect(option.rect.left() + 4, option.rect.top() + 4,
                                    option.rect.height() - 8, option.rect.height() - 8)
                    icon.paint(painter, icon_rect)
                
                # Calculate text rectangles
                text_rect = option.rect.adjusted(option.rect.height(), 4, -4, -4)
                name_rect = text_rect
                count_rect = text_rect
                
                # Draw the name (left-aligned)
                name_rect.setLeft(name_rect.left() - 10)
                # If the name contains one ore more / it means it has subfolders,
                # in this case we should draw each part of the name in a slightly darker color the leftmost it is.
                # each part should still be drawing in the correct position as it would if we didn't separate it.
                
                if "/" in name:
                    # Split the name into parts
                    parts = name.split("/")
                    current_x = name_rect.left()
                    
                    # Draw each part with progressively darker color
                    for i, part in enumerate(parts):
                        # Calculate color darkness based on position
                        # Earlier parts (leftmost) are darker, last part is regular color
                        if i == len(parts) - 1:
                            # Last part uses regular color
                            color = option.palette.color(QPalette.Text)
                        else:
                            # Earlier parts get progressively darker
                            darkness = 120 + ((len(parts) - i - 1) * 10)  # More darkness for earlier parts
                            color = option.palette.color(QPalette.Text).darker(darkness)
                        painter.setPen(color)
                        
                        # Draw this part
                        part_rect = QRect(current_x, name_rect.top(), 
                                        painter.fontMetrics().horizontalAdvance(part), 
                                        name_rect.height())
                        painter.drawText(part_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, part)
                        
                        # Move x position for next part
                        current_x += part_rect.width()
                        
                        # Draw separator if not the last part
                        if i < len(parts) - 1:
                            separator_rect = QRect(current_x, name_rect.top(),
                                                painter.fontMetrics().horizontalAdvance("/"),
                                                name_rect.height())
                            painter.drawText(separator_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "/")
                            current_x += separator_rect.width()
                else:
                    # Draw single name without splitting
                    painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
                
                # Draw the count (right-aligned)
                if count:
                    painter.setPen(option.palette.color(QPalette.Text).darker(135))
                    painter.drawText(count_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, count)
                    painter.setPen(option.palette.color(QPalette.Text))
                return
        else:
            # Handle alternating colors for file items
            
            if option.state & QStyle.State_Selected:
                painter.fillRect(full_rect, option.palette.color(QPalette.Highlight))
            else:
                if visual_index % 2 == 0:
                    painter.fillRect(full_rect, option.palette.color(QPalette.Base).lighter(125))
                else:
                    painter.fillRect(full_rect, option.palette.color(QPalette.Base).lighter(110))
                
            if index.column() == 0:
                # Add padding to the left side
                option.rect.setLeft(option.rect.left() + 10)  # Add 20 pixels of padding
                option.text = f" {option.text}" 

            # Draw the item
            QApplication.style().drawControl(QStyle.CE_ItemViewItem, option, painter)

class AudioFileTreeWidget(QTreeWidget):
    """Custom tree widget for displaying audio files with hierarchical folder structure."""
    
    # Signals
    file_selected = Signal(str)  # Emits selected file path
    play_requested = Signal(str)  # Emits file path to play
    extract_requested = Signal(str)  # Emits file path to extract
    status_update = Signal(str)  # Emits status message
    progress_update = Signal(int)  # Emits progress value (0-100)
    
    # Debug flag
    DEBUG = False
    
    def __init__(self, parent=None):
        """Initialize the audio file tree widget."""
        super().__init__(parent)
        
        # Set up tree widget properties
        self.setHeaderLabels([" Name ", " Duration ", " Size "])
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        # Set minimum column widths
        self.setColumnWidth(0, 600)  # Name column
        self.setColumnWidth(1, 100)  # Duration column
        self.setColumnWidth(2, 80)  # Size column
        
        # Set column resize mode
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column stretches
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Duration column fixed
        self.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Size column fixed
        
        self.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustToContents)
        
        # Set custom delegate
        self.item_delegate = TreeItemDelegate(self)
        self.setItemDelegate(self.item_delegate)
        
        # Initialize data model
        self.model = AudioFileModel()
        
        # Set row height
        self.setStyleSheet("""
            QTreeWidget {
                background-color: palette(base);
            }
            QTreeWidget::item {
                height: 32px;
                padding: 6px;
            }
            QTreeWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            QTreeWidget::item:checked {
                background-color: palette(highlight).lighter(110);
                color: palette(highlighted-text).darker(110);
            }
        """)
        
        # Track UI state
        self.folder_items = {}  # Track folder items by path
        self.file_items = {}  # Track file items by path
        self._last_selected_item = None  # Track last selected item for shift selection
        self._current_search = ""  # Track current search text
        
        # Connect signals
        self.itemDoubleClicked.connect(self._handle_double_click)
        self.itemSelectionChanged.connect(self._handle_selection_change)
        self.itemChanged.connect(self._handle_item_changed)
        self.itemClicked.connect(self._handle_item_click)
        
        # Set up context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _handle_item_click(self, item: QTreeWidgetItem, column: int):
        """Handle item clicks, including folder expansion."""
        # If it's a folder item, toggle its expansion
        if item in self.folder_items.values():
            if item.isExpanded():
                item.setExpanded(False)
            else:
                # Load folder contents if not already loaded
                if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
                    self._load_folder_contents(item)
                item.setExpanded(True)
            return
            
        # For file items, just let the default behavior handle it
        pass
    
    def _add_folder(self, folder_path: str) -> QTreeWidgetItem:
        """Add a folder to the tree.
        
        Args:
            folder_path: Path of the folder to add
            
        Returns:
            The created folder item
        """
        # Create folder item
        folder_item = QTreeWidgetItem(self)
        folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        folder_item.setCheckState(0, Qt.CheckState.Unchecked)
        
        # Set folder name
        if folder_path:
            path_parts = folder_path.split(os.sep)
            path_parts = [p for p in path_parts if p]
            if len(path_parts) > 1:
                path_parts = path_parts[1:]
            folder_name = " / ".join(path_parts)
        else:
            folder_name = "Root"
        
        folder_item.setText(0, folder_name)
        
        # Set folder icon
        folder_item.setIcon(0, QIcon(":/icons/folder.png"))
        
        # Set folder background color
        palette = self.palette()
        folder_color = palette.color(QPalette.AlternateBase).darker(120)
        folder_item.setBackground(0, folder_color)
        folder_item.setBackground(1, folder_color)
        folder_item.setBackground(2, folder_color)
        
        # Set folder item type for styling
        folder_item.setData(0, Qt.ItemDataRole.UserRole, "folder")
        
        # Store folder reference
        self.folder_items[folder_path] = folder_item
        
        return folder_item
    
    def _add_file(self, folder_path: str, file_data: Dict[str, Any]) -> QTreeWidgetItem:
        """Add a file under its folder in the tree.
        
        Args:
            folder_path: Path of the parent folder
            file_data: Dictionary containing file information
            
        Returns:
            The created file item
        """
        # Get or create parent folder
        folder_item = self.folder_items.get(folder_path)
        if not folder_item:
            folder_item = self._add_folder(folder_path)
        
        # Create file item
        file_item = QTreeWidgetItem(folder_item)
        file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        file_item.setCheckState(0, Qt.CheckState.Unchecked)
        
        # Set file name and icon
        file_name = os.path.basename(file_data['path'])
        file_item.setText(0, file_name)
        
        # Set icon based on file extension
        ext = os.path.splitext(file_data['path'])[1].lower()
        if ext == '.wav':
            file_item.setIcon(0, QIcon(":/icons/wav.png"))
        elif ext == '.mp3':
            file_item.setIcon(0, QIcon(":/icons/mp3.png"))
        elif ext == '.ogg':
            file_item.setIcon(0, QIcon(":/icons/ogg.png"))
        else:
            file_item.setIcon(0, QIcon(":/icons/audio.png"))
        
        # Set duration and size
        duration_str = "?"
        size_str = "?"
        if file_data['metadata']:
            duration_ms = file_data['metadata'].get('duration_ms', 0)
            if duration_ms > 0:
                minutes = int((duration_ms % 3600000) // 60000)
                seconds = int((duration_ms % 60000) // 1000)
                milliseconds = int(duration_ms % 1000)
                duration_str = f"{minutes:02}:{seconds:02}.{milliseconds:03}"
            
            size_bytes = file_data['metadata'].get('size', 0)
            if size_bytes > 0:
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes/1024:.1f} KB"
                else:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
        
        file_item.setText(1, duration_str)
        file_item.setText(2, size_str)
        
        # Store file reference
        self.file_items[file_data['path']] = file_item
        
        return file_item
    
    def _handle_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle changes to item check state.
        
        Args:
            item: The item that changed
            column: The column that changed
        """
        if column != 0:  # Only handle checkbox column
            return
            
        # Get the path for this item
        item_path = None
        for path, file_item in self.file_items.items():
            if file_item == item:
                item_path = path
                break
        
        if item_path:
            # Update model checked state
            self.model.set_file_checked(item_path, item.checkState(0) == Qt.Checked)
            
            # Update parent folder state
            folder_path = os.path.dirname(item_path)
            if folder_path in self.folder_items:
                self._update_folder_state(folder_path)
    
    def _update_folder_state(self, folder_path: str):
        """Update a folder's check state based on its children.
        
        Args:
            folder_path: Path of the folder to update
        """
        folder_item = self.folder_items.get(folder_path)
        if not folder_item:
            return
            
        # Count checked and unchecked children
        checked_count = 0
        unchecked_count = 0
        total_count = 0
        
        for i in range(folder_item.childCount()):
            child = folder_item.child(i)
            if child.checkState(0) == Qt.Checked:
                checked_count += 1
            elif child.checkState(0) == Qt.Unchecked:
                unchecked_count += 1
            total_count += 1
        
        # Set folder state based on children
        if checked_count == total_count:
            folder_item.setCheckState(0, Qt.Checked)
        elif unchecked_count == total_count:
            folder_item.setCheckState(0, Qt.Unchecked)
        else:
            folder_item.setCheckState(0, Qt.PartiallyChecked)
        
        # Update folder count display
        self._update_folder_count(folder_path)
    
    def _update_folder_count(self, folder_path: str):
        """Update a folder's count display.
        
        Args:
            folder_path: Path of the folder to update
        """
        folder_item = self.folder_items.get(folder_path)
        if not folder_item:
            return
            
        # Count total and selected files
        total_count = folder_item.childCount()
        selected_count = sum(1 for i in range(total_count) 
                           if folder_item.child(i).checkState(0) == Qt.Checked)
        
        # Get the original name by finding the last occurrence of " *%*(" that's followed by a count pattern
        text = folder_item.text(0)
        last_paren_idx = text.rfind(" *%*(")
        if last_paren_idx > -1:
            potential_count = text[last_paren_idx + 5:]  # +5 to skip " *%*("
            original_name = text[:last_paren_idx]
        else:
            original_name = text
        print(f"Original name: {original_name}")
            
        # Update folder name with count, preserving the original name
        folder_item.setText(0, f"{original_name} *%*({total_count} files" + 
                          (f", {selected_count} selected" if selected_count > 0 else "") + ")")
    
    def _handle_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double click on an item.
        
        Args:
            item: The clicked item
            column: The clicked column
        """
        # Find the file path for this item
        file_path = None
        for path, file_item in self.file_items.items():
            if file_item == item:
                file_path = path
                break
                
        if file_path:
            self.play_requested.emit(file_path)
    
    def _handle_selection_change(self):
        """Handle selection changes, including shift and ctrl selection."""
        selected = self.selectedItems()
        if not selected:
            return
            
        # Get the current selected item
        current_item = selected[0]
        
        # Handle shift selection
        modifiers = QApplication.keyboardModifiers()
        is_shift_pressed = bool(modifiers & Qt.ShiftModifier)
        
        if is_shift_pressed and self._last_selected_item is not None:
            # Get the top-level items
            root = self.invisibleRootItem()
            items = []
            for i in range(root.childCount()):
                items.extend(self._get_all_items(root.child(i)))
            
            # Find indices of last and current items
            last_idx = items.index(self._last_selected_item)
            current_idx = items.index(current_item)
            
            # Select all items between last and current
            start_idx = min(last_idx, current_idx)
            end_idx = max(last_idx, current_idx)
            
            for item in items[start_idx:end_idx + 1]:
                if item in self.file_items.values():  # Only select file items
                    item.setSelected(True)
        
        # Update last selected item
        if current_item in self.file_items.values():  # Only update for file items
            self._last_selected_item = current_item
        
        # Emit file selected signal
        if current_item in self.file_items.values():
            # Find the file path for this item
            file_path = None
            for path, file_item in self.file_items.items():
                if file_item == current_item:
                    file_path = path
                    break
                    
            if file_path:
                self.file_selected.emit(file_path)
    
    def _get_all_items(self, item: QTreeWidgetItem) -> List[QTreeWidgetItem]:
        """Get all items under a given item recursively.
        
        Args:
            item: The root item to get children from
            
        Returns:
            List of all items under the root item
        """
        items = [item]
        for i in range(item.childCount()):
            items.extend(self._get_all_items(item.child(i)))
        return items
    
    def _show_context_menu(self, position):
        """Show context menu for the clicked item.
        
        Args:
            position: The position where the context menu was requested
        """
        item = self.itemAt(position)
        if not item or item not in self.file_items.values():
            return
            
        # Find the file path for this item
        file_path = None
        for path, file_item in self.file_items.items():
            if file_item == item:
                file_path = path
                break
                
        if not file_path:
            return
            
        menu = QMenu(self)
        play_action = menu.addAction("Play")
        extract_action = menu.addAction("Extract")
        menu.addSeparator()
        properties_action = menu.addAction("Properties")
        action = menu.exec(self.viewport().mapToGlobal(position))
        
        if action == play_action:
            self.play_requested.emit(file_path)
        elif action == extract_action:
            self.extract_requested.emit(file_path)
        elif action == properties_action:
            self._show_properties(item)
    
    def _show_properties(self, item: QTreeWidgetItem):
        """Show properties dialog for an item.
        
        Args:
            item: The item to show properties for
        """
        # Find the file path for this item
        file_path = None
        for path, file_item in self.file_items.items():
            if file_item == item:
                file_path = path
                break
                
        if not file_path:
            return
            
        # Get file data from model
        file_data = None
        for data in self.model.files:
            if data['path'] == file_path:
                file_data = data
                break
                
        if not file_data:
            return
            
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"File Properties [{os.path.basename(file_path)}]")
        dialog.setMinimumWidth(600)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Add file information
        info_layout = QVBoxLayout()
        
        # Helper function to create label-value pairs
        def add_label_value(label_text, value_text, word_wrap=False):
            label_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            label.setFixedWidth(100)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            value = QLabel(value_text)
            if word_wrap:
                value.setWordWrap(True)
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)  # <-- Make selectable!

            label_layout.addWidget(label)
            label_layout.addWidget(value)
            info_layout.addLayout(label_layout)
        
        # File name
        add_label_value("Name:", os.path.basename(file_path))
        
        # File path
        add_label_value("Path:", file_path, word_wrap=True)
        
        # File size
        size_bytes = file_data['metadata'].get('size', 0)
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes/1024:.1f} KB"
        else:
            size_str = f"{size_bytes/(1024*1024):.1f} MB"
        add_label_value("Size:", size_str)
        
        # Duration
        duration_ms = file_data['metadata'].get('duration_ms', 0)
        if duration_ms > 0:
            minutes = int((duration_ms % 3600000) // 60000)
            seconds = int((duration_ms % 60000) // 1000)
            milliseconds = int(duration_ms % 1000)
            duration_str = f"{minutes:02}:{seconds:02}.{milliseconds:03}"
        else:
            duration_str = "Unknown"
        add_label_value("Duration:", duration_str)
        
        # File type
        add_label_value("Type:", os.path.splitext(file_path)[1].upper()[1:])
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        info_layout.addWidget(separator)
        
        # Audio format section
        format_label = QLabel("Audio Format")
        format_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        info_layout.addWidget(format_label)
        
        # Get full metadata from ZipManager
        zip_path = file_data.get('zip_path')
        zip_manager = file_data.get('zip_manager')
        
        if zip_path and zip_manager:
            try:
                metadata = zip_manager.get_full_audio_metadata(zip_path, file_path)
                if metadata:
                    # Sample rate
                    sample_rate = metadata.get('sample_rate', 0)
                    sample_rate_str = f"{sample_rate:,} Hz" if sample_rate > 0 else "Unknown"
                    add_label_value("Sample Rate:", sample_rate_str)
                    
                    # Channels
                    channels = metadata.get('channels', 0)
                    channels_str = f"{channels} ({'Mono' if channels == 1 else 'Stereo' if channels == 2 else 'Multi-channel'})"
                    add_label_value("Channels:", channels_str)
                    
                    # Bit depth
                    bit_depth = metadata.get('bit_depth', 0)
                    bit_depth_str = f"{bit_depth} bits" if bit_depth > 0 else "Unknown"
                    add_label_value("Bit Depth:", bit_depth_str)
                    
                    # Bitrate
                    bitrate = metadata.get('bitrate', 0)
                    if bitrate > 0:
                        if bitrate < 1000:
                            bitrate_str = f"{bitrate} b/s"
                        elif bitrate < 1000000:
                            bitrate_str = f"{bitrate/1000:.1f} kb/s"
                        else:
                            bitrate_str = f"{bitrate/1000000:.1f} Mb/s"
                    else:
                        bitrate_str = "Unknown"
                    add_label_value("Bitrate:", bitrate_str)
                    
                    # Add separator
                    separator = QFrame()
                    separator.setFrameShape(QFrame.HLine)
                    separator.setFrameShadow(QFrame.Sunken)
                    info_layout.addWidget(separator)
                    
                    # Metadata section
                    metadata_label = QLabel("Metadata")
                    metadata_label.setStyleSheet("font-weight: bold; font-size: 12px;")
                    info_layout.addWidget(metadata_label)
                    
                    # Add all other metadata fields
                    for key, value in metadata.items():
                        # Skip fields we've already shown
                        if key in ['sample_rate', 'channels', 'bit_depth', 'bitrate', 'duration_ms']:
                            continue
                        add_label_value(
                            key.replace('_', ' ').title() + ":",
                            str(value),
                            word_wrap=True
                        )
            except Exception as e:
                print(f"Error getting metadata: {e}")
                # Show basic info from model metadata
                metadata = file_data['metadata']
                if metadata:
                    for key, value in metadata.items():
                        if value and key not in ['size', 'duration_ms']:
                            add_label_value(
                                key.replace('_', ' ').title() + ":",
                                str(value),
                                word_wrap=True
                            )
        else:
            # Show basic info from model metadata
            metadata = file_data['metadata']
            if metadata:
                for key, value in metadata.items():
                    if value and key not in ['size', 'duration_ms']:
                        add_label_value(
                            key.replace('_', ' ').title() + ":",
                            str(value),
                            word_wrap=True
                        )
        
        # Add info layout to main layout
        layout.addLayout(info_layout)
        
        # Add close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
    
    def set_audio_files(self, file_list: List[str], zip_manager: ZipManager, 
                       zip_path: str, resort_after_load: bool = False):
        """Add files from a ZIP to the tree.
        
        Args:
            file_list: List of file paths to add
            zip_manager: ZipManager instance for handling ZIP operations
            zip_path: Path to the ZIP file
            resort_after_load: Whether to resort after loading
        """
        # Disable UI updates during processing
        self.setUpdatesEnabled(False)
        timing_set_audio_start = time.time()
        
        try:
            # Process files in batches
            BATCH_SIZE = 50
            total_files = len(file_list)
            processed_files = 0
            
            # Pre-fetch all metadata at once
            cached_metadata = zip_manager.cache_manager.get_cached_metadata(zip_path)
            cache_file = zip_manager.cache_manager._get_cache_file_path(zip_path)
            
            if self.DEBUG:
                print(f"\n[DEBUG] Cache file location: {cache_file}")
                if cached_metadata:
                    print(f"[DEBUG] Using cached metadata for {zip_path}")
                    print(f"[DEBUG] Cache contains {len(cached_metadata.get('audio_files', []))} files")
                else:
                    print(f"[DEBUG] No cache found for {zip_path}, will create new cache")
            
            # Process files in batches
            start_process_files_in_batches = time.time()
            for i in range(0, total_files, BATCH_SIZE):
                batch = file_list[i:i + BATCH_SIZE]
                for file_path in batch:
                    base = os.path.basename(file_path)
                    if base.startswith("._") or "__MACOSX" in file_path.split(os.sep):
                        continue
                    
                    file_metadata = None
                    if cached_metadata and 'file_metadata' in cached_metadata:
                        file_metadata = cached_metadata['file_metadata'].get(file_path)
                    
                    # Add to model
                    self.model.add_file(
                        file_path,
                        file_bytes=None,  # Don't read file bytes if we have metadata
                        zip_path=zip_path,
                        file_metadata=file_metadata,
                        zip_manager=zip_manager
                    )
                    
                    processed_files += 1
                
                # Update progress less frequently
                progress = int((processed_files / total_files) * 100)
                self.progress_update.emit(progress)
                self.status_update.emit(f"Processed {processed_files}/{total_files} files...")
                
                # Process Qt events every batch to keep UI responsive
                QApplication.processEvents()
            
            process_files_in_batches_time = time.time() - start_process_files_in_batches
            if self.DEBUG:
                print(f"[DEBUG] Processed {processed_files} files in {process_files_in_batches_time:.2f} seconds")
            
            self.status_update.emit(f"Processed {processed_files} files")
            self.progress_update.emit(100)
            QTimer.singleShot(1000, lambda: self.progress_update.emit(0))
            
        finally:
            # Re-enable UI updates
            self.setUpdatesEnabled(True)
            timing_set_audio_time = time.time() - timing_set_audio_start
            before_sort_and_rebuild_start = time.time()
            
            # Sort and rebuild the tree after loading
            if resort_after_load:
                self.sort_groups_and_files()
                sort_and_rebuild_time = time.time() - before_sort_and_rebuild_start
                if self.DEBUG:
                    print(f"[DEBUG] Set audio files in {timing_set_audio_time:.2f} seconds. Sort and rebuild in {sort_and_rebuild_time:.2f} seconds")
            else:
                if self.DEBUG:
                    print(f"[DEBUG] Set audio files in {timing_set_audio_time:.2f} seconds. No sort and rebuild")
    
    def sort_groups_and_files(self):
        """Sort all folders and files globally and rebuild the tree."""
        # Disable UI updates during sorting
        time_start = time.time()
        self.setUpdatesEnabled(False)
        
        try:
            # Sort the data model
            self.model.sort_files()
            
            # Clear the tree
            self.clear()
            self.folder_items.clear()
            self.file_items.clear()
            
            # Only add folders initially, without their contents
            for folder in self.model.get_folders():
                folder_item = self._add_folder(folder)
                # Add a placeholder child to make the folder expandable
                placeholder = QTreeWidgetItem(folder_item)
                placeholder.setText(0, "Loading...")
                placeholder.setFlags(Qt.NoItemFlags)  # Make it non-selectable
                
                # Update folder name with total file count
                total_count = len(self.model.get_folder_files(folder))
                base_name = folder_item.text(0).split(" *%*(")[0]
                folder_item.setText(0, f"{base_name} *%*({total_count} files)")
            
        finally:
            # Re-enable UI updates
            self.setUpdatesEnabled(True)
            time_end = time.time()
            print(f"Sort and rebuild in {time_end - time_start:.2f} seconds")

    def _load_folder_contents(self, folder_item: QTreeWidgetItem):
        """Load the contents of a folder when it's expanded.
        
        Args:
            folder_item: The folder item to load contents for
        """
        # Find the folder path
        folder_path = None
        for path, item in self.folder_items.items():
            if item == folder_item:
                folder_path = path
                break
                
        if not folder_path:
            return
            
        # Remove the loading placeholder
        folder_item.removeChild(folder_item.child(0))
        
        # Add all files under this folder
        for file_data in self.model.get_folder_files(folder_path):
            file_item = self._add_file(folder_path, file_data)
            # Hide non-matching files if there's a search
            if self._current_search:
                matches_search = self._current_search in file_data['path'].lower()
                file_item.setHidden(not matches_search)
        
        # Update folder state
        self._update_folder_state(folder_path)

    def apply_search_filter(self, search_text: str):
        """Apply search filter to the tree.
        
        Args:
            search_text: Text to filter by
        """
        self._current_search = search_text.lower()
        
        # First, update folder visibility based on whether they have matching children
        for folder_path, folder_item in self.folder_items.items():
            matching_count = 0
            total_count = 0
            
            # Count matching and total files
            for file_data in self.model.get_folder_files(folder_path):
                total_count += 1
                if not self._current_search or self._current_search in file_data['path'].lower():
                    matching_count += 1
            
            # Show/hide folder based on search
            has_matching_children = matching_count > 0
            folder_item.setHidden(not has_matching_children)
            
            # Update folder name with counts
            base_name = folder_item.text(0).split(" *%*(")[0]
            if self._current_search:
                folder_item.setText(0, f"{base_name} *%*( {matching_count} / {total_count} files match )")
            else:
                folder_item.setText(0, f"{base_name} *%*( {total_count} files )")
        
        # Then update file visibility based on search
        for file_path, file_item in self.file_items.items():
            matches_search = not self._current_search or self._current_search in file_path.lower()
            file_item.setHidden(not matches_search)
    
    def clear_all_files(self):
        """Clear all loaded files and reset the tree."""
        self.model.clear()
        self.clear()
        self.folder_items.clear()
        self.file_items.clear()
        self._last_selected_item = None
        self._current_search = ""
    
    def get_checked_files(self) -> List[str]:
        """Get list of checked file paths.
        
        Returns:
            List of checked file paths
        """
        return self.model.get_checked_files()
    
    def get_file_duration(self, file_path: str) -> int:
        """Get the duration of a file in milliseconds.
        
        Args:
            file_path: Path of the file
            
        Returns:
            Duration in milliseconds, or 0 if not found
        """
        for file_data in self.model.files:
            if file_data['path'] == file_path:
                return file_data['metadata'].get('duration_ms', 0)
        return 0
    
    def get_zip_path(self, file_path: str) -> Optional[str]:
        """Get the ZIP path for a file.
        
        Args:
            file_path: Path of the file
            
        Returns:
            Path to the ZIP file containing this file, or None if not found
        """
        for file_data in self.model.files:
            if file_data['path'] == file_path:
                return file_data.get('zip_path')
        return None
    
    def toggle_current_selection(self):
        """Toggle the checkbox state of all selected items."""
        selected_items = self.selectedItems()
        if not selected_items:
            return
            
        # Get the state of the first selected item
        first_item = selected_items[0]
        if first_item in self.file_items.values():
            new_state = Qt.Unchecked if first_item.checkState(0) == Qt.Checked else Qt.Checked
            
            # Apply the same state to all selected items
            for item in selected_items:
                if item in self.file_items.values():  # Only toggle file items
                    item.setCheckState(0, new_state)
                    # Update model state
                    for path, file_item in self.file_items.items():
                        if file_item == item:
                            self.model.set_file_checked(path, new_state == Qt.Checked)
                            # Update parent folder state
                            folder_path = os.path.dirname(path)
                            if folder_path in self.folder_items:
                                self._update_folder_state(folder_path)
                            break 