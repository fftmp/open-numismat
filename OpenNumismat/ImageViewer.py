from PyQt5.QtCore import Qt, QMargins, QSettings, QObject, QPointF, QRectF, QRect, pyqtSignal, QMimeData
from PyQt5.QtGui import QPixmap, QPen, QTransform, QImage, QKeySequence, QColor
from PyQt5.QtWidgets import *

import OpenNumismat
from OpenNumismat.Tools.DialogDecorators import storeDlgSizeDecorator, storeDlgPositionDecorator
from OpenNumismat.Tools.Gui import createIcon, getSaveFileName

ZOOM_IN_FACTOR = 1.25
ZOOM_MAX = 5


@storeDlgPositionDecorator
class CropDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.tr("Crop"))

        buttonBox = QDialogButtonBox(Qt.Horizontal)
        buttonBox.addButton(QDialogButtonBox.Ok)
        buttonBox.addButton(QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
#        layout.addWidget(tab)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

    def showEvent(self, _e):
        self.setFixedSize(self.size())


@storeDlgPositionDecorator
class RotateDialog(QDialog):
    valueChanged = pyqtSignal(float)

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.tr("Rotate"))

        angelLabel = QLabel(self.tr("Angel:"))

        angelSlider = QSlider(Qt.Horizontal)
        angelSlider.setRange(-180, 180)
        angelSlider.setTickInterval(10)
        angelSlider.setTickPosition(QSlider.TicksAbove)
        angelSlider.setMinimumWidth(200)

        self.angelSpin = QDoubleSpinBox()
        self.angelSpin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.angelSpin.setRange(-180, 180)
        self.angelSpin.setSingleStep(0.1)
        self.angelSpin.setAccelerated(True)
        self.angelSpin.setKeyboardTracking(False)

        angelSlider.valueChanged.connect(self.angelSpin.setValue)
        self.angelSpin.valueChanged.connect(angelSlider.setValue)
        self.angelSpin.valueChanged.connect(self.valueChanged.emit)

        angelLayout = QHBoxLayout()
        angelLayout.addWidget(angelLabel)
        angelLayout.addWidget(angelSlider)
        angelLayout.addWidget(self.angelSpin)

        settings = QSettings()
        autoCropEnabled = settings.value('rotate_dialog/auto_crop', False, type=bool)
        self.autoCrop = QCheckBox(self.tr("Auto crop"))
        self.autoCrop.stateChanged.connect(self.autoCropChanged)
        self.autoCrop.setChecked(autoCropEnabled)

        gridEnabled = settings.value('rotate_dialog/grid', False, type=bool)
        self.gridShown = QCheckBox(self.tr("Show grid"))
        self.gridShown.stateChanged.connect(self.gridChanged)
        self.gridShown.setChecked(gridEnabled)

        buttonBox = QDialogButtonBox(Qt.Horizontal)
        buttonBox.addButton(QDialogButtonBox.Ok)
        buttonBox.addButton(QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(angelLayout)
        layout.addWidget(self.autoCrop)
        layout.addWidget(self.gridShown)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

    def showEvent(self, _e):
        self.setFixedSize(self.size())

    def autoCropChanged(self, state):
        settings = QSettings()
        settings.setValue('rotate_dialog/auto_crop', state)

        self.valueChanged.emit(self.angelSpin.value())

    def isAutoCrop(self):
        return self.autoCrop.isChecked()

    def gridChanged(self, state):
        settings = QSettings()
        settings.setValue('rotate_dialog/grid', state)

        self.valueChanged.emit(self.angelSpin.value())

    def isGridShown(self):
        return self.gridShown.isChecked()


class BoundingPointItem(QGraphicsRectItem):
    SIZE = 4
    TOP_LEFT = 0
    TOP_RIGHT = 1
    BOTTOM_RIGHT = 2
    BOTTOM_LEFT = 3

    def __init__(self, bounding, width, height, corner):
        self.bounding = bounding
        self.width = width
        self.height = height
        self.corner = corner

        if corner == self.TOP_LEFT:
            x = 0
            y = 0
        elif corner == self.TOP_RIGHT:
            x = width
            y = 0
        elif corner == self.BOTTOM_RIGHT:
            x = width
            y = height
        else:  # corner == self.BOTTOM_LEFT
            x = 0
            y = height

        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE)
        self.setPos(QPointF(x, y))

        self.setBrush(Qt.white)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
