#-*-coding:utf-8-*-
import os
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class BaseDialog(QDialog):
    #def __init__(self, parent): #不知道为什么这里的init不会被执行, 待解决
    #    super(QDialog, self).__init__(parent)
    def _initUI(self, parent):
        self.parent = parent
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.initUI()
        self.on_submit = lambda *args: None
        self.on_cancel = lambda *args: None

    def add_ok_cancel_buttons(self, buttons='', text_ok='确定', text_cancel='取消'):
        '''添加确认取消按钮
        buttons: 默认都需要, 1代表只需要确认, 0代表只需要取消'''
        if buttons == 0:
            _buttons = QDialogButtonBox.Cancel
        elif buttons == 1:
            _buttons = QDialogButtonBox.Ok
        else:
            _buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonBox = QDialogButtonBox(_buttons, Qt.Horizontal, parent=self)
        self.layout().addWidget(buttonBox)
        if buttonBox.button(QDialogButtonBox.Ok):
            buttonBox.button(QDialogButtonBox.Ok).setText(text_ok)
        if buttonBox.button(QDialogButtonBox.Cancel):
            buttonBox.button(QDialogButtonBox.Cancel).setText(text_cancel)
        buttonBox.accepted.connect(self._on_submit)
        buttonBox.rejected.connect(self._on_cancel)

    @pyqtSlot()
    def _on_submit(self):
        self.on_submit()
        self.close()

    @pyqtSlot()
    def _on_cancel(self):
        self.on_cancel()
        self.close()
    
def ShowMessageDialog(parent, title, message):
    return QMessageBox.information(parent, title, message)

class ShowCustomMessageDialog(BaseDialog):
    def __init__(self, parent, message, title='提醒'):
        super(BaseDialog, self).__init__(parent)
        self.message = message
        self.title = title
        self._initUI(parent)

    def initUI(self):
        self.setWindowTitle(self.title)
        self.layout().addWidget(QLabel(self.message, self))
        self.add_ok_cancel_buttons(0, text_cancel='确定')

class HomePageDialog(BaseDialog):
    def __init__(self, parent):
        super(BaseDialog, self).__init__(parent)
        self._initUI(parent)

    def initUI(self):
        self.setWindowTitle('设置主页')
        self.resize(600, 100)
        self.setWindowModality(Qt.ApplicationModal)
        widget = QWidget(self)
        grid_layout = QGridLayout()
        widget.setLayout(grid_layout)
        label_current_homepage = QLabel('当前主页: ', widget)
        grid_layout.addWidget(label_current_homepage, 0, 0)
        text_current_homepage = QLabel(self.parent.webview.url().url(), widget)
        grid_layout.addWidget(text_current_homepage, 0, 1)
        label_new_homepage = QLabel('新的主页: ', widget)
        grid_layout.addWidget(label_new_homepage, 1, 0)
        text_new_homepage = QLineEdit('https://', widget)
        text_new_homepage.setFixedWidth(500)
        text_new_homepage.setStyleSheet('line-height:20px;font-size:18px')
        text_new_homepage.selectAll()
        grid_layout.addWidget(text_new_homepage, 1, 1)
        self.layout().addWidget(widget)
        self.add_ok_cancel_buttons()
        
