from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPolygon

from .point import Point


class _DragMode:
    """Index of current bounding box being modified."""
    bbox_idx = None


class _SizeMode(_DragMode):
    """Index of which corner is being resized.

    0: top left
    1: top right
    2: bottom right
    3: bottom left
    """
    corner_idx = None

    def __init__(self, bbox_idx, corner_idx):
        self.bbox_idx = bbox_idx
        self.corner_idx = corner_idx


class _PositionMode(_DragMode):
    def __init__(self, bbox_idx):
        self.bbox_idx = bbox_idx


class ImageWidget(QtWidgets.QLabel):
    """Widget that displays the image along with bounding boxes."""
    # Radius of the drag handle
    DRAG_RADIUS = 6

    # We need to add a margin around the image since having a bbox around the entire image
    # caused drawing issues
    MARGIN = 5

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setFrameStyle(QtWidgets.QFrame.Box)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Upload Image")
        self.setMargin(ImageWidget.MARGIN)

        self.parent = parent

        # Current dragging mode if mouse is pressed (changing size or position)
        self.drag_mode = None

        # Previous location of mouse, used for finding delta position when changing position of bbox
        self.last_mouse_pos = None

    def img_to_qt(self, point):
        """Scale point from image dimension to qt dimension."""
        new_x = point.x / self.pixmap().rect().width() \
            * (self.rect().width() - 2 * ImageWidget.MARGIN) + ImageWidget.MARGIN
        new_y = point.y / self.pixmap().rect().height() \
            * (self.rect().height() - 2 * ImageWidget.MARGIN) + ImageWidget.MARGIN
        return Point(new_x, new_y)

    def qt_to_img(self, point):
        """Scale point from qt dimension to image dimension."""
        new_x = (point.x - ImageWidget.MARGIN) \
            / (self.rect().width() - 2 * ImageWidget.MARGIN) * self.pixmap().rect().width()
        new_y = (point.y - ImageWidget.MARGIN) \
            / (self.rect().height() - 2 * ImageWidget.MARGIN) * self.pixmap().rect().height()
        return Point(new_x, new_y)

    def bbox_to_polygon(self, bbox):
        """Unscaled bounding box to QPolygon"""
        scaled = [self.img_to_qt(point) for point in bbox]
        return QPolygon([QPoint(p.x, p.y) for p in scaled])

    def paintEvent(self, event):
        """Draws bounding box and dragging handle."""
        super().paintEvent(event)
        painter = QtGui.QPainter(self)

        for i, bbox in enumerate(self.parent.bboxes):
            if not self.parent.color_change[i]:
                painter.setPen(QtGui.QPen(Qt.blue, 3))
                # Draw bounding box
                painter.setBrush(Qt.NoBrush)  # No fill
                painter.drawPolygon(self.bbox_to_polygon(bbox))

                # Draw dragging handles
                painter.setBrush(QtGui.QBrush(Qt.blue))  # Fill blue

            else:
                if self.parent.statusLabel.text() == 'Not in the list':
                    painter.setPen(QtGui.QPen(Qt.red, 3))
                    painter.setBrush(QtGui.QBrush(Qt.red))

                else:
                    painter.setPen(QtGui.QPen(Qt.green, 3))
                    painter.setBrush(QtGui.QBrush(Qt.green))

                # Draw bounding box
                painter.setBrush(Qt.NoBrush)  # No fill
                painter.drawPolygon(self.bbox_to_polygon(bbox))

            for point in bbox:
                scaled = self.img_to_qt(point)
                painter.drawEllipse(scaled.x - ImageWidget.DRAG_RADIUS,
                                    scaled.y - ImageWidget.DRAG_RADIUS,
                                    ImageWidget.DRAG_RADIUS * 2,
                                    ImageWidget.DRAG_RADIUS * 2)

    def mousePressEvent(self, event):
        """Checks if the drag is changing size, position, or neither when mouse is pressed.

        Also updates the currently selected bbox in the main window.
        """
        super().mousePressEvent(event)
        for i, bbox in enumerate(self.parent.bboxes):
            selected = False
            for j, point in enumerate(bbox):
                # If cursor is in dragging circle
                scaled = self.img_to_qt(point)
                radius = (((event.pos().x() - scaled.x) ** 2 +
                           (event.pos().y() - scaled.y) ** 2))

                if radius < ImageWidget.DRAG_RADIUS ** 2:
                    self.drag_mode = _SizeMode(i, j)
                    selected = True

            # If cursor is within rectangle
            if not selected and self.bbox_to_polygon(bbox).containsPoint(event.pos(), Qt.OddEvenFill):
                self.drag_mode = _PositionMode(i)
                selected = True

            if selected:
                self.parent.color_change = len(self.parent.bboxes)*[False]
                self.parent.color_change[i] = True
                self.parent.img_id_idx = i
                self.parent.update_text_list_ui()
                self.parent.update_ui()
                break

    def mouseReleaseEvent(self, event):
        """Stops size/position change and update MainWindow when mouse is released."""
        super().mouseReleaseEvent(event)
        self.drag_mode = None
        self.last_mouse_pos = None

    def mouseMoveEvent(self, event):
        """Update bounding box to mouse while dragging."""
        super().mouseMoveEvent(event)
        if self.drag_mode and self.last_mouse_pos:
            bbox = self.parent.bboxes[self.drag_mode.bbox_idx]
            delta = Point(
                event.pos().x() - self.last_mouse_pos[0],
                event.pos().y() - self.last_mouse_pos[1]
            )

            corners = []

            if isinstance(self.drag_mode, _SizeMode):
                corners = [
                    (self.drag_mode.corner_idx, delta),
                    (
                        (self.drag_mode.corner_idx + 1) % 4,
                        Point(delta.x, 0) if self.drag_mode.corner_idx % 2 else Point(0, delta.y)

                    ),
                    (
                        (self.drag_mode.corner_idx - 1) % 4,
                        Point(0, delta.y) if self.drag_mode.corner_idx % 2 else Point(delta.x, 0)
                    )
                ]

            elif isinstance(self.drag_mode, _PositionMode):
                corners = [(i, delta) for i in range(len(bbox))]

            for corner in corners:
                bbox[corner[0]] = self.qt_to_img(self.img_to_qt(bbox[corner[0]]) + corner[1])

            self.update()

        self.last_mouse_pos = (event.pos().x(), event.pos().y())
