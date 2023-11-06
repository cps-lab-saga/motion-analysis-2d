from pathlib import Path

import qtawesome as qta

from defs import QtCore, QtWidgets
from motion_analysis_2d.custom_components.my_colors import tab10_qcolor
from motion_analysis_2d.funcs import guess_file_type, check_file_type


class FileListWidget(QtWidgets.QListWidget):
    def __init__(self, filetypes=None, parent=None):
        super().__init__(parent=parent)

        self.filetypes = filetypes
        self.setAcceptDrops(True)

        self.setWordWrap(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.full_paths = {}

        self.image_file_icons = {
            "jpeg": qta.icon("mdi.file-image", color=tab10_qcolor["blue"]),
            "png": qta.icon("mdi.file-image", color=tab10_qcolor["purple"]),
            "tiff": qta.icon("mdi.file-image", color=tab10_qcolor["green"]),
            "bmp": qta.icon("mdi.file-image", color=tab10_qcolor["cyan"]),
            "svg+xml": qta.icon("mdi.file-image", color=tab10_qcolor["pink"]),
            "x-emf": qta.icon("mdi.file-image", color=tab10_qcolor["gray"]),
            "gif": qta.icon("mdi.file-image", color=tab10_qcolor["orange"]),
            "generic": qta.icon("mdi.file-image", color=tab10_qcolor["red"]),
        }
        self.video_file_icons = {
            "mp4": qta.icon("mdi.file-video", color=tab10_qcolor["blue"]),
            "webm": qta.icon("mdi.file-video", color=tab10_qcolor["purple"]),
            "x-matroska": qta.icon("mdi.file-video", color=tab10_qcolor["green"]),
            "x-ms-wmv": qta.icon("mdi.file-video", color=tab10_qcolor["cyan"]),
            "mpeg": qta.icon("mdi.file-video", color=tab10_qcolor["pink"]),
            "quicktime": qta.icon("mdi.file-video", color=tab10_qcolor["gray"]),
            "avi": qta.icon("mdi.file-video", color=tab10_qcolor["orange"]),
            "generic": qta.icon("mdi.file-video", color=tab10_qcolor["red"]),
        }

    def add_file_to_list(self, file_path):
        key = file_path.name
        keys_prev = [k for k, v in self.full_paths.items() if key == v.name]
        paths_prev = [self.full_paths[k] for k in keys_prev]
        file_type = guess_file_type(file_path)
        # if doesn't exist, create new file.
        # if exists, check if it's the same file.
        #   if it's the same, move file to top.
        #   if not the same, remove add parent dir(s) until unique
        if not keys_prev:
            self.full_paths[key] = file_path
            self.generate_file_item(key, file_type)
        else:
            if file_path in paths_prev:
                # move to top
                i = paths_prev.index(file_path)
                k_prev = keys_prev[i]
                item = self.findItems(k_prev, QtCore.Qt.MatchExactly)[0]
                row = self.row(item)
                self.takeItem(row)
                self.insertItem(0, item)
                self.setCurrentItem(item)
            else:
                keys_new = [key] * len(keys_prev)
                key_curr = key
                lvl = 0
                while len(set(keys_new + [key_curr])) < len(keys_new + [key_curr]):
                    for i, p in enumerate(paths_prev):
                        keys_new[i] = "/".join([p.parents[lvl].name, keys_new[i]])
                    key_curr = "/".join([file_path.parents[lvl].name, key_curr])
                    lvl += 1

                for k_prev, k_new, p in zip(keys_prev, keys_new, paths_prev):
                    item = self.findItems(k_prev, QtCore.Qt.MatchExactly)[0]
                    item.setText(k_new)
                    self.full_paths[k_new] = p
                    del self.full_paths[k_prev]

                self.full_paths[key_curr] = file_path
                self.generate_file_item(key_curr, file_type)

    def generate_file_item(self, key, file_type):
        file_type, subtype = file_type.split("/")
        file_item = QtWidgets.QListWidgetItem(key)
        if file_type == "video":
            if subtype in self.video_file_icons.keys():
                file_item.setIcon(self.video_file_icons[subtype])
            else:
                file_item.setIcon(self.video_file_icons["generic"])

        elif file_type == "image":
            if subtype in self.video_file_icons.keys():
                file_item.setIcon(self.image_file_icons[subtype])
            else:
                file_item.setIcon(self.image_file_icons["generic"])

        self.insertItem(0, file_item)
        self.setCurrentItem(file_item)

    def valid_paths(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if Path(urls[0].toLocalFile()).is_dir():
                paths = Path(urls[0].toLocalFile()).glob("*")
            else:
                paths = (Path(url.toLocalFile()) for url in e.mimeData().urls())
            if self.filetypes is None:
                return [p for p in paths if p.is_file()]
            else:
                return [p for p in paths if check_file_type(p, self.filetypes)]

    def valid_path(self, e):
        if e.mimeData().hasUrls():
            path = Path(e.mimeData().urls()[0].toLocalFile())
            if self.filetypes is None and path.is_file():
                return path
            if check_file_type(path, self.filetypes):
                return path

    def dragEnterEvent(self, e):
        if self.valid_paths(e):
            e.acceptProposedAction()
            e.setDropAction(QtCore.Qt.LinkAction)
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self.valid_paths(e):
            e.acceptProposedAction()
            e.setDropAction(QtCore.Qt.LinkAction)
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if paths := self.valid_paths(e):
            for p in paths:
                self.blockSignals(True)
                self.add_file_to_list(p)
                self.blockSignals(False)
            self.itemSelectionChanged.emit()
            e.accept()
        else:
            super().dropEvent(e)

    def remove_all(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)
        self.full_paths = {}
        self.itemSelectionChanged.emit()

    def remove_selection(self):
        items = self.selectedItems()
        for item in items:
            row = self.row(item)

            self.blockSignals(True)
            self.takeItem(row)
            self.blockSignals(False)

            del self.full_paths[item.text()]
            self.itemSelectionChanged.emit()

    def sort_ascend(self):
        self.sortItems(QtCore.Qt.AscendingOrder)

    def sort_descend(self):
        self.sortItems(QtCore.Qt.DescendingOrder)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = FileListWidget(filetypes=["video"])
    widget.show()

    app.exec()
