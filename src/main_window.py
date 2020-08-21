import glob
import re
import json
import ntpath
import os
from os import path
import cv2
import codecs

import shutil

from PyQt5 import QtGui, QtWidgets, uic

from . import Point
from .image_widget import ImageWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        form, _ = uic.loadUiType("idr_tool.ui")
        self.ui = form()
        self.ui.setupUi(self)

        self.dir_name = ''

        self.img_files = []
        self.img_file_id = None
        self.text_id = None
        self.img_height = 0
        self.img_width = 0

        self.img_file_name = ''
        self.file_name = ''

        self.box_info = {}
        self.bboxes = []
        self.img_text = []
        self.color_change = []
        self.init_widgets()

    def init_widgets(self):
        """Initialize image widget and connections."""
        self.ui.img = ImageWidget(self, objectName="img")
        self.ui.mainLayout.insertWidget(0, self.ui.img)

        self.ui.actionLoad.triggered.connect(self.load_action)
        self.ui.actionSave.triggered.connect(self.save_action)
        self.ui.actionDelete.triggered.connect(self.delete_action)
        self.ui.actionNewBox.triggered.connect(self.new_box_action)
        self.ui.actionEntireImage.triggered.connect(self.entire_image_action)
        self.ui.leftButton.clicked.connect(self.prev_button_action)
        self.ui.rightButton.clicked.connect(self.next_button_action)
        self.ui.currPage.returnPressed.connect(self.current_page_action)
        self.ui.fileList.selectionChanged = self.file_selection_changed
        self.ui.textList.selectionChanged = self.text_selection_changed

    def load_action(self):
        """Open file dialog and get directory of images."""
        self.dir_name = QtWidgets.QFileDialog.getExistingDirectory(self)
        self.img_files = glob.glob(self.dir_name + '/*.jpg')
        self.img_files.extend(glob.glob(self.dir_name + '/*.png'))

        self.img_files = MainWindow.sort_string(self.img_files)
        self.img_file_id = 0

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
        self.img_file_name, _ = path.splitext(self.img_files[self.img_file_id])
        base_name = ntpath.basename(self.img_files[self.img_file_id])
        self.file_name, _ = path.splitext(base_name)

        if not path.exists(self.dir_name + "/" + self.file_name + '.json'):

            cv2_img = cv2.imread(self.img_files[self.img_file_id])
            cv2_img_width = cv2_img.shape[1]
            cv2_img_height = cv2_img.shape[0]
            img_size = path.getsize(self.img_files[self.img_file_id])

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
                        "image_path": self.img_files[self.img_file_id]
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
            self.box_info = json.load(codecs.open(self.dir_name + "/" + self.file_name + '.json', 'r', 'utf-8-sig'))

        self.img_text = self.box_info['object_info']['face']['result']['ids']
        self.img_width = self.box_info['image_info']['attributes']['image_width']
        self.img_height = self.box_info['image_info']['attributes']['image_height']

        # Turn JSON list into list of Points
        self.bboxes = list(map(lambda a: [
            Point(self.img_width*a[0], self.img_height*a[1]),
            Point(self.img_width*a[0] + self.img_width*a[2], self.img_height*a[1]),
            Point(self.img_width*a[0] + self.img_width*a[2], self.img_height*a[1] + self.img_height*a[3]),
            Point(self.img_width*a[0], self.img_height * a[1] + self.img_height * a[3])
        ], self.box_info['object_info']['face']['result']['bboxes']))

        self.color_change = len(self.bboxes) * [False]

        self.text_id = 0
        self.ui.value.clear()
        self.update_text_list_ui()

    def update_ui(self):
        """Update all ui elements except lists."""
        if not self.img_files:
            return

        self.ui.save_alert.clear()

        # Update image
        pix_map_image = QtGui.QPixmap(self.img_files[self.img_file_id])
        self.ui.img.setPixmap(pix_map_image)
        self.ui.img.setScaledContents(True)

        # Update page selection
        self.ui.currPage.setText(str(self.img_file_id + 1))
        self.ui.currPage.setValidator(
            QtGui.QIntValidator(1, len(self.img_files), self))
        self.ui.numPage.setText(f"/ {len(self.img_files)}")

        # Update list selections
        self.ui.fileList.setCurrentIndex(
            self.ui.fileList.model().createIndex(self.img_file_id if self.img_file_id else 0, 0))

        self.ui.textList.setCurrentIndex(
            self.ui.textList.model().createIndex(self.text_id if self.text_id else 0, 0))

        # Update text
        if self.img_text:
            self.ui.value.setText(self.img_text[self.text_id])

    def update_file_list_ui(self):
        """Update model for file list."""
        model = QtGui.QStandardItemModel()
        for img_file in self.img_files:
            base_name = ntpath.basename(img_file)
            model.appendRow(QtGui.QStandardItem(base_name))
        self.ui.fileList.setModel(model)

    def update_text_list_ui(self):
        """Update model for text list."""
        model = QtGui.QStandardItemModel()
        for name in self.img_text:
            model.appendRow(QtGui.QStandardItem(name))
        self.ui.textList.setModel(model)

    def prev_button_action(self):
        """Go to previous image, do nothing if already at beginning."""
        if self.img_file_id > 0:
            self.img_file_id -= 1
            self.process_image()
            self.update_ui()

    def next_button_action(self):
        """Go to next image, do nothing if already at end."""
        if self.img_file_id < len(self.img_files) - 1:
            self.img_file_id += 1
            self.process_image()
            self.update_ui()

    def current_page_action(self):
        """Go to specific image entered into page selection."""
        if int(self.ui.currPage.text()) - 1 != self.img_file_id:
            self.img_file_id = int(self.ui.currPage.text()) - 1
            self.process_image()
            self.update_ui()

    def save_action(self):
        """Save data back to json file."""
        try:
            #check if the input can be converted to int
            self.img_text[self.text_id] = self.ui.value.text()
            self.update_text_list_ui()

            self.box_info['dataset_info']['attributes']['answer_refined'] = True

            self.box_info['object_info']['face']['result']['ids'] = self.img_text

            # Turn list of Points back into JSON list
            self.box_info['object_info']['face']['result']['bboxes'] = []
            for idx1, bbox in enumerate(self.bboxes):
                self.box_info['object_info']['face']['result']['bboxes'].append([0,0,0,0])
                for idx2, p in enumerate(bbox):
                    if idx2 == 0:
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][0] = p.x/self.img_width
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][1] = p.y/self.img_height

                    if idx2 == 1:
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][2] = \
                            p.x/self.img_width - self.box_info['object_info']['face']['result']['bboxes'][idx1][0]

                    if idx2 == 3:
                        self.box_info['object_info']['face']['result']['bboxes'][idx1][3] = \
                            p.y/self.img_height - self.box_info['object_info']['face']['result']['bboxes'][idx1][1]

            original_file = self.dir_name + "/" + self.file_name + '.json~'
            shutil.copy2(self.dir_name + "/" + self.file_name + '.json', original_file)

            with open(self.dir_name + "/" + self.file_name + '.json', 'w', encoding='utf-8') as json_file:
                json.dump(self.box_info, json_file, ensure_ascii=False, indent=4)

            self.ui.save_alert.setText("Saved!")
        except IndexError:
            self.ui.save_alert.setText("Invalid Text")

    def delete_action(self):
        """Delete current selected bbox."""
        del self.bboxes[self.text_id]
        del self.img_text[self.text_id]

        if self.text_id == len(self.bboxes):
            self.text_id -= 1
        self.update_text_list_ui()
        self.update_ui()

    def new_box_action(self):
        """Add a new box with default size and text."""
        self.bboxes.append([Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)])
        self.img_text.append("--추가해주세요--")
        self.update_text_list_ui()
        self.update_ui()

    def entire_image_action(self):
        """Change current bbox to cover entire image."""
        try:
            self.bboxes[self.text_id] = [
                Point(0, 0),
                Point(self.img_width, 0),
                Point(self.img_width, self.img_height),
                Point(0, self.img_height)
            ]
            self.update_ui()
        except IndexError:
            self.ui.save_alert.setText("Box unavailable")

    def file_selection_changed(self, selected, _):
        """Get new file selection and update UI."""
        indexes = selected.indexes()
        if len(indexes) <= 0:
            return

        self.img_file_id = indexes[0].row()
        self.process_image()
        self.update_ui()

    def text_selection_changed(self, selected, _):
        """Get new text selection and update UI."""
        indexes = selected.indexes()
        if len(indexes) <= 0:
            return
        self.text_id = indexes[0].row()
        if self.bboxes:
            self.color_change = len(self.bboxes) * [False]
            self.color_change[self.text_id] = True
        self.update_ui()
