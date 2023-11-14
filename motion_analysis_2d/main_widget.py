import logging
from pathlib import Path
from queue import Queue
from time import sleep

import numpy as np
from PySide6 import QtGui

from defs import QtCore, QtWidgets, project_root, settings_file, resource_dir
from motion_analysis_2d.controls import EditControls, MediaControls
from motion_analysis_2d.custom_components import tab10_rgb_cycle
from motion_analysis_2d.dialogs import TrackerDialog, AngleDialog, DistanceDialog
from motion_analysis_2d.display_widgets import FrameWidget
from motion_analysis_2d.docks import (
    FilesDock,
    LoadIntrinsicDock,
    LoadExtrinsicDock,
    OrientDock,
    SaveDock,
    ItemsDock,
    DataPlotDock,
)
from motion_analysis_2d.funcs import (
    setup_logger,
    save_tracking_data,
    load_tracking_data,
    export_csv,
    load_shortcut_keys,
    save_warp_points,
)
from motion_analysis_2d.splashscreen import SplashScreen
from motion_analysis_2d.workers import StreamWorker, TrackingWorker


class MainWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.splashscreen = SplashScreen()
        self.splashscreen.show()

        self.setWindowTitle("2D Motion Analysis")
        self.setWindowIcon(QtGui.QIcon(str(resource_dir() / "motion_analysis_2d.svg")))
        self.resize(800, 600)

        self.log_new_session()

        self.main_widget = QtWidgets.QWidget(parent=self)
        self.main_layout = QtWidgets.QGridLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.frame_widget = FrameWidget(self)
        self.frame_widget.new_tracker_suggested.connect(self.tracker_suggested)
        self.frame_widget.tracker_added.connect(self.add_tracker)
        self.frame_widget.tracker_moved.connect(self.move_tracker)
        self.frame_widget.tracker_removed.connect(self.remove_tracker)
        self.frame_widget.new_angle_suggested.connect(self.angle_suggested)
        self.frame_widget.angle_added.connect(self.add_angle)
        self.frame_widget.angle_moved.connect(self.move_angle)
        self.frame_widget.angle_removed.connect(self.remove_angle)
        self.frame_widget.new_distance_suggested.connect(self.distance_suggested)
        self.frame_widget.distance_added.connect(self.add_distance)
        self.frame_widget.distance_moved.connect(self.move_distance)
        self.frame_widget.distance_removed.connect(self.remove_distance)
        self.frame_widget.marker_file_dropped.connect(self.load_markers)
        self.frame_widget.new_warp_points_selected.connect(self.warp_points_selected)
        self.main_layout.addWidget(self.frame_widget, 0, 0)

        self.splashscreen.set_progress(20)

        self.edit_controls = EditControls(self, "vertical")
        self.edit_controls.mode_changed.connect(self.edit_mode_changed)
        self.edit_controls.setDisabled(True)
        self.main_layout.addWidget(self.edit_controls, 0, 1)

        self.media_controls = MediaControls(self, "horizontal")
        self.media_controls.play.connect(self.play_video)
        self.media_controls.next_frame.connect(self.move_frame_forwards)
        self.media_controls.previous_frame.connect(self.move_frame_backwards)
        self.media_controls.seek_bar_moved.connect(self.seek_bar_moved)
        self.media_controls.track_enabled.connect(self.track_enabled)
        self.media_controls.setDisabled(True)
        self.main_layout.addWidget(self.media_controls, 1, 0, 1, 2)

        self.setCorner(QtCore.Qt.TopLeftCorner, QtCore.Qt.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.BottomLeftCorner, QtCore.Qt.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.TopRightCorner, QtCore.Qt.RightDockWidgetArea)
        # self.setCorner(QtCore.Qt.BottomRightCorner, QtCore.Qt.RightDockWidgetArea)

        self.docks = {
            "Files": FilesDock(["video"]),
            "Orient": OrientDock(),
            "Intrinsic": LoadIntrinsicDock(),
            "Extrinsic": LoadExtrinsicDock(),
            "Save": SaveDock(),
            "Items": ItemsDock(),
            "DataPlot": DataPlotDock(),
        }
        for dock in self.docks.values():
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.docks["Items"])
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.docks["DataPlot"])
        self.docks["Files"].video_file_changed.connect(self.video_file_changed)
        self.docks["Intrinsic"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Extrinsic"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Extrinsic"].select_points_started.connect(self.start_select_points)
        self.docks["Extrinsic"].select_points_finished.connect(
            self.finish_select_points
        )
        self.docks["Extrinsic"].select_points_button.setDisabled(True)
        self.docks["Orient"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Items"].show_item.connect(self.show_item)
        self.docks["Items"].hide_item.connect(self.hide_item)
        self.docks["Items"].remove_item.connect(self.remove_item)
        self.docks["Save"].autosave_toggled.connect(self.autosave_toggled)
        self.docks["Save"].export_clicked.connect(self.export_data)
        self.docks["DataPlot"].frame_line_dragged.connect(
            self.media_controls.seek_bar.setValue
        )

        self.splashscreen.set_progress(50)

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
        self.tracking_worker.reached_end.connect(self.reached_end)
        self.tracking_worker.tracking_failed.connect(self.tracking_failed)
        self.tracking_thread.started.connect(self.tracking_worker.run)
        self.tracking_thread.start()

        self.splashscreen.set_progress(70)

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

        self.splashscreen.set_progress(90)

        # load settings from previous session
        self.settings_file = settings_file()
        if self.settings_file.is_file():
            settings = QtCore.QSettings(
                str(self.settings_file), QtCore.QSettings.IniFormat
            )
            self.gui_restore(settings)

        self.splashscreen.finish(self)

    def video_file_changed(self, path):
        self.play_video(False)

        self.camera_frame_update_timer.stop()
        self.edit_controls.set_normal_mode()
        self.edit_controls.setDisabled(True)
        self.media_controls.set_seek_bar_value(0)
        self.media_controls.setDisabled(True)
        self.docks["Extrinsic"].select_points_button.setDisabled(True)
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
            self.media_controls.track_button_toggled()
            self.docks["Extrinsic"].select_points_button.setDisabled(False)
            self.frame_widget.update_scaling(self.docks["Extrinsic"].scaling)
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

            if self.docks["Files"].continue_button.isChecked():
                self.play_video(True)

    def close_video(self):
        if self.streaming:
            self.stream_worker.set_stop()
            while self.streaming:  # wait till capture is closed
                sleep(0.1)
                QtCore.QCoreApplication.processEvents()

    def next_video(self):
        logging.info("Go to next video")
        self.docks["Files"].next_file()

    def previous_video(self):
        logging.info("Go to previous video")
        self.docks["Files"].previous_file()

    def reached_end(self):
        if self.docks["Files"].continue_button.isChecked():
            self.play_video(False)
            self.next_video()

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
                self.media_controls.blockSignals(True)
                self.media_controls.play_button.setChecked(True)
                self.media_controls.blockSignals(True)

                self.stream_worker.set_play()
                self.docks["DataPlot"].set_frame_line_draggable(False)
                self.edit_controls.blockSignals(True)
                self.edit_controls.set_normal_mode()
                self.frame_widget.set_mouse_mode("normal")
                self.edit_controls.blockSignals(False)

                if self.media_controls.track_button.isChecked():
                    self.media_controls.set_tracking(True)
                else:
                    self.media_controls.set_tracking(False)

            else:
                self.media_controls.blockSignals(True)
                self.media_controls.play_button.setChecked(False)
                self.media_controls.blockSignals(True)

                self.docks["DataPlot"].set_frame_line_draggable(True)
                self.stream_worker.set_pause()
                self.media_controls.set_tracking(False)

    def toggle_play(self):
        self.media_controls.play_button.toggle()

    def toggle_track(self):
        self.media_controls.track_button.toggle()

    def toggle_autosave(self):
        self.docks["Save"].autosave_button.toggle()

    def click_export(self):
        self.docks["Save"].export_button.click()

    def stream_finished(self):
        self.stream_thread.exit()
        self.stream_worker = None
        self.streaming = False

    def track_enabled(self, track):
        if track:
            if self.media_controls.play_button.isChecked():
                self.media_controls.set_tracking(True)
                self.tracking_worker.reset_trackers()
        else:
            self.media_controls.set_tracking(False)

        if self.stream_worker is not None:
            self.stream_worker.set_tracking(track)

    def update_frame_view(self):
        if self.stream_worker is not None:
            i = self.tracking_worker.frame_no - 1
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
                    i,
                    tracking_data["target"],
                )
                self.docks["DataPlot"].update_tracker(
                    name,
                    tracking_data["target"] / self.docks["Extrinsic"].scaling,
                    frames=tracking_data["frame_no"],
                )
            for name, angle_data in self.tracking_worker.analysis_data["angle"].items():
                self.docks["DataPlot"].update_angle(
                    name,
                    angle_data["angle"],
                    frames=angle_data["frame_no"],
                )
            for name, distance_data in self.tracking_worker.analysis_data[
                "distance"
            ].items():
                self.docks["DataPlot"].update_distance(
                    name,
                    distance_data["distance"] / self.docks["Extrinsic"].scaling,
                    frames=distance_data["frame_no"],
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
            self.frame_widget.update_scaling(self.docks["Extrinsic"].scaling)
            self.stream_worker.read_current_frame()
            self.update_frame_view()
            self.frame_widget.frame_shape_changed()

    def seek_bar_moved(self, frame_no):
        if self.stream_worker is not None:
            self.stream_worker.move_frame_to(frame_no)
            self.tracking_worker.reset_trackers()

    def edit_mode_changed(self, mode):
        self.play_video(False)
        while not self.stream_queue.empty():
            sleep(0.1)

        if mode == "add_tracker":
            self.frame_widget.set_mouse_mode("add_tracker")
        elif mode == "remove_tracker":
            self.frame_widget.set_mouse_mode("remove_tracker")
        elif mode == "add_angle":
            self.frame_widget.set_mouse_mode("add_angle")
        elif mode == "remove_angle":
            self.frame_widget.set_mouse_mode("remove_angle")
        elif mode == "add_distance":
            self.frame_widget.set_mouse_mode("add_distance")
        elif mode == "remove_distance":
            self.frame_widget.set_mouse_mode("remove_distance")
        elif mode == "select_warp_points":
            self.frame_widget.set_mouse_mode("select_warp_points")
        else:
            self.frame_widget.remove_temp_tracker()
            self.frame_widget.remove_temp_angle()
            self.frame_widget.remove_temp_distance()
            self.frame_widget.remove_warp_points()
            self.frame_widget.set_mouse_mode("normal")

    def set_normal_mode(self):
        self.edit_controls.set_normal_mode()
        self.docks["Extrinsic"].uncheck_select_points_button()

    def show_item(self, item_type, name):
        if item_type == "tracker":
            self.frame_widget.show_tracker(name)
            self.docks["DataPlot"].show_tracker(name)
        elif item_type == "angle":
            self.frame_widget.show_angle(name)
            self.docks["DataPlot"].show_angle(name)
        elif item_type == "distance":
            self.frame_widget.show_distance(name)
            self.docks["DataPlot"].show_distance(name)

    def hide_item(self, item_type, name):
        if item_type == "tracker":
            self.frame_widget.hide_tracker(name)
            self.docks["DataPlot"].hide_tracker(name)
        elif item_type == "angle":
            self.frame_widget.hide_angle(name)
            self.docks["DataPlot"].hide_angle(name)
        elif item_type == "distance":
            self.frame_widget.hide_distance(name)
            self.docks["DataPlot"].hide_distance(name)

    def remove_item(self, item_type, name):
        self.play_video(False)
        while not self.stream_queue.empty():
            sleep(0.1)

        if item_type == "tracker":
            self.frame_widget.remove_tracker(name)
        elif item_type == "angle":
            self.frame_widget.remove_angle(name)
        elif item_type == "distance":
            self.frame_widget.remove_distance(name)

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
        self.play_video(False)
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
        self.tracking_worker.remove_angle(name)
        self.docks["Items"].remove_row(name, "angle")
        self.docks["DataPlot"].remove_angle(name)

    def move_angle(self, name, start1, end1, start2, end2, color):
        self.tracking_worker.add_angle(name, start1, end1, start2, end2)

    def distance_suggested(self, start, end):
        dialog = DistanceDialog(default_color=next(tab10_rgb_cycle))
        dialog.exec()
        if dialog.result():
            name, color = dialog.get_inputs()
            self.frame_widget.remove_temp_distance()

            self.frame_widget.add_distance(
                name,
                start,
                end,
                color,
            )

        else:
            self.frame_widget.remove_temp_distance()

    def add_distance(self, name, start, end, color):
        self.tracking_worker.add_distance(name, start, end)
        self.docks["Items"].add_row(name, color, "distance")
        self.docks["DataPlot"].add_distance(name, color)

    def remove_distance(self, name):
        self.tracking_worker.remove_distance(name)
        self.docks["Items"].remove_row(name, "distance")
        self.docks["DataPlot"].remove_distance(name)

    def move_distance(self, name, start, end, color):
        self.tracking_worker.add_distance(name, start, end)

    def save_data(self):
        if self.frame_widget.trackers["name"] and self.stream_worker is not None:
            video_path = self.stream_worker.path
            save_path = video_path.parent / f"{video_path.stem}.json"
            save_tracking_data(
                save_path,
                {
                    k: v
                    for k, v in self.frame_widget.trackers.items()
                    if k in ["name", "offset", "color", "tracker_type"]
                },
                {
                    "angle": {
                        k: v
                        for k, v in self.frame_widget.angles.items()
                        if k in ["name", "start1", "end1", "start2", "end2", "color"]
                    },
                    "distance": {
                        k: v
                        for k, v in self.frame_widget.distances.items()
                        if k in ["name", "start", "end", "color"]
                    },
                },
                self.tracking_worker.tracking_data,
                self.tracking_worker.frame_no,
                self.docks["Extrinsic"].scaling,
            )

    def load_data(self, path):
        (
            tracker_properties,
            analysis_properties,
            tracking_data,
            current_frame,
        ) = load_tracking_data(path)

        # move frame if current frame has no data
        first_tracker = next(iter(tracking_data.values()))
        if np.isnan(first_tracker["time"][current_frame - 1]):
            current_frame = np.argwhere(~np.isnan(first_tracker["time"])).max() - 1

        self.media_controls.seek_bar.setValue(current_frame)
        self.tracking_worker.set_tracking_data(tracking_data)
        for name, offset, color, tracker_type in zip(
            tracker_properties["name"],
            tracker_properties["offset"],
            tracker_properties["color"],
            tracker_properties["tracker_type"],
        ):
            bbox = tracking_data[name]["bbox"][current_frame - 1]
            if np.isnan(bbox).any():
                i = np.argwhere(
                    ~np.isnan(tracking_data[name]["bbox"]).any(axis=1)
                ).min()
                bbox = tracking_data[name]["bbox"][i]

            self.frame_widget.add_tracker(
                name,
                bbox[:2].astype(np.int_),
                bbox[2:].astype(np.int_),
                offset,
                color,
                tracker_type,
            )

        angle_props = analysis_properties["angle"]
        for args in zip(
            angle_props["name"],
            angle_props["start1"],
            angle_props["end1"],
            angle_props["start2"],
            angle_props["end2"],
            angle_props["color"],
        ):
            self.frame_widget.add_angle(*args)

        distance_props = analysis_properties["distance"]
        for args in zip(
            distance_props["name"],
            distance_props["start"],
            distance_props["end"],
            distance_props["color"],
        ):
            self.frame_widget.add_distance(*args)

    def load_markers(self, path):
        if self.stream_worker is not None:
            try:
                (
                    tracker_properties,
                    analysis_properties,
                    tracking_data,
                    _,
                ) = load_tracking_data(path)

                for name, offset, color, tracker_type in zip(
                    tracker_properties["name"],
                    tracker_properties["offset"],
                    tracker_properties["color"],
                    tracker_properties["tracker_type"],
                ):
                    bbox = tracking_data[name]["bbox"][1]
                    if np.isnan(bbox).any():
                        i = np.argwhere(
                            ~np.isnan(tracking_data[name]["bbox"]).any(axis=1)
                        ).min()
                        bbox = tracking_data[name]["bbox"][i]

                    self.frame_widget.add_tracker(
                        name,
                        bbox[:2].astype(np.int_),
                        bbox[2:].astype(np.int_),
                        offset,
                        color,
                        tracker_type,
                    )
                angle_props = analysis_properties["angle"]
                for args in zip(
                    angle_props["name"],
                    angle_props["start1"],
                    angle_props["end1"],
                    angle_props["start2"],
                    angle_props["end2"],
                    angle_props["color"],
                ):
                    self.frame_widget.add_angle(*args)

                distance_props = analysis_properties["distance"]
                for args in zip(
                    distance_props["name"],
                    distance_props["start"],
                    distance_props["end"],
                    distance_props["color"],
                ):
                    self.frame_widget.add_distance(*args)
            except Exception as e:
                self.error_dialog(f"Failed to load markers.\n{e}")

    def export_data(self, path):
        try:
            export_csv(
                path,
                self.tracking_worker.tracking_data,
                self.tracking_worker.analysis_data,
                self.docks["Extrinsic"].scaling,
            )
        except Exception as e:
            self.error_dialog(e)

    def autosave_toggled(self, autosave):
        if autosave:
            self.save_data()
            self.autosave_timer.start(30000)  # every 30 s
        else:
            self.autosave_timer.stop()

    def start_select_points(self):
        if self.stream_worker is None:
            return
        self.edit_mode_changed("select_warp_points")

    def finish_select_points(self):
        if self.stream_worker is None:
            return
        self.frame_widget.emit_new_warp_points()
        self.set_normal_mode()

    def warp_points_selected(self, img_points, obj_points):
        self.docks["Extrinsic"].uncheck_select_points_button()
        path = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save points", "warp_points", "JSON (*.json)"
        )
        if path[1] == "JSON (*.json)":
            save_path = Path(path[0]).resolve()
            save_warp_points(img_points, obj_points, save_path)
            self.docks["Extrinsic"].extrinsic_cal_file_edit.setText(
                str(save_path.resolve())
            )

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
    def log_new_session():
        banner = "-" * 20 + " New Session " + "-" * 20
        logging.info("")
        logging.info("=" * len(banner))
        logging.info(banner)
        logging.info("=" * len(banner))


def main():
    setup_logger()

    app = QtWidgets.QApplication([])
    win = MainWidget()
    win.show()

    app.exec()


if __name__ == "__main__":
    main()
