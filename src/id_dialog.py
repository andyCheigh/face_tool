from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QDialog, QAbstractItemView
from PyQt5.QtGui import QStandardItem, QStandardItemModel


class IDDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        uic.loadUi("id_dialog.ui", self)

        # Make list non-editable
        self.idList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.idList.selectionChanged = self.selection_changed

        with open('id_cand_list.txt', 'r') as file:  # TODO don't hardcode list path
            self.items = file.read().splitlines()

        # Add current id if not present in list
        if self.parent.img_ids[self.parent.img_bbox_idx] not in self.items:
            self.items.insert(0, self.parent.img_ids[self.parent.img_bbox_idx])
            self.parent.statusLabel.setText("Not in the list")

        self.update_ui()

    def update_ui(self):
        """Update all ui elements."""
        model = QStandardItemModel()
        for item in self.items:
            model.appendRow(QStandardItem(item))

        index = self.items.index(self.parent.img_ids[self.parent.img_bbox_idx])
        self.idList.setModel(model)
        self.idList.setCurrentIndex(self.idList.model().createIndex(index, 0))

    def selection_changed(self, selected, _):
        if len(selected.indexes()) > 0:
            self.parent.img_ids[self.parent.img_bbox_idx] = self.items[selected.indexes()[0].row()]
            self.parent.update_id_list_ui()
