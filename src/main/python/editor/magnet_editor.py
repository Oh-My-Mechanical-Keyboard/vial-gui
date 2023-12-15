# SPDX-License-Identifier: GPL-2.0-or-later
import json

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget
from PyQt5.QtCore import Qt, pyqtSignal

from any_keycode_dialog import AnyKeycodeDialog
from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget, EncoderWidget
from widgets.mag_keyboard_widget import MagKeyboardWidget
from keycodes.keycodes import Keycode
from widgets.square_button import SquareButton
from tabbed_keycodes import TabbedKeycodes, keycode_filter_masked
from table_mag_args import MagTabbedKeycodes, mag_keycode_filter_masked
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard


class MAG_ClickableWidget(QWidget):

    clicked = pyqtSignal()

    def mousePressEvent(self, evt):
        super().mousePressEvent(evt)
        self.clicked.emit()


class MagKeymapEditor(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

        self.layout_layers = QHBoxLayout()
        self.layout_size = QVBoxLayout()
        layer_label = QLabel(tr("KeymapEditor", "Layer"))

        layout_labels_container = QHBoxLayout()
        layout_labels_container.addWidget(layer_label)
        layout_labels_container.addLayout(self.layout_layers)
        layout_labels_container.addStretch()
        layout_labels_container.addLayout(self.layout_size)

        # contains the actual keyboard
        self.container = MagKeyboardWidget(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)

        layout = QVBoxLayout()
        layout.addLayout(layout_labels_container)
        layout.addWidget(self.container)
        layout.setAlignment(self.container, Qt.AlignHCenter)
        w = MAG_ClickableWidget()
        w.setLayout(layout)
        w.clicked.connect(self.on_empty_space_clicked)

        self.layer_buttons = []
        self.keyboard = None
        self.current_layer = 0

        layout_editor.changed.connect(self.on_layout_changed)

        self.container.anykey.connect(self.on_any_keycode)

        self.tabbed_keycodes = MagTabbedKeycodes()
        # self.tabbed_keycodes.make_tray()
        self.tabbed_keycodes.th_val_changed.connect(self.on_th_val_changed)
        self.tabbed_keycodes.rt_sw_changed.connect(self.on_rt_sw_changed)
        self.tabbed_keycodes.rt_th_val_changed.connect(self.on_rt_th_val_changed)
        # self.tabbed_keycodes.anykey.connect(self.on_any_keycode)

        self.addWidget(w)
        self.addWidget(self.tabbed_keycodes)

        self.device = None
        KeycodeDisplay.notify_keymap_override(self)

    def on_empty_space_clicked(self):
        self.container.deselect()
        self.container.update()

    def on_th_val_changed(self, val):
        print(val)
        self.set_mag_val_u8(3, val)
    def on_rt_sw_changed(self, sw):
        print(sw)
        self.set_rt_sw(sw)
    def on_rt_th_val_changed(self, val):
        print(val)
        self.set_mag_val_u8(5, val)

    def rebuild_layers(self):
        # delete old layer labels
        for label in self.layer_buttons:
            label.hide()
            label.deleteLater()
        self.layer_buttons = []

        # create new layer labels

        x = 1
        btn = SquareButton(str(x))
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setRelSize(1.667)
        btn.setCheckable(True)
        btn.clicked.connect(lambda state, idx=x: self.switch_layer(idx))
        self.layout_layers.addWidget(btn)
        self.layer_buttons.append(btn)
        for x in range(0,2):
            btn = SquareButton("-") if x else SquareButton("+")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setCheckable(False)
            btn.clicked.connect(lambda state, idx=x: self.adjust_size(idx))
            self.layout_size.addWidget(btn)
            self.layer_buttons.append(btn)

    def adjust_size(self, minus):
        if minus:
            self.container.set_scale(self.container.get_scale() - 0.1)
        else:
            self.container.set_scale(self.container.get_scale() + 0.1)
        self.refresh_layer_display()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            # get number of layers
            self.rebuild_layers()

            self.container.set_keys(self.keyboard.keys, self.keyboard.encoders)

            self.current_layer = 0
            self.on_layout_changed()

            # self.tabbed_keycodes.recreate_keycode_buttons()
            # self.tabbed_keycodes.make_tray()
            # MagTabbedKeycodes.tray.recreate_keycode_buttons()
            self.refresh_layer_display()
        self.container.setEnabled(self.valid())

    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def save_layout(self):
        return self.keyboard.save_layout()

    def restore_layout(self, data):
        if json.loads(data.decode("utf-8")).get("uid") != self.keyboard.keyboard_id:
            ret = QMessageBox.question(self.widget(), "",
                                       tr("KeymapEditor", "Saved keymap belongs to a different keyboard,"
                                                          " are you sure you want to continue?"),
                                       QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.keyboard.restore_layout(data)
        self.refresh_layer_display()

    def on_any_keycode(self):
        if self.container.active_key is None:
            return
        current_code = self.code_for_widget(self.container.active_key)
        if self.container.active_mask:
            kc = Keycode.find_inner_keycode(current_code)
            current_code = kc.qmk_id

        self.dlg = AnyKeycodeDialog(current_code)
        self.dlg.finished.connect(self.on_dlg_finished)
        self.dlg.setModal(True)
        self.dlg.show()

    def on_dlg_finished(self, res):
        if res > 0:
            self.on_keycode_changed(self.dlg.value)

    def code_for_widget(self, widget):
        if widget.desc.row is not None:
            return self.keyboard.layout[(self.current_layer, widget.desc.row, widget.desc.col)]
        else:
            return self.keyboard.encoder_layout[(self.current_layer, widget.desc.encoder_idx,
                                                 widget.desc.encoder_dir)]
    def mag_code_for_widget(self, widget):
            mag_args = []
            mag_args.append(self.keyboard.mag_th_lv_layout[(widget.desc.row, widget.desc.col)])
            mag_args.append(self.keyboard.mag_rt_sw_layout[(widget.desc.row, widget.desc.col)])
            mag_args.append(self.keyboard.mag_rt_lv_layout[(widget.desc.row, widget.desc.col)])
            mag_args.append(self.keyboard.mag_rt_set_lv_layout[(widget.desc.row, widget.desc.col)])
            return mag_args

    def refresh_layer_display(self):
        """ Refresh text on key widgets to display data corresponding to current layer """

        self.container.update_layout()

        for idx, btn in enumerate(self.layer_buttons):
            btn.setEnabled(idx != self.current_layer)
            btn.setChecked(idx == self.current_layer)

        for widget in self.container.widgets:
            code = self.code_for_widget(widget)
            mag_args = self.mag_code_for_widget(widget)
            KeycodeDisplay.display_mag(widget, code, mag_args)
        self.container.update()
        self.container.updateGeometry()

    def switch_layer(self, idx):
        self.container.deselect()
        self.current_layer = idx
        self.refresh_layer_display()

    def set_th_lv(self, keycode):
        """ Change currently selected key to provided keycode """

        if self.container.active_key is None:
            print("none active_key key")
            return

        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            self.keyboard.set_th_lv(r, c, keycode)
            self.refresh_layer_display()

    def set_rt_sw(self, sw):
        if (sw != 0):
            sw = 1
        """ Change currently selected key to provided keycode """

        if self.container.active_key is None:
            print("none active_key key")
            return

        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            self.keyboard.set_rt_sw(r, c, sw)
            self.refresh_layer_display()

    def set_mag_val_u8(self, field, val):
        if (val >= 255):
            val = 255
        if (val <= 0):
            val = 0
        """ Change currently selected key to provided keycode """

        if self.container.active_key is None:
            print("none active_key key")
            return

        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            if field == 3:
                self.keyboard.set_th_lv(r, c, val)
            elif field == 5:
                self.keyboard.set_rt_th_lv(r, c, val)
            elif field == 6:
                pass
            elif field == 7:
                pass
            self.refresh_layer_display()
    def set_rt_th_lv(self, keycode):
        """ Change currently selected key to provided keycode """

        if self.container.active_key is None:
            print("none active_key key")
            return

        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            self.keyboard.set_rt_th_lv(r, c, keycode)
            self.refresh_layer_display()


    def set_key_encoder(self, keycode):
        l, i, d = self.current_layer, self.container.active_key.desc.encoder_idx,\
                            self.container.active_key.desc.encoder_dir

        # if masked, ensure that this is a byte-sized keycode
        if self.container.active_mask:
            if not Keycode.is_basic(keycode):
                return
            kc = Keycode.find_outer_keycode(self.keyboard.encoder_layout[(l, i, d)])
            if kc is None:
                return
            keycode = kc.qmk_id.replace("(kc)", "({})".format(keycode))

        self.keyboard.set_encoder(l, i, d, keycode)
        self.refresh_layer_display()

    def set_key_matrix(self, keycode):
        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            # if masked, ensure that this is a byte-sized keycode
            if self.container.active_mask:
                if not Keycode.is_basic(keycode):
                    return
                kc = Keycode.find_outer_keycode(self.keyboard.layout[(l, r, c)])
                if kc is None:
                    return
                keycode = kc.qmk_id.replace("(kc)", "({})".format(keycode))

            self.keyboard.set_key(l, r, c, keycode)
            self.refresh_layer_display()

    def on_key_clicked(self):
        """ Called when a key on the keyboard widget is clicked """
        self.refresh_layer_display()
        # if self.container.active_mask:
        #     self.tabbed_keycodes.set_keycode_filter(keycode_filter_masked)
        # else:
        #     self.tabbed_keycodes.set_keycode_filter(None)

    def on_key_deselected(self):
        # self.tabbed_keycodes.set_keycode_filter(None)
        pass

    def on_layout_changed(self):
        if self.keyboard is None:
            return

        self.refresh_layer_display()
        self.keyboard.set_layout_options(self.layout_editor.pack())

    def on_keymap_override(self):
        self.refresh_layer_display()
