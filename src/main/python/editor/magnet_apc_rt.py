# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, QSlider, QDoubleSpinBox, QCheckBox, QGridLayout, QProgressBar
from PyQt5.QtCore import QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication

import math, struct

from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard

def apc_rt_display(widget, apc, rts, mag_th_resolution = 200):
    apc = apc*4.0/mag_th_resolution
    apc_text = "{:.2f}".format(apc)
    widget.setText(apc_text)

    if rts[0] > 0:
        tooltip = f"APC: {apc}, RT: [RELEASE: {rts[1]}, PRESS: {rts[2]}]"
        widget.masked = True
        rt_th = rts[1]*4.0/mag_th_resolution
        rt_set_th = rts[2]*4.0/mag_th_resolution
        rt_text = "{:.2f}|{:.2f}".format(rt_th, rt_set_th)
        widget.setMaskText(rt_text)
        widget.setMaskColor(QApplication.palette().color(QPalette.Link))
    else:
        tooltip = f"APC{apc}, RT: Not Enable"
        widget.masked = False

    widget.setToolTip(tooltip)

class ApcRt(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

        self.keyboardWidget = KeyboardWidget(layout_editor)
        self.keyboardWidget.set_enabled(True)
        self.keyboardWidget.clicked.connect(self.on_key_clicked)
        self.keyboardWidget.set_scale(2.3)
        self.keyboardWidget.magnet_text = True

        layout = QVBoxLayout()
        layout.addWidget(self.keyboardWidget)
        # layout.setAlignment(self.keyboardWidget, Qt.AlignCenter)

        self.addLayout(layout)

        switch_show_layout = QVBoxLayout()
        self.switch_adc_lbl = QLabel(tr("Switch ADC", "Current key adc: NAN"))
        switch_show_layout.addWidget(self.switch_adc_lbl)
        show_pgb_layout = QHBoxLayout()
        self.show_sw_pgb = QProgressBar()
        self.show_sw_pgb.setMinimum(0)
        self.show_sw_pgb.setMaximum(200)
        self.show_sw_pgb.setValue(0)
        self.show_sw_pgb.setOrientation(Qt.Vertical)
        self.show_sw_pgb.setMaximumWidth(30)
        self.show_sw_pgb.setMinimumWidth(15)
        self.show_sw_pgb.setMaximumHeight(100)
        self.show_sw_pgb.setMinimumHeight(90)
        self.show_sw_pgb.setTextVisible(False)
        self.show_sw_pgb.setInvertedAppearance(True)
        show_pgb_layout.addWidget(self.show_sw_pgb)
        switch_show_layout.addLayout(show_pgb_layout)
        self.show_sw_lbl = QLabel(tr("Switch Travel: ", "Key travel: NAN"))
        switch_show_layout.addWidget(self.show_sw_lbl)
        

        self.show_sw_timer = QTimer()
        self.show_sw_timer_interval = 200
        self.show_sw_timer.timeout.connect(self.show_sw_timer_cbk)


        apc_rt_layout = QGridLayout()

        self.apc_lbl = QLabel(tr("APC setting", "Set the actuation point:"))
        self.apc_dpb = QDoubleSpinBox()
        self.apc_dpb.setRange(0.02, 4.0)
        self.apc_dpb.setValue(1.2)
        self.apc_dpb.setSingleStep(0.02)
        self.apc_dpb.valueChanged.connect(self.on_apc_dpb) 
        self.apc_sld = QSlider(Qt.Horizontal)
        self.apc_sld.setMaximumWidth(300)
        self.apc_sld.setMinimumWidth(200)
        self.apc_sld.setRange(1, 200)
        self.apc_sld.setSingleStep(1)
        self.apc_sld.setValue(100)
        self.apc_sld.setTickPosition(QSlider.TicksAbove)
        self.apc_sld.setTracking(False)
        self.apc_sld.valueChanged.connect(self.on_apc_sld) 

        apc_rt_layout.addWidget(self.apc_lbl, 0, 0)
        apc_rt_layout.addWidget(self.apc_dpb, 0, 1)
        apc_rt_layout.addWidget(self.apc_sld, 0, 2)

        self.rt_cbx = QCheckBox("Enable RT")
        self.rt_cbx.setTristate(False)
        self.rt_cbx.setCheckState(Qt.Unchecked)
        self.rt_cbx.stateChanged.connect(self.on_rt_check)
        apc_rt_layout.addWidget(self.rt_cbx, 1, 0)

        self.rt_lbl = QLabel(tr("RT setting", "Set the RT release threshold:"))
        self.rt_dpb = QDoubleSpinBox()
        self.rt_dpb.setEnabled(False)
        self.rt_dpb.setRange(0.02, 3)
        self.rt_dpb.setValue(1.0)
        self.rt_dpb.setSingleStep(0.02)
        self.rt_dpb.valueChanged.connect(self.on_rt_dpb) 
        self.rt_sld= QSlider(Qt.Horizontal)
        self.rt_sld.setEnabled(False)
        self.rt_sld.setMaximumWidth(300)
        self.rt_sld.setMinimumWidth(200)
        self.rt_sld.setRange(1, 150)
        self.rt_sld.setSingleStep(1)
        self.rt_sld.setValue(50)
        self.rt_sld.setTickPosition(QSlider.TicksAbove)
        self.rt_sld.setTracking(False)
        self.rt_sld.valueChanged.connect(self.on_rt_sld) 
        apc_rt_layout.addWidget(self.rt_lbl, 2, 0)
        apc_rt_layout.addWidget(self.rt_dpb, 2, 1)
        apc_rt_layout.addWidget(self.rt_sld, 2, 2)

        self.rt_set_lbl = QLabel(tr("RT setting", "Set the RT press threshold:"))
        self.rt_set_dpb = QDoubleSpinBox()
        self.rt_set_dpb.setEnabled(False)
        self.rt_set_dpb.setRange(0.02, 3)
        self.rt_set_dpb.setValue(1.0)
        self.rt_set_dpb.setSingleStep(0.02)
        self.rt_set_dpb.valueChanged.connect(self.on_rt_set_dpb) 
        self.rt_set_sld= QSlider(Qt.Horizontal)
        self.rt_set_sld.setEnabled(False)
        self.rt_set_sld.setMaximumWidth(300)
        self.rt_set_sld.setMinimumWidth(200)
        self.rt_set_sld.setRange(1, 150)
        self.rt_set_sld.setSingleStep(1)
        self.rt_set_sld.setValue(50)
        self.rt_set_sld.setTickPosition(QSlider.TicksAbove)
        self.rt_set_sld.setTracking(False)
        self.rt_set_sld.valueChanged.connect(self.on_rt_set_sld) 
        apc_rt_layout.addWidget(self.rt_set_lbl, 3, 0)
        apc_rt_layout.addWidget(self.rt_set_dpb, 3, 1)
        apc_rt_layout.addWidget(self.rt_set_sld, 3, 2)


        deadband_layout = QVBoxLayout()
        self.deadband_lbl = QLabel(tr("Deadband", "Deadband Setting (Global)"))
        deadband_layout.addWidget(self.deadband_lbl)

        deadband_top_ctl_layout = QHBoxLayout()
        self.top_deadband_lbl = QLabel(tr("Top Deadband", "Top Deadband:"))
        self.top_deadband_dpb = QDoubleSpinBox()
        self.top_deadband_dpb.setRange(0, 1.0)
        self.top_deadband_dpb.setValue(0.2)
        self.top_deadband_dpb.setSingleStep(0.1)
        self.top_deadband_dpb.valueChanged.connect(self.on_deadband_dpb)
        self.top_deadband_sld = QSlider(Qt.Horizontal)
        self.top_deadband_sld.setMaximumWidth(200)
        self.top_deadband_sld.setMinimumWidth(100)
        self.top_deadband_sld.setRange(0, 50)
        self.top_deadband_sld.setSingleStep(5)
        self.top_deadband_sld.setValue(10)
        self.top_deadband_sld.setTickPosition(QSlider.TicksAbove)
        self.top_deadband_sld.setTracking(False)
        self.top_deadband_sld.valueChanged.connect(self.on_deadband_sld)

        deadband_top_ctl_layout.addWidget(self.top_deadband_lbl)
        deadband_top_ctl_layout.addWidget(self.top_deadband_dpb)
        deadband_top_ctl_layout.addWidget(self.top_deadband_sld)

        deadband_layout.addLayout(deadband_top_ctl_layout)

        self.top_deadband_tip_lbl = QLabel(tr("Top Deadband Tip", "Never trigger in top deadband."))
        deadband_layout.addWidget(self.top_deadband_tip_lbl)
  
        deadband_bottom_ctl_layout = QHBoxLayout()
        self.bottom_deadband_lbl = QLabel(tr("Bottom Deadband", "Bottom Deadband:"))
        self.bottom_deadband_dpb = QDoubleSpinBox()
        self.bottom_deadband_dpb.setRange(0, 1.0)
        self.bottom_deadband_dpb.setValue(0.2)
        self.bottom_deadband_dpb.setSingleStep(0.1)
        self.bottom_deadband_dpb.valueChanged.connect(self.on_deadband_dpb)
        self.bottom_deadband_sld = QSlider(Qt.Horizontal)
        self.bottom_deadband_sld.setMaximumWidth(200)
        self.bottom_deadband_sld.setMinimumWidth(100)
        self.bottom_deadband_sld.setRange(0, 50)
        self.bottom_deadband_sld.setSingleStep(5)
        self.bottom_deadband_sld.setValue(10)
        self.bottom_deadband_sld.setTickPosition(QSlider.TicksAbove)
        self.bottom_deadband_sld.setTracking(False)
        self.bottom_deadband_sld.valueChanged.connect(self.on_deadband_sld)

        deadband_bottom_ctl_layout.addWidget(self.bottom_deadband_lbl)
        deadband_bottom_ctl_layout.addWidget(self.bottom_deadband_dpb)
        deadband_bottom_ctl_layout.addWidget(self.bottom_deadband_sld)

        deadband_layout.addLayout(deadband_bottom_ctl_layout)

        self.top_deadband_tip_lbl = QLabel(tr("Bottom Deadband Tip", "Always trigger in bottom deadband."))
        deadband_layout.addWidget(self.top_deadband_tip_lbl)

        mag_layout = QHBoxLayout()
        mag_layout.addStretch(1)
        mag_layout.addLayout(switch_show_layout)
        mag_layout.addStretch(1)
        mag_layout.addLayout(apc_rt_layout)
        mag_layout.addStretch(1)
        mag_layout.addLayout(deadband_layout)
        mag_layout.addStretch(1)
        self.addLayout(mag_layout)

        self.keyboard = None
        self.device = None
    
    def show_sw_timer_cbk(self):
        if self.keyboardWidget.active_key is None:
            self.show_sw_timer.stop()
            return
        try:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            data = self.keyboard.get_adc(row, col)
            txt = "Current key adc: " + str(data)
            self.switch_adc_lbl.setText(txt)
            data = self.keyboard.get_travel(row, col)
            self.show_sw_pgb.setValue(data)
            data = data*0.02
            if data >= 4.0:
                data = 4.0
            txt = "Key travel: {:.2f}mm".format(data)
            self.show_sw_lbl.setText(txt)
        except:
            print("excepttttttttttttttt")
            self.show_sw_timer.stop()
            self.switch_adc_lbl.setText("Current key adc: NAN")
            self.show_sw_pgb.setValue(0)
            self.show_sw_lbl.setText("Key travel: NAN")

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.keyboardWidget.set_keys(self.keyboard.keys, self.keyboard.encoders)
        self.keyboardWidget.setEnabled(self.valid())
        self.reset_keyboard_widget()

    def valid(self):
        # Check if vial protocol is v3 or later
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.keyboard_type == "magnet") and \
               ((self.device.keyboard.cols // 8 + 1) * self.device.keyboard.rows <= 28)

    def reset_keyboard_widget(self):

        self.keyboardWidget.update_layout()

        for widget in self.keyboardWidget.widgets:
            apc_rt_display(widget, self.keyboard.mag_apc[(widget.desc.row, widget.desc.col)],
                        self.keyboard.mag_rt[(widget.desc.row, widget.desc.col)])
            widget.setOn(False)
        
        self.show_sw_timer.stop()
        
        if self.keyboard is not None:
            self.top_deadband_sld.blockSignals(True)
            self.top_deadband_dpb.blockSignals(True)
            self.bottom_deadband_sld.blockSignals(True)
            self.bottom_deadband_dpb.blockSignals(True)

            self.top_deadband_sld.setValue(self.keyboard.top_deadband_lv)
            self.top_deadband_dpb.setValue(self.keyboard.top_deadband_lv*0.02)

            self.bottom_deadband_sld.setValue(self.keyboard.bottom_deadband_lv)
            self.bottom_deadband_dpb.setValue(self.keyboard.bottom_deadband_lv*0.02)

            self.bottom_deadband_dpb.blockSignals(False)
            self.bottom_deadband_sld.blockSignals(False)
            self.top_deadband_dpb.blockSignals(False)
            self.top_deadband_sld.blockSignals(False)

        self.keyboardWidget.update()
        self.keyboardWidget.updateGeometry()

    def reset_active_apcrt(self):
        if self.keyboardWidget.active_key is None:
            return

        widget = self.keyboardWidget.active_key
        row = widget.desc.row
        col = widget.desc.col
        apc_rt_display(widget, self.keyboard.mag_apc[(row,col)], self.keyboard.mag_rt[(row,col)])
        self.keyboardWidget.update()

    def activate(self):
        self.reset_keyboard_widget()

    def deactivate(self):
        pass

    def on_key_clicked(self):
        """ Called when a key on the keyboard widget is clicked """
        if self.keyboardWidget.active_key is None:
            return

        row = self.keyboardWidget.active_key.desc.row
        col = self.keyboardWidget.active_key.desc.col

        apc = self.keyboard.mag_apc.get((row, col), 100)
        rt  = self.keyboard.mag_rt.get((row,col), [1, 50, 50])

        self.apc_sld.blockSignals(True)
        self.apc_dpb.blockSignals(True)
        self.rt_cbx.blockSignals(True)
        self.rt_sld.blockSignals(True)
        self.rt_dpb.blockSignals(True)
        self.rt_set_sld.blockSignals(True)
        self.rt_set_dpb.blockSignals(True)

        self.apc_sld.setValue(apc)
        self.apc_dpb.setValue(apc*0.02)

        if self.show_sw_timer.isActive():
            self.show_sw_timer.stop()
        
        self.show_sw_timer.start(self.show_sw_timer_interval)

        if rt[0] > 0:
            self.rt_cbx.setCheckState(Qt.Checked)
            self.rt_sld.setEnabled(True)
            self.rt_dpb.setEnabled(True)
            self.rt_set_sld.setEnabled(True)
            self.rt_set_dpb.setEnabled(True)
            self.rt_sld.setValue(rt[1])
            self.rt_dpb.setValue(rt[1]*0.02)
            self.rt_set_sld.setValue(rt[2])
            self.rt_set_dpb.setValue(rt[2]*0.02)
        else:
            self.rt_cbx.setCheckState(Qt.Unchecked)
            self.rt_sld.setEnabled(False)
            self.rt_dpb.setEnabled(False)
            self.rt_set_sld.setEnabled(False)
            self.rt_set_dpb.setEnabled(False)

        self.rt_dpb.blockSignals(False)
        self.rt_sld.blockSignals(False)
        self.rt_set_dpb.blockSignals(False)
        self.rt_set_sld.blockSignals(False)
        self.rt_cbx.blockSignals(False)
        self.apc_dpb.blockSignals(False)
        self.apc_sld.blockSignals(False)

        #print("row={},col={},apc={},rt={}".format(row, col, apc, rt))

    def on_rt_check(self):
        self.rt_cbx.blockSignals(True)
        self.rt_sld.blockSignals(True)
        self.rt_dpb.blockSignals(True)
        self.rt_set_sld.blockSignals(True)
        self.rt_set_dpb.blockSignals(True)
        if self.rt_cbx.isChecked():
            self.rt_dpb.setEnabled(True)
            self.rt_sld.setEnabled(True)
            self.rt_set_dpb.setEnabled(True)
            self.rt_set_sld.setEnabled(True)
            if self.keyboardWidget.active_key is not None:
                row = self.keyboardWidget.active_key.desc.row
                col = self.keyboardWidget.active_key.desc.col
                rt = self.keyboard.mag_rt.get((row, col), [1,50,50])
                if rt[0] == 0:
                    #self.keyboard.amk_rt[(row,col)] = 1
                    self.keyboard.apply_rt(row, col, [1, rt[1], rt[2]])
                    self.rt_sld.setValue(rt[1])
                    self.rt_dpb.setValue(rt[1]*0.02)
                    self.rt_set_sld.setValue(rt[2])
                    self.rt_set_dpb.setValue(rt[2]*0.02)
        else:
            if self.keyboardWidget.active_key is not None:
                row = self.keyboardWidget.active_key.desc.row
                col = self.keyboardWidget.active_key.desc.col
                rt = self.keyboard.mag_rt.get((row, col), [1,50,50])
                if rt[0] > 0:
                    self.keyboard.apply_rt(row, col, [0, rt[1], rt[2]])
                    self.rt_sld.setValue(rt[1])
                    self.rt_dpb.setValue(rt[1]*0.02)
                    self.rt_set_sld.setValue(rt[2])
                    self.rt_set_dpb.setValue(rt[2]*0.02)
            self.rt_dpb.setEnabled(False)
            self.rt_sld.setEnabled(False)
            self.rt_set_dpb.setEnabled(False)
            self.rt_set_sld.setEnabled(False)
        self.rt_dpb.blockSignals(False)
        self.rt_sld.blockSignals(False)
        self.rt_set_dpb.blockSignals(False)
        self.rt_set_sld.blockSignals(False)
        self.rt_cbx.blockSignals(False)
        self.reset_active_apcrt()

    def on_deadband_dpb(self):
        self.top_deadband_sld.blockSignals(True)
        self.top_deadband_dpb.blockSignals(True)
        self.bottom_deadband_sld.blockSignals(True)
        self.bottom_deadband_dpb.blockSignals(True)
        top_val = int(self.top_deadband_dpb.value()/0.02)
        bottom_val = int(self.bottom_deadband_dpb.value()/0.02)
        self.top_deadband_sld.setValue(top_val)
        self.bottom_deadband_sld.setValue(bottom_val)
        if self.keyboard is not None:
            self.keyboard.apply_deadband(top_val, bottom_val)
        self.bottom_deadband_dpb.blockSignals(False)
        self.bottom_deadband_sld.blockSignals(False)
        self.top_deadband_dpb.blockSignals(False)
        self.top_deadband_sld.blockSignals(False)

    def on_deadband_sld(self):
        self.top_deadband_sld.blockSignals(True)
        self.top_deadband_dpb.blockSignals(True)
        self.bottom_deadband_sld.blockSignals(True)
        self.bottom_deadband_dpb.blockSignals(True)
        top_val = self.top_deadband_sld.value()*0.02
        bottom_val = self.bottom_deadband_sld.value()*0.02
        self.top_deadband_dpb.setValue(top_val)
        self.bottom_deadband_dpb.setValue(bottom_val)
        if self.keyboard is not None:
            self.keyboard.apply_deadband(self.top_deadband_sld.value(), self.bottom_deadband_sld.value())
        self.bottom_deadband_dpb.blockSignals(False)
        self.bottom_deadband_sld.blockSignals(False)
        self.top_deadband_dpb.blockSignals(False)
        self.top_deadband_sld.blockSignals(False)

    def on_apc_dpb(self):
        self.apc_sld.blockSignals(True)
        self.apc_dpb.blockSignals(True)
        val = int(self.apc_dpb.value()/0.02)
        self.apc_sld.setValue(val)
        if self.keyboardWidget.active_key is not None:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            self.keyboard.apply_apc(row, col, val)
        self.apc_dpb.blockSignals(False)
        self.apc_sld.blockSignals(False)
        self.reset_active_apcrt()
            

    def on_apc_sld(self):
        self.apc_sld.blockSignals(True)
        self.apc_dpb.blockSignals(True)
        val = self.apc_sld.value()*0.02
        self.apc_dpb.setValue(val)
        if self.keyboardWidget.active_key is not None:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            self.keyboard.apply_apc(row, col, self.apc_sld.value())
        self.apc_dpb.blockSignals(False)
        self.apc_sld.blockSignals(False)
        self.reset_active_apcrt()

    def on_rt_dpb(self):
        self.rt_sld.blockSignals(True)
        self.rt_dpb.blockSignals(True)
        val = int(self.rt_dpb.value()/0.02)
        self.rt_sld.setValue(val)
        if self.keyboardWidget.active_key is not None:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            vals = self.keyboard.mag_rt[(row, col)]
            self.keyboard.apply_rt(row, col, [vals[0], val, vals[2]])
        self.rt_dpb.blockSignals(False)
        self.rt_sld.blockSignals(False)
        self.reset_active_apcrt()

    def on_rt_sld(self):
        self.rt_sld.blockSignals(True)
        self.rt_dpb.blockSignals(True)
        val = self.rt_sld.value()*0.02
        self.rt_dpb.setValue(val)
        if self.keyboardWidget.active_key is not None:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            vals = self.keyboard.mag_rt[(row, col)]
            self.keyboard.apply_rt(row, col, [vals[0], self.rt_sld.value(), vals[2]])
        self.rt_dpb.blockSignals(False)
        self.rt_sld.blockSignals(False)
        self.reset_active_apcrt()

    def on_rt_set_dpb(self):
        self.rt_set_sld.blockSignals(True)
        self.rt_set_dpb.blockSignals(True)
        val = int(self.rt_set_dpb.value()/0.02)
        self.rt_set_sld.setValue(val)
        if self.keyboardWidget.active_key is not None:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            vals = self.keyboard.mag_rt[(row, col)]
            self.keyboard.apply_rt(row, col, [vals[0], vals[1], val])
        self.rt_set_dpb.blockSignals(False)
        self.rt_set_sld.blockSignals(False)
        self.reset_active_apcrt()

    def on_rt_set_sld(self):
        self.rt_set_sld.blockSignals(True)
        self.rt_set_dpb.blockSignals(True)
        val = self.rt_set_sld.value()*0.02
        self.rt_set_dpb.setValue(val)
        if self.keyboardWidget.active_key is not None:
            row = self.keyboardWidget.active_key.desc.row
            col = self.keyboardWidget.active_key.desc.col
            vals = self.keyboard.mag_rt[(row, col)]
            self.keyboard.apply_rt(row, col, [vals[0], vals[1], self.rt_set_sld.value()])
        self.rt_set_dpb.blockSignals(False)
        self.rt_set_sld.blockSignals(False)
        self.reset_active_apcrt()