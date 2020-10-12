import glob
import re
import json
import os
import codecs
import shutil
import cv2
from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QAbstractItemView

from .id_dialog import IDDialog
from .point import Point
from .image_widget import ImageWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main_window.ui", self)

        self.img_files = []  # List of absolute paths to all image files
        self.img_file_idx = None  # Current selected image file index
        self.img_json_file = ''  # Current selected image JSON file absolute path
        self.img_json = {}  # Current selected image JSON data

        self.img_height = 0  # Current selected image height
        self.img_width = 0  # Current selected image width
        self.img_bboxes = []  # Current selected image bboxes
        self.img_ids = []  # Current selected image bbox IDs
        self.img_bbox_idx = None  # Current selected image - selected box

        self.color_change = []
        self.init_widgets()

    def init_widgets(self):
        """Initialize image widget and connections."""
        self.imgWidget = ImageWidget(self, objectName="img")
        self.mainLayout.insertWidget(0, self.imgWidget)

        # Make list items non-editable
        self.fileList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.idList.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.loadAction.triggered.connect(self.load_action)
        self.saveAction.triggered.connect(self.save_action)
        self.deleteAction.triggered.connect(self.delete_action)
        self.newBoxAction.triggered.connect(self.new_box_action)
        self.entireImageAction.triggered.connect(self.entire_image_action)
        self.prevPageButton.clicked.connect(self.prev_button_action)
        self.nextPageButton.clicked.connect(self.next_button_action)
        self.idDialogButton.clicked.connect(self.id_dialog_button_action)
        self.currentPageEdit.returnPressed.connect(self.current_page_action)
        self.fileList.selectionChanged = self.file_selection_changed
        self.idList.selectionChanged = self.id_selection_changed

    def load_action(self):
        """Open file dialog and get directory of images."""
        dir_name = QFileDialog.getExistingDirectory(self)
        self.img_files = glob.glob(f"{dir_name}/*.jpg")
        self.img_files.extend(glob.glob(f"{dir_name}/*.png"))

        def key(string):
            key_list = []
            for c in re.split('([0-9]+)', string):
                if string.isdigit():
                    key_list.append(int(string))
                else:
                    key_list.append(string.lower())

            return key_list

        self.img_files = sorted(self.img_files, key=key)
        self.img_file_idx = 0

        self.process_image()
        self.update_file_list_ui()
        self.update_ui()

    def process_image(self):
        """Load json data for current file."""
        dir_name = os.path.dirname(self.img_files[self.img_file_idx])
        file_root = os.path.splitext(os.path.basename(self.img_files[self.img_file_idx]))[0]
        self.img_json_file = os.path.join(dir_name, f"{file_root}.json")

        if not os.path.exists(self.img_json_file):
            cv2_img = cv2.imread(self.img_files[self.img_file_idx])
            cv2_img_width = cv2_img.shape[1]
            cv2_img_height = cv2_img.shape[0]
            img_size = os.path.getsize(self.img_files[self.img_file_idx])

            self.img_json = {
                "dataset_info": {
                    "description": ".",
                    "dataset_version": "1.0",
                    "dateset_created": "",
                    "attributes": {
                        "image_augmented": "",
                        "answer_refined": ""
                    },
                    "dataset_created": ""
                },
                "image_info": {
                    "image_name": file_root,
                    "attributes": {
                        "color": 3,
                        "image_size": img_size,
                        "image_width": cv2_img_width,
                        "image_height": cv2_img_height,
                        "image_path": self.img_files[self.img_file_idx]
                    }
                },
                "object_info": {
                    "face": {
                        "algorithm": {
                            "face_detect_algorithm": "",
                            "face_recog_algorithm": "",
                            "face_age_gender_algorithm": "",
                            "face_detect_model": "",
                            "face_recog_model": "",
                            "face_age_gender_model": ""
                        },
                        "result": {
                            "bboxes": [],
                            "embeddings": [],
                            "ids": [],
                            "ages": [],
                            "genders": []
                        }
                    },
                    "face_detect_algorithm": "",
                    "face_recog_algorithm": "",
                    "face_detect_model": "",
                    "face_recog_model": "",
                }
            }
            with open(self.img_json_file, 'w', encoding='utf-8') as json_file:
                json.dump(self.img_json, json_file, ensure_ascii=False, indent=4)

        else:
            self.img_json = json.load(codecs.open(self.img_json_file, 'r', 'utf-8-sig'))

        self.img_ids = self.img_json['object_info']['face']['result']['ids']
        self.img_width = self.img_json['image_info']['attributes']['image_width']
        self.img_height = self.img_json['image_info']['attributes']['image_height']

        # Turn JSON list into list of Points
        self.img_bboxes = list(map(lambda a: [
            Point(self.img_width * a[0], self.img_height * a[1]),
            Point(self.img_width * a[2], self.img_height * a[1]),
            Point(self.img_width * a[2], self.img_height * a[3]),
            Point(self.img_width * a[0], self.img_height * a[3])
        ], self.img_json['object_info']['face']['result']['bboxes']))

        self.color_change = len(self.img_bboxes) * [False]

        self.img_bbox_idx = 0
        self.update_id_list_ui()

    def update_ui(self):
        """Update all ui elements except lists."""
        if not self.img_files:
            return

        self.statusLabel.clear()

        # Update image
        pix_map_image = QtGui.QPixmap(self.img_files[self.img_file_idx])
        self.imgWidget.setPixmap(pix_map_image)
        self.imgWidget.setScaledContents(True)

        # Update page selection
        self.currentPageEdit.setText(str(self.img_file_idx + 1))
        self.currentPageEdit.setValidator(
            QtGui.QIntValidator(1, len(self.img_files), self))
        self.totalPageLabel.setText(f"/ {len(self.img_files)}")

        # Update list selections
        self.fileList.setCurrentIndex(
            self.fileList.model().createIndex(self.img_file_idx if self.img_file_idx else 0, 0))

        self.idList.setCurrentIndex(
            self.idList.model().createIndex(self.img_bbox_idx if self.img_bbox_idx else 0, 0))

    def update_file_list_ui(self):
        """Update model for file list."""
        model = QtGui.QStandardItemModel()
        for img_file in self.img_files:
            model.appendRow(QtGui.QStandardItem(os.path.basename(img_file)))

        self.fileList.setModel(model)

    def update_id_list_ui(self):
        """Update model for text list."""
        model = QtGui.QStandardItemModel()
        for name in self.img_ids:
            model.appendRow(QtGui.QStandardItem(name))

        self.idList.setModel(model)

    def prev_button_action(self):
        """Go to previous image, do nothing if already at beginning."""
        if self.img_file_idx > 0:
            self.save_action()
            self.img_file_idx -= 1
            self.process_image()
            self.update_ui()

    def next_button_action(self):
        """Go to next image, do nothing if already at end."""
        if self.img_file_idx < len(self.img_files) - 1:
            self.save_action()
            self.img_file_idx += 1
            self.process_image()
            self.update_ui()

    def current_page_action(self):
        """Go to specific image entered into page selection."""
        if int(self.currentPageEdit.text()) - 1 != self.img_file_idx:
            self.img_file_idx = int(self.currentPageEdit.text()) - 1
            self.process_image()
            self.update_ui()

    def id_dialog_button_action(self):
        try:
            dialog = IDDialog(self)
            dialog.exec_()
        except (TypeError, IndexError):
            self.statusLabel.setText("No Box available")

    def save_action(self):
        """Save data back to json file."""
        try:
            # check if the input can be converted to int
            self.update_id_list_ui()

            self.img_json['dataset_info']['attributes']['answer_refined'] = True

            self.img_json['object_info']['face']['result']['ids'] = self.img_ids

            # Turn list of Points back into JSON list
            self.img_json['object_info']['face']['result']['bboxes'] = []
            for idx1, bbox in enumerate(self.img_bboxes):
                self.img_json['object_info']['face']['result']['bboxes'].append([0, 0, 0, 0])
                for idx2, p in enumerate(bbox):
                    if idx2 == 0:
                        self.img_json['object_info']['face']['result']['bboxes'][idx1][0] = \
                            p.x / self.img_width
                        self.img_json['object_info']['face']['result']['bboxes'][idx1][1] = \
                            p.y / self.img_height

                    if idx2 == 2:
                        self.img_json['object_info']['face']['result']['bboxes'][idx1][2] = \
                            p.x / self.img_width
                        self.img_json['object_info']['face']['result']['bboxes'][idx1][3] = \
                            p.y / self.img_height

            original_file = f"{self.img_json_file}~"
            shutil.copy2(self.img_json_file, original_file)

            with open(self.img_json_file, 'w', encoding='utf-8') as json_file:
                json.dump(self.img_json, json_file, ensure_ascii=False, indent=4)

            self.statusLabel.setText("Saved!")
        except IndexError:
            self.statusLabel.setText("Invalid Text")

    def delete_action(self):
        """Delete current selected bbox."""
        del self.img_bboxes[self.img_bbox_idx]
        del self.img_ids[self.img_bbox_idx]

        if self.img_bbox_idx == len(self.img_bboxes):
            self.img_bbox_idx -= 1

        self.update_id_list_ui()
        self.update_ui()

    def new_box_action(self):
        """Add a new box with default size and text."""
        self.img_bboxes.append([Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)])
        self.img_ids.append("--추가해주세요--")

        self.update_id_list_ui()
        self.update_ui()

    def entire_image_action(self):
        """Change current bbox to cover entire image."""
        try:
            self.img_bboxes[self.img_bbox_idx] = [
                Point(0, 0),
                Point(self.img_width, 0),
                Point(self.img_width, self.img_height),
                Point(0, self.img_height)
            ]
            self.update_ui()
        except IndexError:
            self.statusLabel.setText("Box unavailable")

    def file_selection_changed(self, selected, _):
        """Get new file selection and update UI."""
        indexes = selected.indexes()
        if len(indexes) <= 0:
            return

        self.save_action()
        self.img_file_idx = indexes[0].row()

        self.process_image()
        self.update_ui()

    def id_selection_changed(self, selected, _):
        """Get new id selection and update UI."""
        indexes = selected.indexes()
        if len(indexes) <= 0:
            return
        self.img_bbox_idx = indexes[0].row()
        if self.img_bboxes:
            self.color_change = len(self.img_bboxes) * [0]
            # Not in list
            with open('id_cand_list.txt', 'r') as file:
                items = file.read().splitlines()
            for i, name in enumerate(self.img_ids):
                if name not in items:
                    self.color_change[i] = 2

            self.color_change[self.img_bbox_idx] = 1

        self.update_ui()
