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


class DepthLineProfileWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        grid_layout = QGridLayout()
        grid_layout.setAlignment(Qt.AlignTop)
        self.setLayout(grid_layout)

        self.cb_image = QComboBox()
        self.cb_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(QLabel("3D Image", self), 0, 0)
        grid_layout.addWidget(self.cb_image, 0, 1)

        self.canvas = FigureCanvas()
        self.canvas.figure.set_tight_layout(True)
        self.canvas.figure.set_size_inches(6.0, 4.0)
        self.canvas.figure.patch.set_facecolor("#c4d6ec")

        self.axes = self.canvas.figure.subplots()
        self.axes.set_facecolor("#ffffff")
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')

        self.canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.canvas.setMinimumSize(200, 150)
        grid_layout.addWidget(self.canvas, 1, 0, 1, 2)

        # Cut slider event
        self.viewer.dims.events.current_step.connect(self._on_slice_change)

        # Events related to layer change
        self.viewer.layers.events.inserted.connect(
            lambda e: e.value.events.name.connect(self._on_layer_change)
        )
        self.viewer.layers.events.inserted.connect(self._on_layer_change)
        self.viewer.layers.events.removed.connect(self._on_layer_change)
        self._on_layer_change(None)

    @property
    def z_data_range(self):
        dims_range = np.array(self.viewer.dims.range, dtype='int')[self.axis][0]
        return np.arange(*dims_range)
    
    @property
    def axis(self):
        axis = list(self.viewer.dims.displayed)
        axis.insert(0, list(set([0, 1, 2]) - set(self.viewer.dims.displayed))[0])
        
        return axis

    def _on_layer_change(self, e):
        """
        Called when a new layer is inserted, removed, or renamed. Updates the layer combobox.
        """
        self.cb_image.clear()
        for x in self.viewer.layers:
            if isinstance(x, napari.layers.Image) & (x.data.ndim == 3) & (x.rgb == False):
                self.cb_image.addItem(x.name, x.data)
                if self._on_mouse_click not in x.mouse_drag_callbacks:
                    x.mouse_drag_callbacks.append(self._on_mouse_click)

    def _on_mouse_click(self, source_layer, event):
        """
        Called when the user clicks in the image. Updates the line plot.
        """
        image_data = source_layer.data
        if image_data is None:
            return

        # Check that we are in 2D mode
        if len(event.dims_displayed) != 2:
            return

        # Take care of the transpose state of the image of in the viewer
        z, y, x = np.array(source_layer.world_to_data(event.position), dtype=np.int_)[self.axis]

        image_transposed = image_data.transpose(self.axis)
        _, max_y, max_x = image_transposed.shape

        # Check that the click is not outside the image
        if not (0 <= y <= max_y) & (0 < x < max_x):
            return

        line_profile = image_transposed[:, y, x]

        self.axes.cla()
        self.axes.plot(self.z_data_range, line_profile)
        self.axes.axvline(self.z_data_range[z], linestyle='--', color='grey')
        self.axes.set_xlim(min(self.z_data_range), max(self.z_data_range))
        self.canvas.draw()

    def _on_slice_change(self, event):
        """
        Called when the user changes the slice slider. Updates the line plot. Update vline.
        """
        line_position = self.z_data_range[event.value[self.axis[0]]]

        if len(self.axes.lines) > 0:
            self.axes.lines[1].set(xdata=[line_position]*2, visible=True)

        self.canvas.draw()
