from pathlib import Path

import qtawesome as qta

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import BaseDock, FileListWidget, tab10_qcolor


class FilesDock(BaseDock):
    video_file_changed = Signal(Path)
    batch_button_toggled = Signal(Path)

    def __init__(self, filetypes=None):
        super().__init__()

        self.setWindowTitle("Files")

        self.setFeatures(
            self.DockWidgetFeature.DockWidgetFloatable
            | self.DockWidgetFeature.DockWidgetMovable
        )

        icon_size = 18
        self.batch_button = QtWidgets.QPushButton(self)
        self.continue_icon = qta.icon("mdi.playlist-play")
        self.batch_button.setIcon(self.continue_icon)
        self.batch_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.batch_button.setCheckable(True)
        self.batch_button.setFlat(True)
        self.batch_button.setText("Batch Processing")
        self.batch_button.setToolTip(
            "Automatically continue to next video in queue and start playing."
        )
        self.gui_save_exceptions.append(self.batch_button)
        self.batch_button.toggled.connect(self.batch_button_toggled.emit)
        self.dock_layout.addWidget(self.batch_button)

        self.file_list_widget = FileListWidget(filetypes, self)
        self.file_list_widget.setToolTip("Quick files.\nDrop files here.")
        self.dock_layout.addWidget(self.file_list_widget)

        self.files_action_layout = QtWidgets.QBoxLayout(
            QtWidgets.QBoxLayout.LeftToRight
        )
        self.dock_layout.addLayout(self.files_action_layout)

        self.sort_ascend_button = QtWidgets.QPushButton(self)
        self.sort_ascend_button.setIcon(qta.icon("mdi.sort-alphabetical-ascending"))
        self.sort_ascend_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.sort_ascend_button.setToolTip("Sort ascending.")
        self.sort_ascend_button.setFlat(True)
        self.sort_ascend_button.clicked.connect(self.file_list_widget.sort_ascend)
        self.files_action_layout.addWidget(self.sort_ascend_button)

        self.sort_descend_button = QtWidgets.QPushButton(self)
        self.sort_descend_button.setIcon(qta.icon("mdi.sort-alphabetical-descending"))
        self.sort_descend_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.sort_descend_button.setToolTip("Sort descending.")
        self.sort_descend_button.setFlat(True)
        self.sort_descend_button.clicked.connect(self.file_list_widget.sort_descend)
        self.files_action_layout.addWidget(self.sort_descend_button)

        self.remove_selection_button = QtWidgets.QPushButton(self)
        self.remove_selection_button.setIcon(
            qta.icon("mdi.delete", color=tab10_qcolor["red"])
        )
        self.remove_selection_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.remove_selection_button.setToolTip("Remove selection.")
        self.remove_selection_button.setFlat(True)
        self.remove_selection_button.clicked.connect(
            self.file_list_widget.remove_selection
        )
        self.files_action_layout.addWidget(self.remove_selection_button)

        self.remove_all_button = QtWidgets.QPushButton(self)
        self.remove_all_button.setIcon(
            qta.icon("mdi.delete-empty", color=tab10_qcolor["red"])
        )
        self.remove_all_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.remove_all_button.setToolTip("Remove all.")
        self.remove_all_button.setFlat(True)
        self.remove_all_button.clicked.connect(self.file_list_widget.remove_all)
        self.files_action_layout.addWidget(self.remove_all_button)

        self.layout_direction_changed.connect(self.change_action_layout)

        self.file_list_widget.itemSelectionChanged.connect(self.item_selection_changed)
        self.file_list_widget.itemDoubleClicked.connect(self.item_selection_changed)

    def next_file(self):
        row = self.file_list_widget.currentRow()
        row += 1
        max_row = self.file_list_widget.count()
        if row < max_row:
            self.file_list_widget.setCurrentRow(row)

    def previous_file(self):
        row = self.file_list_widget.currentRow()
        row -= 1
        if row >= 0:
            self.file_list_widget.setCurrentRow(row)

    def item_selection_changed(self):
        item = self.file_list_widget.currentItem()
        if item is not None:
            path = self.file_list_widget.full_paths[item.text()]
            self.video_file_changed.emit(path)
        else:
            self.video_file_changed.emit(None)
            path = None

    def change_action_layout(self, direction):
        if direction == QtWidgets.QBoxLayout.LeftToRight:
            self.files_action_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        elif direction == QtWidgets.QBoxLayout.TopToBottom:
            self.files_action_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = FilesDock(["video"])
    widget.show()

    app.exec()
