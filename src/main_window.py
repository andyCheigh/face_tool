import glob
import re
import json
import ntpath
import os
import codecs
import shutil
import cv2
from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QFileDialog, QMainWindow

from .point import Point
from .image_widget import ImageWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main_window.ui", self)

        self.dir_name = ''

        self.img_files = []
        self.img_file_idx = None
        self.img_id_idx = None
        self.img_height = 0
        self.img_width = 0

        self.img_file_name = ''
        self.file_name = ''

        self.box_info = {}
        self.bboxes = []
        self.img_ids = []
        self.color_change = []
        self.init_widgets()

    def init_widgets(self):
        """Initialize image widget and connections."""
        self.imgWidget = ImageWidget(self, objectName="img")
        self.mainLayout.insertWidget(0, self.imgWidget)

        self.loadAction.triggered.connect(self.load_action)
        self.saveAction.triggered.connect(self.save_action)
        self.deleteAction.triggered.connect(self.delete_action)
        self.newBoxAction.triggered.connect(self.new_box_action)
        self.entireImageAction.triggered.connect(self.entire_image_action)
        self.prevPageButton.clicked.connect(self.prev_button_action)
        self.nextPageButton.clicked.connect(self.next_button_action)
        self.currentPageEdit.returnPressed.connect(self.current_page_action)
        self.fileList.selectionChanged = self.file_selection_changed
        self.idList.selectionChanged = self.id_selection_changed

    def load_action(self):
        """Open file dialog and get directory of images."""
        self.dir_name = QFileDialog.getExistingDirectory(self)
        self.img_files = glob.glob(self.dir_name + '/*.jpg')
        self.img_files.extend(glob.glob(self.dir_name + '/*.png'))

        self.img_files = MainWindow.sort_string(self.img_files)
        self.img_file_idx = 0

        self.process_image()
        self.update_file_list_ui()
        self.update_ui()

    @staticmethod
    def sort_string(strings):
        """Sort images by filename."""
        def _key(string):
            if string.isdigit():
                return int(string)
            return string.lower()

        def _alpha_key(string):
            key = []
            for c in re.split('([0-9]+)', string):
                key.append(_key(c))
            return key

        return sorted(strings, key=_alpha_key)

    def process_image(self):
        """Load json data for current file."""
        self.img_file_name = os.path.splitext(self.img_files[self.img_file_idx])[0]
        base_name = ntpath.basename(self.img_files[self.img_file_idx])
        self.file_name = os.path.splitext(base_name)[0]

        if not os.path.exists(self.dir_name + "/" + self.file_name + '.json'):

            cv2_img = cv2.imread(self.img_files[self.img_file_idx])
            cv2_img_width = cv2_img.shape[1]
            cv2_img_height = cv2_img.shape[0]
            img_size = os.path.getsize(self.img_files[self.img_file_idx])

            self.box_info = {
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
                    "image_name": base_name,
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
            with open(self.dir_name + "/" + self.file_name + '.json',
                      'w', encoding='utf-8') as json_file:
                json.dump(self.box_info, json_file, ensure_ascii=False, indent=4)

        else:
            self.box_info = json.load(codecs.open(self.dir_name + "/" +
                                                  self.file_name + '.json', 'r', 'utf-8-sig'))

        self.img_ids = self.box_info['object_info']['face']['result']['ids']
        self.img_width = self.box_info['image_info']['attributes']['image_width']
        self.img_height = self.box_info['image_info']['attributes']['image_height']

        # Turn JSON list into list of Points
        self.bboxes = list(map(lambda a: [
            Point(self.img_width * a[0], self.img_height * a[1]),
            Point(self.img_width * a[0] + self.img_width * a[2], self.img_height * a[1]),
            Point(self.img_width * a[0] + self.img_width * a[2],
                  self.img_height * a[1] + self.img_height * a[3]),
            Point(self.img_width * a[0], self.img_height * a[1] + self.img_height * a[3])
        ], self.box_info['object_info']['face']['result']['bboxes']))

        self.color_change = len(self.bboxes) * [False]

        self.img_id_idx = 0
        self.update_id_combo_box_ui()
        self.update_text_list_ui()

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
            self.idList.model().createIndex(self.img_id_idx if self.img_id_idx else 0, 0))

        self.update_id_combo_box_ui()

    def update_file_list_ui(self):
        """Update model for file list."""
        model = QtGui.QStandardItemModel()
        for img_file in self.img_files:
            base_name = ntpath.basename(img_file)
            model.appendRow(QtGui.QStandardItem(base_name))
        self.fileList.setModel(model)

    def update_text_list_ui(self):
        """Update model for text list."""
        model = QtGui.QStandardItemModel()
        for name in self.img_ids:
            model.appendRow(QtGui.QStandardItem(name))
        self.idList.setModel(model)

    def update_id_combo_box_ui(self):
        """Update model for id list."""
        with open('id_cand_list.txt', 'r') as f:
            items = f.read().splitlines()

        if self.img_ids[self.img_id_idx] not in items:  # Add current id if not present in list
            items.insert(0, self.img_ids[self.img_id_idx])
            self.statusLabel.setText("Not in the list")

        self.idComboBox.setCurrentIndex(-1)
        self.idComboBox.clear()
        self.idComboBox.addItems(items)
        self.idComboBox.setCurrentIndex(items.index(self.img_ids[self.img_id_idx]))

    def prev_button_action(self):
        """Go to previous image, do nothing if already at beginning."""
        if self.img_file_idx > 0:
            self.img_file_idx -= 1
            self.process_image()
            self.update_ui()

    def next_button_action(self):
        """Go to next image, do nothing if already at end."""
        if self.img_file_idx < len(self.img_files) - 1:
            self.img_file_idx += 1
            self.process_image()
            self.update_ui()

    def current_page_action(self):
        """Go to specific image entered into page selection."""
        if int(self.currentPageEdit.text()) - 1 != self.img_file_idx:
            self.img_file_idx = int(self.currentPageEdit.text()) - 1
            self.process_image()
            self.update_ui()

    def save_action(self):
        """Save data back to json file."""
        try:
            # check if the input can be converted to int
            self.img_ids[self.img_id_idx] = self.idComboBox.currentText()
            self.update_text_list_ui()

            self.box_info['dataset_info']['attributes']['answer_refined'] = True

            self.box_info['object_info']['face']['result']['ids'] = self.img_ids

            # Turn list of Points back into JSON list
            self.box_info['object_info']['face']['result']['bboxes'] = []
            for idx1, bbox in enumerate(self.bboxes):
                self.box_info['object_info']['face']['result']['bboxes'].append([0, 0, 0, 0])
                for idx2, p in enumerate(bbox):
                    if idx2 == 0:
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][0] = p.x/self.img_width
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][1] = p.y/self.img_height

                    if idx2 == 1:
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][2] = \
                            p.x/self.img_width - \
                            self.box_info['object_info']['face']['result']['bboxes'][idx1][0]

                    if idx2 == 3:
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][3] = \
                            p.y/self.img_height - \
                            self.box_info['object_info']['face']['result']['bboxes'][idx1][1]

            original_file = self.dir_name + "/" + self.file_name + '.json~'
            shutil.copy2(self.dir_name + "/" + self.file_name + '.json', original_file)

            with open(self.dir_name + "/" + self.file_name + '.json', 'w', encoding='utf-8') as json_file:
                json.dump(self.box_info, json_file, ensure_ascii=False, indent=4)

            self.statusLabel.setText("Saved!")
        except IndexError:
            self.statusLabel.setText("Invalid Text")

    def delete_action(self):
        """Delete current selected bbox."""
        del self.bboxes[self.img_id_idx]
        del self.img_ids[self.img_id_idx]

        if self.img_id_idx == len(self.bboxes):
            self.img_id_idx -= 1
        self.update_text_list_ui()
        self.update_ui()

    def new_box_action(self):
        """Add a new box with default size and text."""
        self.bboxes.append([Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)])
        self.img_ids.append("--추가해주세요--")
        self.update_text_list_ui()
        self.update_ui()

    def entire_image_action(self):
        """Change current bbox to cover entire image."""
        try:
            self.bboxes[self.img_id_idx] = [
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

        self.img_file_idx = indexes[0].row()
        self.process_image()
        self.update_ui()

    def id_selection_changed(self, selected, _):
        """Get new id selection and update UI."""
        indexes = selected.indexes()
        if len(indexes) <= 0:
            return
        self.img_id_idx = indexes[0].row()
        if self.bboxes:
            self.color_change = len(self.bboxes) * [False]
            self.color_change[self.img_id_idx] = True
        self.update_ui()