#        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            newPos = value
            if self.corner == self.TOP_LEFT:
                if newPos.x() < 0:
                    newPos.setX(0)
                if newPos.y() < 0:
                    newPos.setY(0)

                oppositePoint = self.bounding.points[self.BOTTOM_RIGHT]
                oppositePos = oppositePoint.scenePos()
                if newPos.x() > oppositePos.x() - self.SIZE:
                    newPos.setX(oppositePos.x() - self.SIZE)
                if newPos.y() > oppositePos.y() - self.SIZE:
                    newPos.setY(oppositePos.y() - self.SIZE)

                self.bounding.points[self.BOTTOM_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.TOP_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.BOTTOM_LEFT].setX(newPos.x())
                self.bounding.points[self.TOP_RIGHT].setY(newPos.y())
                self.bounding.points[self.BOTTOM_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                self.bounding.points[self.TOP_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
            elif self.corner == self.TOP_RIGHT:
                if newPos.x() > self.width:
                    newPos.setX(self.width)
                if newPos.y() < 0:
                    newPos.setY(0)

                oppositePoint = self.bounding.points[self.BOTTOM_LEFT]
                oppositePos = oppositePoint.scenePos()
                if newPos.x() < oppositePos.x() + self.SIZE:
                    newPos.setX(oppositePos.x() + self.SIZE)
                if newPos.y() > oppositePos.y() - self.SIZE:
                    newPos.setY(oppositePos.y() - self.SIZE)

                self.bounding.points[self.BOTTOM_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.TOP_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.BOTTOM_RIGHT].setX(newPos.x())
                self.bounding.points[self.TOP_LEFT].setY(newPos.y())
                self.bounding.points[self.BOTTOM_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                self.bounding.points[self.TOP_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
            elif self.corner == self.BOTTOM_RIGHT:
                if newPos.x() > self.width:
                    newPos.setX(self.width)
                if newPos.y() > self.height:
                    newPos.setY(self.height)

                oppositePoint = self.bounding.points[self.TOP_LEFT]
                oppositePos = oppositePoint.scenePos()
                if newPos.x() < oppositePos.x() + self.SIZE:
                    newPos.setX(oppositePos.x() + self.SIZE)
                if newPos.y() < oppositePos.y() + self.SIZE:
                    newPos.setY(oppositePos.y() + self.SIZE)

                self.bounding.points[self.BOTTOM_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.TOP_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.BOTTOM_LEFT].setY(newPos.y())
                self.bounding.points[self.TOP_RIGHT].setX(newPos.x())
                self.bounding.points[self.BOTTOM_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                self.bounding.points[self.TOP_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
            else:  # self.corner == self.BOTTOM_LEFT
                if newPos.x() < 0:
                    newPos.setX(0)
                if newPos.y() > self.height:
                    newPos.setY(self.height)

                oppositePoint = self.bounding.points[self.TOP_RIGHT]
                oppositePos = oppositePoint.scenePos()
                if newPos.x() > oppositePos.x() - self.SIZE:
                    newPos.setX(oppositePos.x() - self.SIZE)
                if newPos.y() < oppositePos.y() + self.SIZE:
                    newPos.setY(oppositePos.y() + self.SIZE)

                self.bounding.points[self.BOTTOM_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.TOP_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
                self.bounding.points[self.BOTTOM_RIGHT].setY(newPos.y())
                self.bounding.points[self.TOP_LEFT].setX(newPos.x())
                self.bounding.points[self.BOTTOM_RIGHT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                self.bounding.points[self.TOP_LEFT].setFlag(QGraphicsItem.ItemSendsGeometryChanges)

            self.bounding.updateRect()

            return newPos

        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        if self.corner in (self.TOP_LEFT, self.BOTTOM_RIGHT):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeBDiagCursor)

        super().hoverEnterEvent(event)


class GraphicsBoundingItem(QObject):

    def __init__(self, width, height, scale):
        super().__init__()

        self.width = width
        self.height = height
        self.scale = scale

        point1 = BoundingPointItem(self, self.width, self.height,
                                   BoundingPointItem.TOP_LEFT)
        point1.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        point2 = BoundingPointItem(self, self.width, self.height,
                                   BoundingPointItem.TOP_RIGHT)
        point2.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        point3 = BoundingPointItem(self, self.width, self.height,
                                   BoundingPointItem.BOTTOM_RIGHT)
        point3.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        point4 = BoundingPointItem(self, self.width, self.height,
                                   BoundingPointItem.BOTTOM_LEFT)
        point4.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.points = [point1, point2, point3, point4]

        self.rect = QGraphicsRectItem()
        self.rect.setPen(QPen(Qt.DashLine))
        self.rect.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.updateRect()

    def updateRect(self):
        p1 = self.points[BoundingPointItem.TOP_LEFT].scenePos()
        p2 = self.points[BoundingPointItem.BOTTOM_RIGHT].scenePos()
        rect = QRectF(p1 * self.scale, p2 * self.scale)
        self.rect.setRect(rect)

    def setScale(self, scale):
        self.scale = scale

        self.updateRect()

    def items(self):
        return [self.rect] + self.points

    def cropRect(self):
        rect = QRectF(self.rect.rect().topLeft() / self.scale,
                      self.rect.rect().bottomRight() / self.scale)
        return rect.toRect()


class GraphicsGridItem(QObject):
    STEP = 40

    def __init__(self, width, height, scale):
        super().__init__()

        self.width = width * scale - 1
        self.height = height * scale - 1

        self.v_lines = []
        for i in range(int(self.width / self.STEP) + 1):
            line = QGraphicsLineItem()
            line.setPen(QPen(QColor(Qt.red)))
            line.setFlag(QGraphicsItem.ItemIgnoresTransformations)

            line.setLine(i * self.STEP, 0, i * self.STEP, self.height)

            self.v_lines.append(line)

        self.h_lines = []
        for i in range(int(self.height / self.STEP) + 1):
            line = QGraphicsLineItem()
            line.setPen(QPen(QColor(Qt.red)))
            line.setFlag(QGraphicsItem.ItemIgnoresTransformations)

            self.h_lines.append(line)

            line.setLine(0, i * self.STEP, self.width, i * self.STEP)

    def items(self):
        return self.v_lines + self.h_lines


class GraphicsView(QGraphicsView):

    def __init__(self, scene, parent):
        super().__init__(scene, parent)

        self.setStyleSheet("border: 0px;")

    def wheelEvent(self, event):
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
#        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        oldPos = self.mapToScene(event.pos())

        if event.angleDelta().y() > 0:
            self.parent().zoomIn()
        else:
            self.parent().zoomOut()

        # Get the new position
        newPos = self.mapToScene(event.pos())

        # Move scene to old position
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())


@storeDlgSizeDecorator
class ImageViewer(QDialog):
    imageSaved = pyqtSignal(QImage)

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowSystemMenuHint |
                         Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        self.scene = QGraphicsScene()
        self.viewer = GraphicsView(self.scene, self)

        self.viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewer.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewer.installEventFilter(self)
        self.viewer.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.menuBar = QMenuBar()

        self.toolBar = QToolBar()

        self.statusBar = QStatusBar()

        self.sizeLabel = QLabel()
        self.statusBar.addWidget(self.sizeLabel)

        self.zoomLabel = QLabel()
        self.statusBar.addWidget(self.zoomLabel)

        layout = QVBoxLayout()
        layout.setMenuBar(self.menuBar)
        layout.addWidget(self.toolBar)
        layout.addWidget(self.viewer)
        layout.addWidget(self.statusBar)
        layout.setContentsMargins(QMargins())
        layout.setSpacing(0)
        self.setLayout(layout)

        self.isChanged = False
        self.cropDlg = None
        self.rotateDlg = None
        self.grid = None
        self.bounding = None
        self.isFullScreen = False
        self.name = 'photo'
        self._pixmapHandle = None
        self._origPixmap = None
        self._startPixmap = None
        self.scale = 1
        self.minScale = 0.2
        self.isFitToWindow = True

        self.createActions()
        self.createMenus()
        self.createToolBar()

    def createActions(self):
        self.saveAsAct = QAction(self.tr("&Save As..."), self, shortcut=QKeySequence.SaveAs, triggered=self.saveAs)
#        self.printAct = QAction(self.tr("&Print..."), self, shortcut=QKeySequence.Print, enabled=False, triggered=self.print_)
        self.exitAct = QAction(self.tr("E&xit"), self, shortcut=QKeySequence.Quit, triggered=self.close)
        self.fullScreenAct = QAction(self.tr("Full Screen"), self, shortcut=QKeySequence.FullScreen, triggered=self.fullScreen)
        self.zoomInAct = QAction(createIcon('zoom_in.png'), self.tr("Zoom &In (25%)"), self, triggered=self.zoomIn)
        self.zoomInShortcut = QShortcut(Qt.Key_Plus, self, self.zoomIn)
        self.zoomOutAct = QAction(createIcon('zoom_out.png'), self.tr("Zoom &Out (25%)"), self, triggered=self.zoomOut)
        self.zoomOutShortcut = QShortcut(Qt.Key_Minus, self, self.zoomOut)
        self.normalSizeAct = QAction(createIcon('arrow_out.png'), self.tr("&Normal Size"), self, triggered=self.normalSize)
        self.fitToWindowAct = QAction(createIcon('arrow_in.png'), self.tr("&Fit to Window"), self, triggered=self.fitToWindow)
        self.showToolBarAct = QAction(self.tr("Show Tool Bar"), self, checkable=True, triggered=self.showToolBar)
        self.showStatusBarAct = QAction(self.tr("Show Status Bar"), self, checkable=True, triggered=self.showStatusBar)
        self.rotateLeftAct = QAction(createIcon('arrow_rotate_anticlockwise.png'), self.tr("Rotate to Left"), self, triggered=self.rotateLeft)
        self.rotateRightAct = QAction(createIcon('arrow_rotate_clockwise.png'), self.tr("Rotate to Right"), self, triggered=self.rotateRight)
        self.rotateAct = QAction(self.tr("Rotate..."), self, checkable=True, triggered=self.rotate)
        self.cropAct = QAction(createIcon('shape_handles.png'), self.tr("Crop"), self, checkable=True, triggered=self.crop)
        self.saveAct = QAction(createIcon('save.png'), self.tr("Save"), self, shortcut=QKeySequence.Save, triggered=self.save)
        self.saveAct.setDisabled(True)
        self.copyAct = QAction(createIcon('page_copy.png'), self.tr("Copy"), self, shortcut=QKeySequence.Copy, triggered=self.copy)

        settings = QSettings()
        toolBarShown = settings.value('image_viewer/tool_bar', True, type=bool)
        self.showToolBarAct.setChecked(toolBarShown)
        self.toolBar.setVisible(toolBarShown)
        statusBarShown = settings.value('image_viewer/status_bar', True, type=bool)
        self.showStatusBarAct.setChecked(statusBarShown)
        self.statusBar.setVisible(statusBarShown)

    def createMenus(self):
        self.fileMenu = QMenu(self.tr("&File"), self)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.saveAsAct)
#        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.editMenu = QMenu(self.tr("&Edit"), self)
        self.editMenu.addAction(self.copyAct)
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.rotateLeftAct)
        self.editMenu.addAction(self.rotateRightAct)
        self.editMenu.addAction(self.rotateAct)
        self.editMenu.addAction(self.cropAct)

        self.viewMenu = QMenu(self.tr("&View"), self)
        self.viewMenu.addAction(self.fullScreenAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addAction(self.fitToWindowAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.showToolBarAct)
        self.viewMenu.addAction(self.showStatusBarAct)

        self.menuBar.addMenu(self.fileMenu)
        self.menuBar.addMenu(self.editMenu)
        self.menuBar.addMenu(self.viewMenu)

    def createToolBar(self):
        self.toolBar.addAction(self.zoomInAct)
        self.toolBar.addAction(self.zoomOutAct)
        self.toolBar.addAction(self.normalSizeAct)
        self.toolBar.addAction(self.fitToWindowAct)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.rotateLeftAct)
        self.toolBar.addAction(self.rotateRightAct)
        self.toolBar.addAction(self.cropAct)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.saveAct)

    def showToolBar(self, status):
        settings = QSettings()
        settings.setValue('image_viewer/tool_bar', status)
        self.toolBar.setVisible(status)

    def showStatusBar(self, status):
        settings = QSettings()
        settings.setValue('image_viewer/status_bar', status)
        self.statusBar.setVisible(status)

    def hasImage(self):
        return self._pixmapHandle is not None

    def clearImage(self):
        if self.hasImage():
            self.scene.removeItem(self._pixmapHandle)
            self._pixmapHandle = None

    def pixmap(self):
        if self.hasImage():
            return self._pixmapHandle.pixmap()
        return None

    def showEvent(self, _e):
        self.updateViewer()

    def resizeEvent(self, _e):
        if self.isVisible():
            self.updateViewer()

    def setImage(self, image):
        if type(image) is QPixmap:
            pixmap = image
        else:
            pixmap = QPixmap.fromImage(image)

        if self.hasImage():
            self._pixmapHandle.setPixmap(pixmap)
        else:
            self._origPixmap = pixmap
            self._pixmapHandle = self.scene.addPixmap(pixmap)

        self.viewer.setSceneRect(QRectF(pixmap.rect()))
        self.updateViewer()

        self.sizeLabel.setText("%dx%d" % (image.width(), image.height()))

    def saveAs(self):
        filters = (self.tr("Images (*.jpg *.jpeg *.bmp *.png *.tiff *.gif)"),
                   self.tr("All files (*.*)"))
        fileName, _selectedFilter = getSaveFileName(
            self, 'save_image', self.name, OpenNumismat.IMAGE_PATH, filters)
        if fileName:
            self._pixmapHandle.pixmap().save(fileName)

    def done(self, r):
        if self.cropDlg and self.cropDlg.isVisible():
            self.cropDlg.close()
            return
        if self.rotateDlg and self.rotateDlg.isVisible():
            self.rotateDlg.close()
            return

        if self.isFullScreen:
            self.isFullScreen = False

            self.menuBar.show()
            self.toolBar.setVisible(self.showToolBarAct.isChecked())
            self.statusBar.setVisible(self.showStatusBarAct.isChecked())

            self.showNormal()
        else:
            if self.isChanged:
                result = QMessageBox.warning(
                    self, self.tr("Save"),
                    self.tr("Image was changed. Save changes?"),
                    QMessageBox.Save | QMessageBox.No, QMessageBox.No)
                if result == QMessageBox.Save:
                    self.save()

            super().done(r)

    def fullScreen(self):
        self.isFullScreen = True

        self.menuBar.hide()
        self.toolBar.hide()
        self.statusBar.hide()

        self.showFullScreen()

    def normalSize(self):
        self.viewer.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        self.zoom(1 / self.scale)
        self.scale = 1

    def fitToWindow(self):
        self.isFitToWindow = True

        sceneRect = self.viewer.sceneRect()
        if sceneRect.width() > self.viewer.width() or \
                sceneRect.height() > self.viewer.height():
            self.viewer.fitInView(sceneRect, Qt.KeepAspectRatio)
            self.scale = (self.viewer.height() - 4) / sceneRect.height()
        else:
            self.viewer.resetTransform()
            self.scale = 1

        self._updateGrid()
        if self.bounding:
            self.bounding.setScale(self.scale)

        self._updateZoomActions()

    def copy(self):
        image = self._pixmapHandle.pixmap().toImage()
        mime = QMimeData()
        mime.setImageData(image)

        clipboard = QApplication.clipboard()
        clipboard.setMimeData(mime)

    def zoomIn(self):
        self.zoom(ZOOM_IN_FACTOR)

    def zoomOut(self):
        self.zoom(1 / ZOOM_IN_FACTOR)

    def zoom(self, scale):
        need_scale = self.scale * scale
        if need_scale < self.minScale:
            need_scale = self.minScale
            scale = need_scale / self.scale
        if need_scale > ZOOM_MAX:
            need_scale = ZOOM_MAX
            scale = need_scale / self.scale

        if need_scale > self.minScale:
            self.isFitToWindow = False
        else:
            self.isFitToWindow = True

        if need_scale != self.scale:
            self.scale = need_scale
            self.viewer.scale(scale, scale)

            self._updateGrid()
            if self.bounding:
                self.bounding.setScale(self.scale)

        self._updateZoomActions()

    def updateViewer(self):
        if not self.hasImage():
            return

        self.minScale = (self.viewer.height() - 4) / self.viewer.sceneRect().height()
        if self.minScale > 1:
            self.minScale = 1

        if self.isFitToWindow:
            self.fitToWindow()

        self._updateGrid()
        if self.bounding:
            self.bounding.setScale(self.scale)

        self._updateZoomActions()

    def _updateZoomActions(self):
        sceneRect = self.viewer.sceneRect()
        imageRect = self.viewer.mapToScene(self.viewer.rect()).boundingRect()
        if imageRect.contains(sceneRect):
            self.viewer.setDragMode(QGraphicsView.NoDrag)
        else:
            self.viewer.setDragMode(QGraphicsView.ScrollHandDrag)

        self.zoomInAct.setDisabled(self.scale >= ZOOM_MAX)
        self.zoomOutAct.setDisabled(self.scale <= self.minScale)
        self.fitToWindowAct.setDisabled(self.isFitToWindow)
        self.normalSizeAct.setDisabled(self.scale == 1)

        self.zoomLabel.setText("%d%%" % (self.scale * 100 + 0.5))

    def rotateLeft(self):
        transform = QTransform()
        trans = transform.rotate(-90)
        pixmap = self._pixmapHandle.pixmap()
        pixmap = pixmap.transformed(trans)
        self.setImage(pixmap)

        self.isChanged = True
        self._updateEditActions()

    def rotateRight(self):
        transform = QTransform()
        trans = transform.rotate(90)
        pixmap = self._pixmapHandle.pixmap()
        pixmap = pixmap.transformed(trans)
        self.setImage(pixmap)

        self.isChanged = True
        self._updateEditActions()

    def _updateGrid(self):
        if self.grid:
            for item in self.grid.items():
                self.scene.removeItem(item)

        if self.rotateDlg and self.rotateDlg.isVisible():
            if self.rotateDlg.isGridShown():
                sceneRect = self.viewer.sceneRect()
                w = sceneRect.width()
                h = sceneRect.height()
                self.grid = GraphicsGridItem(w, h, self.scale)
                for item in self.grid.items():
                    self.scene.addItem(item)
            else:
                self.grid = None
        else:
            self.grid = None

    def rotate(self, checked):
        if checked:
            self.rotateDlg = RotateDialog(self)
            self.rotateDlg.valueChanged.connect(self.rotateChanged)
            self.rotateDlg.finished.connect(self.closeRotate)
            self.rotateDlg.show()
            self._startPixmap = self._pixmapHandle.pixmap()

            self._updateEditActions()
        else:
            self.rotateDlg.close()
            self.rotateDlg = None

        self._updateGrid()

    def rotateChanged(self, value):
        transform = QTransform()
        trans = transform.rotate(value)
        pixmap = self._startPixmap.transformed(trans, Qt.SmoothTransformation)
        if self.rotateDlg.isAutoCrop():
            if (-45 < value and value < 45) or value < -135 or 135 < value:
                xoffset = (pixmap.width() - self._startPixmap.width()) / 2
                yoffset = (pixmap.height() - self._startPixmap.height()) / 2
                rect = QRect(xoffset, yoffset, self._startPixmap.width(), self._startPixmap.height())
            else:
                xoffset = (pixmap.width() - self._startPixmap.height()) / 2
                yoffset = (pixmap.height() - self._startPixmap.width()) / 2
                rect = QRect(xoffset, yoffset, self._startPixmap.height(), self._startPixmap.width())
            pixmap = pixmap.copy(rect)

        self.setImage(pixmap)

        self._updateGrid()

    def closeRotate(self, result):
        self._updateGrid()

        if result:
            self.isChanged = True
        else:
            self.setImage(self._startPixmap)

        self._startPixmap = None

        self.rotateAct.setChecked(False)
        self._updateEditActions()

    def crop(self, checked):
        if checked:
            sceneRect = self.viewer.sceneRect()
            w = sceneRect.width()
            h = sceneRect.height()

            self.bounding = GraphicsBoundingItem(w, h, self.scale)
            for item in self.bounding.items():
                self.scene.addItem(item)

            self.cropDlg = CropDialog(self)
            self.cropDlg.finished.connect(self.closeCrop)
            self.cropDlg.show()

            self._updateEditActions()
        else:
            self.cropDlg.close()
            self.cropDlg = None

    def closeCrop(self, result):
        rect = self.bounding.cropRect()

        for item in self.bounding.items():
            self.scene.removeItem(item)
        self.bounding = None

        if result:
            pixmap = self._pixmapHandle.pixmap()
            pixmap = pixmap.copy(rect)
            self.setImage(pixmap)

            self.isChanged = True

        self.cropAct.setChecked(False)
        self._updateEditActions()

    def _updateEditActions(self):
        inCrop = self.cropAct.isChecked()
        inRotate = self.rotateAct.isChecked()
        self.rotateLeftAct.setDisabled(inCrop or inRotate)
        self.rotateRightAct.setDisabled(inCrop or inRotate)
        self.rotateAct.setDisabled(inCrop)
        self.cropAct.setDisabled(inRotate)

        self.saveAct.setEnabled(self.isChanged)

    def save(self):
        if self.isChanged:
            self._origPixmap = self._pixmapHandle.pixmap()
            self.imageSaved.emit(self.getImage())

        self.isChanged = False
        self._updateEditActions()

    def getImage(self):
        return self._origPixmap.toImage()
