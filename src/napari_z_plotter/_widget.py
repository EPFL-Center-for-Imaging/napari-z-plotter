from qtpy.QtWidgets import (
    QWidget, 
    QComboBox, 
    QSizePolicy, 
    QLabel, 
    QGridLayout, 
)
from qtpy.QtCore import Qt

import napari
import napari.layers
from matplotlib.backends.backend_qt5agg import FigureCanvas

import numpy as np

class DepthLinePlottingWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        grid_layout = QGridLayout()
        grid_layout.setAlignment(Qt.AlignTop)
        self.setLayout(grid_layout)

        self.cb_image = QComboBox()
        self.cb_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.cb_image.currentTextChanged.connect(self._on_selected_image_change)
        grid_layout.addWidget(QLabel("3D Image", self), 0, 0)
        grid_layout.addWidget(self.cb_image, 0, 1)

        self.canvas = FigureCanvas()
        self.canvas.figure.set_tight_layout(True)
        self.canvas.figure.set_size_inches(6.0, 6.0)
        self.canvas.figure.patch.set_facecolor("#5a626c")

        self.axes = self.canvas.figure.subplots()
        self.axes.set_facecolor("#ffffff")
        self.axes.set_xlabel('Depth')
        self.axes.set_ylabel('Intensity')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')

        self.canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.canvas.setMinimumSize(200, 200)
        grid_layout.addWidget(self.canvas, 3, 0, 1, 2)

        self.viewer.layers.events.inserted.connect(
            lambda e: e.value.events.name.connect(self._on_layer_change)
        )
        self.viewer.layers.events.inserted.connect(self._on_layer_change)
        self.viewer.layers.events.removed.connect(self._on_layer_change)
        self._on_layer_change(None)

    def _on_layer_change(self, e):
        """
        Update the layer selection combobox when a new layer is insered, removed, or renamed.
        It has to be a 3D image.
        """
        self.cb_image.clear()
        for x in self.viewer.layers:
            if isinstance(x, napari.layers.Image):
                if x.data.ndim == 3:
                    self.cb_image.addItem(x.name, x.data)
                    if self._on_mouse_click not in x.mouse_drag_callbacks:
                        x.mouse_drag_callbacks.append(self._on_mouse_click)

    def _on_mouse_click(self, source_layer, event):
        """
        Called when the user clicks in the image.
        """
        image_data = self.cb_image.currentData()
        if image_data is None:
            return

        # Check that we are in 2D mode
        if len(event.dims_displayed) != 2:
            return
        
        # Take care of the transpose state of the image of in the viewer
        axes = list(event.dims_displayed).insert(0, list(set([0, 1, 2]) - set(event.dims_displayed))[0])
        _, p1, p2 = np.array(event.position).astype(int)[axes]
        image_transposed = image_data.transpose(axes)

        # Check that the click is not outside the image
        if (0 <= p1 <= image_transposed.shape[1]) & (0 < p2 < image_transposed.shape[2]):
            line_profile = image_transposed[:, p1, p2]
            self.axes.cla()
            self.axes.plot(line_profile)
            self.canvas.draw()

    # def _on_selected_image_change(self, *args, **kwargs):
    #     """
    #     When the selected image changes, reset the plot and set its limits to the image depth.
    #     """
    #     image_data = self.cb_image.currentData()
    #     if image_data is None:
    #         return
        
    #     self.axes.cla()
    #     self.canvas.figure.patch.set_facecolor("#5a626c")
    #     self.axes.set_facecolor("#ffffff")
    #     self.axes.xaxis.label.set_color('white')
    #     self.axes.yaxis.label.set_color('white')

    #     image_depth = image_data.shape[0]

    #     self.axes.set_xlim(0, image_depth)
    #     self.canvas.draw()
