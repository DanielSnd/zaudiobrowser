# ZAudioBrowser

A modern audio library management application that helps you organize and browse your audio files efficiently.

## Features

- Load and browse audio files from ZIP archives or folders containing ZIP files
- Interactive file/folder tree view for easy navigation
- Built-in audio player for immediate playback
- File selection system with checkboxes for batch operations
- Fast search functionality across your audio library
- Intelligent caching system for improved performance
- Modern and intuitive user interface

## Requirements

- Python 3.8 or higher
- PySide6 (Qt for Python)
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/danielsnd/zaudiobrowser.git
cd zaudiobrowser
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package and its dependencies:
```bash
pip install -e .
```

## Usage

Run the application:
```bash
python -m audio_browser.main
```

### Basic Operations

1. **Loading Audio Files**:
   - Click "Open" to select a ZIP file or folder containing ZIP files
   - The application will scan and display the contents in a tree view

2. **Browsing**:
   - Navigate through folders using the tree view
   - Use the search bar to find specific files or folders

3. **Playing Audio**:
   - Select a file to play it immediately
   - Use the built-in player controls to manage playback

4. **File Selection**:
   - Use checkboxes to select multiple files
   - Selected files can be extracted or processed in batch

## Development

### Running Tests

```bash
pytest
```

### Project Structure

```
zaudiobrowser/
├── src/
│   └── audio_browser/
│       ├── main.py          # Main application entry point
│       ├── ui/              # User interface components
│       ├── player/          # Audio player implementation
│       ├── cache/           # Caching system
│       ├── zip/             # ZIP file handling
│       └── config/          # Configuration management
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
└── setup.py                # Package configuration
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
