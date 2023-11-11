import logging
import sys
from queue import Queue
from time import sleep

import numpy as np
from PySide6 import QtGui

from defs import QtCore, QtWidgets, project_root, log_file, settings_file, resource_dir
from motion_analysis_2d.controls import EditControls, MediaControls
from motion_analysis_2d.custom_components import tab10_rgb_cycle
from motion_analysis_2d.dialogs import TrackerDialog, AngleDialog
from motion_analysis_2d.display_widgets import FrameWidget
from motion_analysis_2d.docks import (
    FilesDock,
    LoadIntrinsicDock,
    LoadExtrinsicDock,
    OrientDock,
    TrackingDock,
    SaveDock,
    ItemsDock,
    DataPlotDock,
)
from motion_analysis_2d.funcs import (
    save_tracking_data,
    load_tracking_data,
    export_csv,
    load_shortcut_keys,
)
from motion_analysis_2d.workers import StreamWorker, TrackingWorker


class MainWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("2D Motion Analysis")
        self.setWindowIcon(QtGui.QIcon(str(resource_dir() / "motion_analysis_2d.svg")))
        self.resize(800, 600)

        self.setup_logger()
        self.log_new_session()

        self.main_widget = QtWidgets.QWidget(parent=self)
        self.main_layout = QtWidgets.QGridLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.frame_widget = FrameWidget(self)
        self.frame_widget.new_tracker_suggested.connect(self.tracker_suggested)
        self.frame_widget.tracker_added.connect(self.add_tracker)
        self.frame_widget.tracker_moved.connect(self.move_tracker)
        self.frame_widget.tracker_removed.connect(self.remove_tracker)
        self.frame_widget.marker_file_dropped.connect(self.load_markers)
        self.frame_widget.new_angle_suggested.connect(self.angle_suggested)
        self.frame_widget.angle_added.connect(self.add_angle)
        self.frame_widget.angle_removed.connect(self.remove_angle)
        self.main_layout.addWidget(self.frame_widget, 0, 0)

        self.edit_controls = EditControls(self, "vertical")
        self.edit_controls.mode_changed.connect(self.edit_mode_changed)
        self.edit_controls.setDisabled(True)
        self.main_layout.addWidget(self.edit_controls, 0, 1)

        self.media_controls = MediaControls(self, "horizontal")
        self.media_controls.play.connect(self.play_video)
        self.media_controls.next_frame.connect(self.move_frame_forwards)
        self.media_controls.previous_frame.connect(self.move_frame_backwards)
        self.media_controls.seek_bar_moved.connect(self.seek_bar_moved)
        self.media_controls.setDisabled(True)
        self.main_layout.addWidget(self.media_controls, 1, 0, 1, 2)

        self.setCorner(QtCore.Qt.TopLeftCorner, QtCore.Qt.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.BottomLeftCorner, QtCore.Qt.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.TopRightCorner, QtCore.Qt.RightDockWidgetArea)
        # self.setCorner(QtCore.Qt.BottomRightCorner, QtCore.Qt.RightDockWidgetArea)

        self.docks = {
            "Files": FilesDock(["video"]),
            "Intrinsic": LoadIntrinsicDock(),
            "Extrinsic": LoadExtrinsicDock(),
            "Orient": OrientDock(),
            "Tracking": TrackingDock(),
            "Save": SaveDock(),
            "Items": ItemsDock(),
            "DataPlot": DataPlotDock(),
        }
        for dock in self.docks.values():
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks["Items"])
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.docks["DataPlot"])
        self.docks["Files"].video_file_changed.connect(self.video_file_changed)
        self.docks["Orient"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Tracking"].track_enabled.connect(self.track_enabled)
        self.docks["Tracking"].reset_trackers_button.clicked.connect(
            self.reset_trackers
        )
        self.docks["Save"].autosave_toggled.connect(self.autosave_toggled)
        self.docks["Save"].export_clicked.connect(self.export_data)
        self.docks["DataPlot"].frame_line_dragged.connect(
            self.media_controls.seek_bar.setValue
        )

        # thread for streaming input
        self.stream_thread = QtCore.QThread()
        self.stream_worker = None
        self.stream_queue = Queue(maxsize=1)
        self.streaming = False

        # thread for track_blocks processing
        self.tracking_thread = QtCore.QThread()
        self.tracking_worker = TrackingWorker(
            self.stream_queue,
        )
        self.tracking_worker.moveToThread(self.tracking_thread)
        self.tracking_worker.add_tracker_failed.connect(self.add_tracker_failed)
        self.tracking_worker.tracking_failed.connect(self.tracking_failed)
        self.tracking_thread.started.connect(self.tracking_worker.run)
        self.tracking_thread.start()

        # periodically update display widgets
        self.camera_frame_update_timer = QtCore.QTimer()
        self.camera_frame_update_timer.timeout.connect(self.update_frame_view)

        # periodically autosave data if enabled
        self.autosave_timer = QtCore.QTimer()
        self.autosave_timer.timeout.connect(self.save_data)

        self.shortcut_keys = {
            "\N{ESCAPE}": "set_normal_mode",
            "F": "move_frame_forwards",
            "S": "move_frame_backwards",
        }
        try:
            self.shortcut_keys.update(
                load_shortcut_keys(project_root() / "shortcut_keys.json")
            )
        except Exception as e:
            self.error_dialog(f"Failed to read shortcut keys file!\n{e}")

        # load settings from previous session
        self.settings_file = settings_file()
        if self.settings_file.is_file():
            settings = QtCore.QSettings(
                str(self.settings_file), QtCore.QSettings.IniFormat
            )
            self.gui_restore(settings)

    def video_file_changed(self, path):
        self.media_controls.pause()

        self.camera_frame_update_timer.stop()
        self.edit_controls.set_normal_mode()
        self.edit_controls.setDisabled(True)
        self.media_controls.set_seek_bar_value(0)
        self.media_controls.setDisabled(True)
        self.docks["Save"].autosave_button_toggled()
        self.docks["Items"].clear()
        self.docks["DataPlot"].clear()
        self.docks["DataPlot"].set_frame_line_draggable(False)
        self.docks["DataPlot"].move_frame_line(0)
        self.tracking_worker.no_of_frames = 0

        self.close_video()
        self.frame_widget.clear()
        with self.stream_queue.mutex:
            self.stream_queue.queue.clear()
        self.tracking_worker.clear_data()

        if path is not None:
            self.start_stream(path)
            self.edit_controls.setDisabled(False)
            self.media_controls.setDisabled(False)
            self.docks["Tracking"].track_button_toggled()
            self.docks["DataPlot"].set_frame_line_draggable(True)
            self.camera_frame_update_timer.start(30)

            while self.tracking_worker.no_of_frames == 0:
                QtCore.QCoreApplication.processEvents()
                sleep(0.2)

            self.frame_widget.auto_range()
            track_file = path.parent / (path.stem + ".json")
            if track_file.is_file():
                logging.info("Data file exist!")
                self.load_data(track_file)

    def close_video(self):
        if self.streaming:
            self.stream_worker.set_stop()
            while self.streaming:  # wait till capture is closed
                sleep(0.1)
                QtCore.QCoreApplication.processEvents()

    def start_stream(self, path):
        self.stream_worker = StreamWorker(
            path,
            self.stream_queue,
            self.docks["Intrinsic"],
            self.docks["Extrinsic"],
            self.docks["Orient"],
        )
        self.stream_worker.moveToThread(self.stream_thread)
        self.stream_thread.started.connect(self.stream_worker.stream)
        self.stream_worker.stream_props.connect(self.set_stream_props)
        self.stream_worker.finished.connect(self.stream_finished)
        self.stream_thread.start()
        self.streaming = True

    def set_stream_props(self, frame_rate, no_of_frames):
        self.tracking_worker.set_props(no_of_frames)
        self.media_controls.set_seeking_props(no_of_frames - 2)
        self.docks["DataPlot"].set_frame_bound((0, no_of_frames - 2))

    def play_video(self, play):
        if self.stream_worker is not None:
            if play:
                self.stream_worker.set_play()
                self.docks["DataPlot"].set_frame_line_draggable(False)
                self.edit_controls.blockSignals(True)
                self.edit_controls.set_normal_mode()
                self.frame_widget.set_mouse_mode("normal")
                self.edit_controls.blockSignals(False)
            else:
                self.docks["DataPlot"].set_frame_line_draggable(True)
                self.stream_worker.set_pause()

    def toggle_play(self):
        self.media_controls.play_button.toggle()

    def toggle_track(self):
        self.docks["Tracking"].track_button.toggle()

    def toggle_autosave(self):
        self.docks["Save"].autosave_button.toggle()

    def click_export(self):
        self.docks["Save"].export_button.click()

    def stream_finished(self):
        self.stream_thread.exit()
        self.stream_worker = None
        self.streaming = False

    def track_enabled(self, track):
        if self.stream_worker is not None:
            self.stream_worker.set_tracking(track)

    def update_frame_view(self):
        if self.stream_worker is not None:
            i = self.tracking_worker.frame_no
            self.frame_widget.update_frame(
                self.tracking_worker.frame,
                self.tracking_worker.frame_no,
                self.tracking_worker.timestamp / 1000,
            )
            for name, tracking_data in self.tracking_worker.tracking_data.items():
                self.frame_widget.move_tracker(
                    name,
                    tracking_data["bbox"][i],
                    tracking_data["target"][i],
                )
                self.frame_widget.show_trajectory(
                    name,
                    self.tracking_worker.frame_no,
                    tracking_data["target"],
                )
                self.docks["DataPlot"].update_tracker(
                    name,
                    tracking_data["target"],
                )
            for name, angle_data in self.tracking_worker.analysis_data["angle"].items():
                self.docks["DataPlot"].update_angle(
                    name,
                    angle_data["angle"],
                )

            self.media_controls.set_seek_bar_value(self.tracking_worker.frame_no)
            self.docks["DataPlot"].move_frame_line(self.tracking_worker.frame_no)

    def move_frame_forwards(self):
        if self.stream_worker is not None:
            self.stream_worker.move_frame_forwards()

    def move_frame_backwards(self):
        if self.stream_worker is not None:
            self.stream_worker.move_frame_backwards()

    def frame_shape_changed(self):
        if self.stream_worker is not None:
            self.stream_worker.read_current_frame()
            self.update_frame_view()
            self.frame_widget.frame_shape_changed()

    def seek_bar_moved(self, frame_no):
        if self.stream_worker is not None:
            self.stream_worker.move_frame_to(frame_no)
            self.tracking_worker.reset_trackers()

    def edit_mode_changed(self, mode):
        self.media_controls.pause()

        if mode == "add_tracker":
            self.frame_widget.set_mouse_mode("add_tracker")
        elif mode == "remove_tracker":
            self.frame_widget.set_mouse_mode("remove_tracker")
        elif mode == "add_angle":
            self.frame_widget.set_mouse_mode("add_angle")
        elif mode == "remove_angle":
            self.frame_widget.set_mouse_mode("remove_angle")
        else:
            self.frame_widget.remove_temp_tracker()
            self.frame_widget.remove_temp_angle()
            self.frame_widget.set_mouse_mode("normal")

    def set_normal_mode(self):
        self.edit_controls.set_normal_mode()

    def tracker_suggested(self, bbox_pos, bbox_size, offset):
        dialog = TrackerDialog(default_color=next(tab10_rgb_cycle))
        dialog.exec()
        if dialog.result():
            name, color, tracker_type = dialog.get_inputs()
            self.frame_widget.remove_temp_tracker()

            self.frame_widget.add_tracker(
                name, bbox_pos, bbox_size, offset, color, tracker_type
            )

        else:
            self.frame_widget.remove_temp_tracker()

    def add_tracker(self, name, bbox_pos, bbox_size, offset, color, tracker_type):
        self.tracking_worker.add_tracker(
            name, bbox_pos, bbox_size, offset, tracker_type
        )
        self.docks["Items"].add_row(name, color, "tracker")
        self.docks["DataPlot"].add_tracker(name, color)

    def tracking_failed(self, name, frame_no):
        self.media_controls.pause()
        with self.stream_queue.mutex:
            self.stream_queue.queue.clear()
        self.error_dialog(f"Tracking failed for {name} at frame {frame_no}!")

    def add_tracker_failed(self, name, error):
        self.docks["Items"].remove_row(name, "tracker")
        self.error_dialog(f"Could not initialise tracker for ({name})!\n{error}")

    def remove_tracker(self, name):
        self.tracking_worker.remove_tracker(name)
        self.docks["Items"].remove_row(name, "tracker")
        self.docks["DataPlot"].remove_tracker(name)

    def reset_trackers(self):
        self.tracking_worker.reset_trackers()

    def move_tracker(self, name, bbox_pos, bbox_size, offset, color, tracker_type):
        self.tracking_worker.add_tracker(
            name, bbox_pos, bbox_size, offset, tracker_type
        )

    def angle_suggested(self, start1, end1, start2, end2):
        dialog = AngleDialog(default_color=next(tab10_rgb_cycle))
        dialog.exec()
        if dialog.result():
            name, color = dialog.get_inputs()
            self.frame_widget.remove_temp_angle()

            self.frame_widget.add_angle(
                name,
                start1,
                end1,
                start2,
                end2,
                color,
            )

        else:
            self.frame_widget.remove_temp_angle()

    def add_angle(self, name, start1, end1, start2, end2, color):
        self.tracking_worker.add_angle(name, start1, end1, start2, end2)
        self.docks["Items"].add_row(name, color, "angle")
        self.docks["DataPlot"].add_angle(name, color)

    def remove_angle(self, name):
        self.docks["Items"].remove_row(name, "angle")
        self.docks["DataPlot"].remove_angle(name)

    def save_data(self):
        if self.stream_worker is not None:
            video_path = self.stream_worker.path
            save_path = video_path.parent / f"{video_path.stem}.json"
            save_tracking_data(
                save_path,
                {
                    k: v
                    for k, v in self.frame_widget.trackers.items()
                    if k in ["name", "offset", "color", "tracker_type"]
                },
                self.tracking_worker.tracking_data,
                self.tracking_worker.frame_no,
            )

    def load_data(self, path):
        tracker_properties, tracking_data, current_frame = load_tracking_data(path)
        self.media_controls.seek_bar.setValue(current_frame)
        self.tracking_worker.set_tracking_data(tracking_data)
        for name, offset, color, tracker_type in zip(
            tracker_properties["name"],
            tracker_properties["offset"],
            tracker_properties["color"],
            tracker_properties["tracker_type"],
        ):
            bbox = tracking_data[name]["bbox"][current_frame].astype(np.int32)

            self.frame_widget.add_tracker(
                name,
                bbox[:2],
                bbox[2:],
                offset,
                color,
                tracker_type,
            )

    def load_markers(self, path):
        try:
            tracker_properties, tracking_data, _ = load_tracking_data(path)
            for name, offset, color, tracker_type in zip(
                tracker_properties["name"],
                tracker_properties["offset"],
                tracker_properties["color"],
                tracker_properties["tracker_type"],
            ):
                bbox = tracking_data[name]["bbox"][1].astype(np.int32)

                self.frame_widget.add_tracker(
                    name,
                    bbox[:2],
                    bbox[2:],
                    offset,
                    color,
                    tracker_type,
                )
        except Exception as e:
            self.error_dialog(f"Failed to load markers.\n{e}")

    def export_data(self, path):
        try:
            export_csv(path, self.tracking_worker.tracking_data)
        except Exception as e:
            self.error_dialog(e)

    def autosave_toggled(self, autosave):
        if autosave:
            self.save_data()
            self.autosave_timer.start(30000)  # every 30 s
        else:
            self.autosave_timer.stop()

    def gui_save(self, settings):
        for dock in self.docks.values():
            dock.gui_save(settings)
        settings.setValue("Window/geometry", self.saveGeometry())
        settings.setValue("Window/state", self.saveState())

    def gui_restore(self, settings):
        try:
            if geometry := settings.value("Window/geometry"):
                self.restoreGeometry(geometry)
            if state := settings.value("Window/state"):
                self.restoreState(state)
            for dock in self.docks.values():
                dock.gui_restore(settings)

        except Exception as e:
            self.error_dialog(f"{self.settings_file} is corrupted!\n{str(e)}")

    def closeEvent(self, event):
        """save before closing"""
        self.docks["Save"].autosave_button_toggled()
        settings = QtCore.QSettings(str(self.settings_file), QtCore.QSettings.IniFormat)
        self.gui_save(settings)
        event.accept()

    def error_dialog(self, error):
        QtWidgets.QMessageBox.critical(self, "Error", error)

    def keyPressEvent(self, evt):
        if cmd := self.shortcut_keys.get(evt.text().upper()):
            getattr(self, cmd)()

    @staticmethod
    def setup_logger():
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

        log_handler_stdout = logging.StreamHandler(sys.stdout)
        log_handler_stdout.setFormatter(formatter)

        log_handler_file = logging.FileHandler(log_file())
        log_handler_file.setFormatter(formatter)

        log = logging.getLogger()
        log.setLevel(logging.DEBUG)
        log.addHandler(log_handler_stdout)
        log.addHandler(log_handler_file)

    @staticmethod
    def log_new_session():
        banner = "-" * 20 + " New Session " + "-" * 20
        logging.info("")
        logging.info("=" * len(banner))
        logging.info(banner)
        logging.info("=" * len(banner))


def main():
    app = QtWidgets.QApplication([])
    win = MainWidget()
    win.show()

    app.exec()


if __name__ == "__main__":
    main()
