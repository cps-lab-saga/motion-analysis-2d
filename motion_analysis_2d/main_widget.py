import logging
from queue import Queue
from time import sleep

import numpy as np

from motion_analysis_2d.controls import EditControls, MediaControls, MenuBar
from motion_analysis_2d.defs import (
    QtCore,
    QtGui,
    QtWidgets,
    settings_file,
    resource_dir,
    shortcuts_file,
    visual_preferences_file,
)
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
)
from motion_analysis_2d.preferences_pane import (
    load_preferences,
    shortcut_keys,
    visual_preferences,
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

        self.shortcut_keys = self.load_shortcuts()
        self.visual_preferences = self.load_visual_preferences()

        self.splashscreen.set_progress(10)

        self.main_widget = QtWidgets.QWidget(parent=self)
        self.main_layout = QtWidgets.QGridLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.frame_widget = FrameWidget(self.visual_preferences, self)
        self.frame_widget.new_item_suggested.connect(self.add_item)
        self.frame_widget.edit_item_suggested.connect(self.edit_item_props)
        self.frame_widget.item_moved.connect(self.move_item)
        self.frame_widget.item_removal_suggested.connect(self.remove_item)
        self.frame_widget.marker_file_dropped.connect(self.load_markers)
        self.frame_widget.image_file_dropped.connect(self.load_image)
        self.frame_widget.new_settings_suggested.connect(self.new_settings_suggested)
        self.frame_widget.new_settings_ended.connect(self.new_settings_ended)
        self.main_layout.addWidget(self.frame_widget, 0, 0)

        self.splashscreen.set_progress(30)

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
        self.docks["Files"].batch_button_toggled.connect(self.batch_toggled)
        self.docks["Intrinsic"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Extrinsic"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Extrinsic"].add_perspective_started.connect(
            self.start_add_perspective
        )
        self.docks["Extrinsic"].add_perspective_finished.connect(
            self.new_settings_ended
        )
        self.docks["Extrinsic"].add_perspective_button.setDisabled(True)
        self.docks["Orient"].settings_updated.connect(self.frame_shape_changed)
        self.docks["Items"].show_item.connect(self.show_item)
        self.docks["Items"].hide_item.connect(self.hide_item)
        self.docks["Items"].edit_item_suggested.connect(self.edit_item_suggested)
        self.docks["Items"].remove_item_suggested.connect(self.remove_item)
        self.docks["Save"].autosave_toggled.connect(self.autosave_toggled)
        self.docks["Save"].export_clicked.connect(self.export_data)
        self.docks["DataPlot"].frame_line_dragged.connect(
            self.media_controls.seek_bar.setValue
        )

        self.splashscreen.set_progress(50)

        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.open_video_file.connect(self.docks["Files"].add_files)
        self.menu_bar.open_video_folder.connect(self.docks["Files"].add_files)
        self.menu_bar.update_shortcuts.connect(self.update_shortcuts)
        self.menu_bar.update_visual_preferences.connect(self.update_visual_preferences)

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

        self.splashscreen.set_progress(90)

        # load settings from previous session
        self.settings_file = settings_file("ma2d_ui_restore.ini")
        if self.settings_file.is_file():
            settings = QtCore.QSettings(
                str(self.settings_file), QtCore.QSettings.IniFormat
            )
            self.gui_restore(settings)

        self.splashscreen.finish(self)

    def load_shortcuts(self):
        shortcuts_f = shortcuts_file()
        if shortcuts_f.is_file():
            try:
                shortcuts = load_preferences(shortcuts_f)
            except Exception as e:
                self.error_dialog(f"{shortcuts_f} is corrupted!\n{str(e)}")
                shortcuts = shortcut_keys.copy()
        else:
            shortcuts = shortcut_keys.copy()
        return {QtCore.Qt.Key[v]: k for k, v in shortcuts.items()}

    def update_shortcuts(self):
        self.shortcut_keys = self.load_shortcuts()

    def load_visual_preferences(self):
        visual_preferences_f = visual_preferences_file()
        if visual_preferences_f.is_file():
            try:
                preferences = load_preferences(visual_preferences_f)
            except Exception as e:
                self.error_dialog(f"{visual_preferences_f} is corrupted!\n{str(e)}")
                preferences = visual_preferences.copy()
        else:
            preferences = visual_preferences.copy()
        return preferences

    def update_visual_preferences(self):
        self.visual_preferences = self.load_visual_preferences()
        self.frame_widget.update_visual_preferences(self.visual_preferences)

    def video_file_changed(self, path):
        self.play_video(False)

        self.camera_frame_update_timer.stop()
        self.edit_controls.set_normal_mode()
        self.edit_controls.setDisabled(True)
        self.media_controls.set_seek_bar_value(0)
        self.media_controls.setDisabled(True)
        self.docks["Extrinsic"].add_perspective_button.setDisabled(True)
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
            self.docks["Extrinsic"].add_perspective_button.setDisabled(False)
            self.frame_widget.update_scaling(self.docks["Extrinsic"].scaling)
            self.docks["DataPlot"].set_frame_line_draggable(True)
            self.camera_frame_update_timer.start(30)

            while self.tracking_worker.no_of_frames == 0:
                QtCore.QCoreApplication.processEvents()
                sleep(0.2)

            track_file = path.parent / (path.stem + ".json")
            if track_file.is_file():
                logging.info(f"Loaded data file {track_file.name}")
                self.load_data(track_file)

            self.frame_widget.auto_range()
            if self.docks["Files"].batch_button.isChecked():
                self.play_video(True)

    def close_video(self):
        if self.streaming:
            self.stream_worker.set_stop()
            while self.streaming:  # wait till capture is closed
                sleep(0.1)
                QtCore.QCoreApplication.processEvents()

    def next_video(self):
        logging.debug("Go to next video")
        self.docks["Files"].next_file()

    def previous_video(self):
        logging.debug("Go to previous video")
        self.docks["Files"].previous_file()

    def reached_end(self):
        if self.docks["Files"].batch_button.isChecked():
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

    def toggle_auto_save(self):
        self.docks["Save"].autosave_button.toggle()

    def click_export(self):
        self.docks["Save"].export_button.click()

    def set_autosave(self, autosave: bool):
        self.docks["Save"].autosave_button.setChecked(autosave)

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
                self.frame_widget.set_item_data(
                    "tracker",
                    name,
                    (
                        i,
                        tracking_data["bbox"],
                        tracking_data["target"],
                    ),
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
            self.play_video(False)
            while not self.stream_queue.empty():
                sleep(0.1)

            self.frame_widget.update_scaling(self.docks["Extrinsic"].scaling)
            frame_no, timestamp, frame = self.stream_worker.read_current_frame()
            self.frame_widget.frame_shape_changed((frame, frame_no, timestamp / 1000))
        else:
            self.load_image()

    def seek_bar_moved(self, frame_no):
        if self.stream_worker is not None:
            self.stream_worker.move_frame_to(frame_no)
            self.tracking_worker.reset_trackers()

    def edit_mode_changed(self, mode):
        self.play_video(False)
        while not self.stream_queue.empty():
            sleep(0.1)

        self.frame_widget.set_mouse_mode(mode)

    def set_normal_mode(self):
        self.edit_controls.set_normal_mode()
        self.docks["Extrinsic"].uncheck_select_points_button()

    def show_item(self, item_type, name):
        self.frame_widget.show_item(item_type, name)
        self.docks["DataPlot"].show_item(item_type, name)

    def hide_item(self, item_type, name):
        self.frame_widget.hide_item(item_type, name)
        self.docks["DataPlot"].hide_item(item_type, name)

    def edit_item_suggested(self, item_type, name):
        self.frame_widget.start_edit_item(item_type, name)

    def edit_item_props(self, item_type, name, props):
        self.play_video(False)
        while not self.stream_queue.empty():
            sleep(0.1)

        self.frame_widget.edit_item_props(item_type, name, props)
        self.docks["Items"].edit_row(item_type, name, props)
        self.docks["DataPlot"].edit_item(item_type, name, props)
        self.tracking_worker.edit_item(item_type, name, props)

    def remove_item(self, item_type, name):
        self.play_video(False)
        while not self.stream_queue.empty():
            sleep(0.1)

        self.tracking_worker.remove_item(item_type, name)
        self.frame_widget.remove_item(item_type, name)
        self.docks["Items"].remove_row(item_type, name)
        self.docks["DataPlot"].remove_item(item_type, name)

    def add_item(self, item_type, item_props):
        self.tracking_worker.add_item(item_type, item_props)
        self.frame_widget.add_item(item_type, item_props)
        self.docks["Items"].add_row(item_type, item_props)
        self.docks["DataPlot"].add_item(item_type, item_props)
        self.set_normal_mode()

    def tracking_failed(self, name, frame_no):
        self.play_video(False)
        if self.docks["Files"].batch_button.isChecked():
            msg = f"Tracking failed for {name} at frame {frame_no} in {self.stream_worker.path.name}!"
            self.info_dialog(
                "Tracking Failure!",
                msg,
            )
            logging.info(msg)
            self.stream_worker.move_frame_to(frame_no - 2, track=False)
            self.next_video()
        else:
            self.error_dialog(f"Tracking failed for {name} at frame {frame_no}!")
            self.stream_worker.move_frame_to(frame_no - 2, track=False)

    def add_tracker_failed(self, name, error):
        self.error_dialog(f"Could not initialise tracker for ({name})!\n{error}")
        self.frame_widget.remove_item("tracker", name)
        self.docks["Items"].remove_row("tracker", name)
        self.docks["DataPlot"].remove_item("tracker", name)

    def reset_trackers(self):
        self.tracking_worker.reset_trackers()

    def move_item(self, item_type, item_props):
        self.tracking_worker.add_item(item_type, item_props)

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
                (
                    self.docks["Intrinsic"].intrinsic_cal_file_edit.text()
                    if self.docks["Intrinsic"].cal_ok
                    else None
                ),
                (
                    self.docks["Extrinsic"].extrinsic_cal_file_edit.text()
                    if self.docks["Extrinsic"].cal_ok
                    else None
                ),
                self.docks["Orient"].rotation,
                self.docks["Orient"].flip,
            )

    def load_data(self, path):
        (
            tracker_properties,
            analysis_properties,
            tracking_data,
            current_frame,
            intrinsic,
            extrinsic,
            rotation,
            flip,
        ) = load_tracking_data(path)

        self.docks["Orient"].restore_rotation(rotation)
        self.docks["Orient"].restore_flip(flip)

        if intrinsic is not None:
            relative, absolute = intrinsic
            if relative is not None and (path / relative).is_file():
                self.docks["Intrinsic"].intrinsic_cal_file_edit.setText(
                    str((path / relative).resolve())
                )
            else:
                self.docks["Intrinsic"].intrinsic_cal_file_edit.setText(absolute)

        if extrinsic is not None:
            relative, absolute = extrinsic
            if relative is not None and (path / relative).is_file():
                self.docks["Extrinsic"].extrinsic_cal_file_edit.setText(
                    str((path / relative).resolve())
                )
            else:
                self.docks["Extrinsic"].extrinsic_cal_file_edit.setText(absolute)

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

            self.add_item(
                "tracker",
                {
                    "name": name,
                    "bbox_pos": bbox[:2].astype(np.int_),
                    "bbox_size": bbox[2:].astype(np.int_),
                    "offset": offset,
                    "color": color,
                    "tracker_type": tracker_type,
                },
            )

        angle_props = analysis_properties["angle"]
        for i in range(len(angle_props["name"])):
            self.add_item(
                "angle",
                {k: v[i] for k, v in angle_props.items()},
            )

        distance_props = analysis_properties["distance"]
        for i in range(len(distance_props["name"])):
            self.add_item(
                "distance",
                {k: v[i] for k, v in distance_props.items()},
            )

    def load_markers(self, path):
        if self.stream_worker is not None:
            self.docks["Items"].clear()
            self.docks["DataPlot"].clear()
            self.frame_widget.clear()
            self.tracking_worker.clear_data()
            try:
                (
                    tracker_properties,
                    analysis_properties,
                    tracking_data,
                    current_frame,
                    intrinsic,
                    extrinsic,
                    rotation,
                    flip,
                ) = load_tracking_data(path)

                self.docks["Orient"].restore_rotation(rotation)
                self.docks["Orient"].restore_flip(flip)

                if intrinsic is not None:
                    relative, absolute = intrinsic
                    if relative is not None and (path / relative).is_file():
                        self.docks["Intrinsic"].intrinsic_cal_file_edit.setText(
                            str((path / relative).resolve())
                        )
                    else:
                        self.docks["Intrinsic"].intrinsic_cal_file_edit.setText(
                            absolute
                        )

                if extrinsic is not None:
                    relative, absolute = extrinsic
                    if relative is not None and (path / relative).is_file():
                        self.docks["Extrinsic"].extrinsic_cal_file_edit.setText(
                            str((path / relative).resolve())
                        )
                    else:
                        self.docks["Extrinsic"].extrinsic_cal_file_edit.setText(
                            absolute
                        )

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

                    self.add_item(
                        "tracker",
                        {
                            "name": name,
                            "bbox_pos": bbox[:2].astype(np.int_),
                            "bbox_size": bbox[2:].astype(np.int_),
                            "offset": offset,
                            "color": color,
                            "tracker_type": tracker_type,
                        },
                    )
                angle_props = analysis_properties["angle"]
                for i in range(len(angle_props["name"])):
                    self.add_item(
                        "angle",
                        {k: v[i] for k, v in angle_props.items()},
                    )

                distance_props = analysis_properties["distance"]
                for i in range(len(distance_props["name"])):
                    self.add_item(
                        "distance",
                        {k: v[i] for k, v in distance_props.items()},
                    )

            except Exception as e:
                self.error_dialog(f"Failed to load markers.\n{e}")

    def load_image(self, frame=None):
        self.play_video(False)

        if frame is None:
            frame = self.frame_widget.raw_img
            if frame is None:
                return
        else:
            self.docks["Extrinsic"].add_perspective_button.setDisabled(False)

        frame = self.docks["Intrinsic"].undistort_map(frame)
        frame = self.docks["Orient"].orient_img(frame)
        frame = self.docks["Extrinsic"].change_perspective(frame)
        self.frame_widget.set_image(frame)
        self.frame_widget.auto_range()

    def export_data(self, path):
        if self.frame_widget.trackers["name"] and self.stream_worker is not None:
            try:
                export_csv(
                    path,
                    self.tracking_worker.tracking_data,
                    self.tracking_worker.analysis_data,
                    self.docks["Extrinsic"].scaling,
                )
            except Exception as e:
                self.error_dialog(str(e))
        else:
            self.error_dialog("No data available for export!")

    def autosave_toggled(self, autosave):
        if autosave:
            self.save_data()
            self.autosave_timer.start(30000)  # every 30 s
        else:
            self.autosave_timer.stop()

    def start_add_perspective(self):
        if self.stream_worker is None and self.frame_widget.raw_img is None:
            return
        self.edit_mode_changed("set_perspective")

    def new_settings_ended(self):
        if self.stream_worker is None and self.frame_widget.raw_img is None:
            return
        self.set_normal_mode()

    def new_settings_suggested(
        self,
        item_type,
        props,
    ):
        if item_type == "set_perspective":
            self.docks["Extrinsic"].save_points(
                props["img_points"], props["obj_points"], props["output_size"]
            )
        self.set_normal_mode()

    def batch_toggled(self, checked):
        if checked:
            self.set_autosave(True)

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

    def info_dialog(self, title, msg):
        message_box = QtWidgets.QMessageBox(self)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        message_box.setText(msg)
        message_box.setWindowTitle(title)
        message_box.show()

    def error_dialog(self, error):
        QtWidgets.QMessageBox.critical(self, "Error", error)

    def keyPressEvent(self, evt):
        if cmd := self.shortcut_keys.get(evt.key()):
            getattr(self, cmd)()

    @staticmethod
    def log_new_session():
        banner = "-" * 20 + " New Session " + "-" * 20
        logging.info(banner)


def main():
    setup_logger(logging.INFO)

    app = QtWidgets.QApplication([])
    win = MainWidget()
    win.show()

    app.exec()


if __name__ == "__main__":
    main()
