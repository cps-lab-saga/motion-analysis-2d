from pathlib import Path

import qtawesome as qta

from motion_analysis_2d.defs import QtWidgets, Signal
from motion_analysis_2d.funcs import get_extensions_for_type
from motion_analysis_2d.preferences_pane import ShortcutsWidget, VisualPreferencesWidget


class MenuBar(QtWidgets.QMenuBar):
    open_video_file = Signal(object)
    open_video_folder = Signal(object)
    update_shortcuts = Signal(object)
    update_visual_preferences = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.file_menu = self.addMenu("File")

        self.open_video_file_action = self.file_menu.addAction(
            qta.icon("mdi6.file-video"), "Open Video File..."
        )
        self.open_video_file_action.setShortcut("Ctrl+O")
        self.open_video_file_action.triggered.connect(self.add_file)

        self.open_video_folder_action = self.file_menu.addAction(
            qta.icon("mdi6.folder-open"), "Open Video Folder..."
        )
        self.open_video_folder_action.triggered.connect(self.add_folder)

        self.edit_menu = self.addMenu("Edit")
        self.shortcuts_action = self.edit_menu.addAction(
            qta.icon("mdi6.keyboard"), "Shortcuts"
        )
        self.shortcuts_action.setShortcut("Ctrl+Shift+S")
        self.shortcuts_action.triggered.connect(self.open_shortcuts_widget)
        self.shortcuts_widget = None

        self.visual_pref_action = self.edit_menu.addAction(
            qta.icon("mdi6.format-color-fill"), "Visual Preferences"
        )
        self.visual_pref_action.setShortcut("Ctrl+Shift+P")
        self.visual_pref_action.triggered.connect(self.open_visual_preference_widget)
        self.visual_preference_widget = None

    def add_file(self):
        extensions = [f"*{x}" for x, _ in get_extensions_for_type("video")]

        file_names, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open Video File",
            None,
            f"Video Files ({' '.join(extensions)})",
        )
        if file_names:
            self.open_video_file.emit([Path(name) for name in file_names])

    def add_folder(self):
        folder_name = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Open Video Folder",
        )
        if folder_name:
            self.open_video_folder.emit(list(Path(folder_name).glob("*")))

    def open_shortcuts_widget(self):
        self.shortcuts_widget = ShortcutsWidget()
        self.shortcuts_widget.closed.connect(self.shortcuts_widget_closed)
        self.shortcuts_widget.update_shortcuts.connect(self.update_shortcuts.emit)
        self.shortcuts_widget.show()

    def shortcuts_widget_closed(self):
        self.shortcuts_widget = None

    def open_visual_preference_widget(self):
        self.visual_preference_widget = VisualPreferencesWidget()
        self.visual_preference_widget.closed.connect(
            self.visual_preference_widget_closed
        )
        self.visual_preference_widget.update_preferences.connect(
            self.update_visual_preferences.emit
        )
        self.visual_preference_widget.show()

    def visual_preference_widget_closed(self):
        self.visual_preference_widget = None


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = QtWidgets.QMainWindow()
    main_menu = MenuBar(main_window)
    main_window.setMenuBar(main_menu)
    main_window.show()

    app.exec()
