from qtpy.QtWidgets import (
    QWidget,
    QSizePolicy,
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

    @property
    def data_layers(self):
        return [layer for layer in self.viewer.layers
                if isinstance(layer, napari.layers.Image) & (layer.data.ndim == 3) & (layer.rgb == False)]

    def _on_layer_change(self, e):
        """
        Called when a new layer is inserted, removed, or renamed.
        Binds mouse click event to _on_mouse_click.
        """
        for layer in self.data_layers:
            if self._on_mouse_click not in layer.mouse_drag_callbacks:
                layer.mouse_drag_callbacks.append(self._on_mouse_click)

    def _on_mouse_click(self, source_layer, event):
        """
        Called when the user clicks in the image. Updates the line plot.
        """
        # Check that we are in 2D mode
        if len(event.dims_displayed) != 2:
            return

        line_profiles = []
        for layer in self.data_layers:
            # Check if position on layer
            z, y, x = np.array(layer.world_to_data(event.position), dtype=np.int_)[self.axis]
            max_z, max_y, max_x = np.array(layer.data.shape)[self.axis]

            if (0 <= y <= max_y) & (0 < x < max_x):
                # Take care of the transpose state of the image of in the viewer
                image_transposed = layer.data.transpose(self.axis)

                # Determine z-range of each layer
                z_shift = layer.translate[self.axis[0]]
                z_scale = layer.scale[self.axis[0]]
                z_range = np.arange(max_z) * z_scale + z_shift

                # List of lines to add
                line_profiles += [[z_range, image_transposed[:, y, x]]]

        self.axes.cla()
        [self.axes.plot(*line_profile) for line_profile in line_profiles]
        self._slice_indicator = self.axes.axvline(self.z_data_range[z], linestyle='--', color='grey')
        self.axes.set_xlim(min(self.z_data_range), max(self.z_data_range))
        self.canvas.draw()

    def _on_slice_change(self, event):
        """
        Called when the user changes the slice slider. Updates the line plot. Update vline.
        """
        # prevent error if last layer is unloaded
        if self.data_layers:
            line_position = self.z_data_range[event.value[self.axis[0]]]

            if len(self.axes.lines) > 0:
                self._slice_indicator.set(xdata=[line_position]*2, visible=True)

            self.canvas.draw()
