from pathlib import Path

import qtawesome as qta

from motion_analysis_2d.defs import QtWidgets, Signal, open_file, project_root
from motion_analysis_2d.funcs import get_extensions_for_type


class MenuBar(QtWidgets.QMenuBar):
    open_video_file = Signal(object)
    open_video_folder = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.file_menu = self.addMenu("File")

        self.open_video_file_action = self.file_menu.addAction(
            qta.icon("mdi6.file-video"), "Open Video File..."
        )
        self.open_video_file_action.triggered.connect(self.add_file)

        self.open_video_folder_action = self.file_menu.addAction(
            qta.icon("mdi6.folder-open"), "Open Video Folder..."
        )
        self.open_video_folder_action.triggered.connect(self.add_folder)

        self.edit_menu = self.addMenu("Edit")
        self.settings_action = self.edit_menu.addAction(
            qta.icon("ri.settings-5-fill"), "Settings"
        )
        self.settings_action.triggered.connect(self.open_settings)

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

    @staticmethod
    def open_settings():
        open_file(project_root() / "application_settings.json")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = QtWidgets.QMainWindow()
    main_menu = MenuBar(main_window)
    main_window.setMenuBar(main_menu)
    main_window.show()

    app.exec()
