#-*-coding:utf-8-*-
import os
import sys
import re
import requests
import urllib.parse
import socket
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4.QtNetwork import *
from dialogs import *
import db

APP_PATH = os.path.dirname(__file__)
INI_FILE = os.path.join(APP_PATH, 'config.conf')
LOADING_BACKGROUND = os.path.join(APP_PATH, 'images', 'loading_background.png')
COOKIES_PATH = os.path.join(APP_PATH, '.cookies')
DB_FILE = os.path.join(APP_PATH, 'database')
SQLITEDB = db.get_db(DB_FILE)
db.init_tables(SQLITEDB)
if not os.path.isdir(COOKIES_PATH):
    os.mkdir(COOKIES_PATH)
CACHES_PATH = os.path.join(APP_PATH, '.caches')
if not os.path.isdir(CACHES_PATH):
    os.mkdir(CACHES_PATH)
SEARCH_ENGINE = 'https://cn.bing.com/search?q=%s'
DEFAULT_SCHEME = 'http' #默认scheme
PLUS_SCHEME = 'plus' #保留的scheme, 用来配置浏览器的scheme

class Nav_Button(QPushButton):
    '''导航按钮'''
    def __init__(self, icon_name, action_name, parent):
        super(QPushButton, self).__init__(QIcon(os.path.join(APP_PATH, 'images', icon_name)), action_name, parent)
        self.setFixedWidth(30)
        self.setFixedHeight(30)
        self.setFlat(True)

class Nav_LineEdit(QLineEdit):
    '''导航地址栏'''
    def __init__(self, parent):
        super(QLineEdit, self).__init__(parent)
        self.parent = parent
        self.setStyleSheet('border:0px;border-radius:5px;margin-left:5px;margin-right:5px;')

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() in [Qt.Key_Enter, Qt.Key_Return]:
            current_view = self.parent.tab_browsers.currentWidget()
            if current_view.url().toString() in ['', 'about:blank']:
                current_view.load(QUrl(self.text()))
            else:
                self.parent.tab_browsers.createTab(self.text())
        QLineEdit.keyPressEvent(self, QKeyEvent)


class QLabel_tooltip(QLabel):
    def __init__(self, parent):
        super(QLabel, self).__init__(parent)
        self.parent = parent
        self.setStyleSheet('color:#777;border-top-right-radius:5px;border-top:1px solid #777;border-right:1px solid #777;')
        self.setFixedHeight(20)

    def setText(self, text):
        #need fix 没有实现chrome的功能 鼠标在最左下时链接地址往右显示
        metric = QFontMetrics(self.font())
        width = metric.width(text)+5
        if width > self.parent.width()*0.5: #宽度不超过主窗口的一半
            width = self.parent.width()*0.5
        self.setFixedWidth(width)
        return QLabel.setText(self, text)

class MyWebView(QWebView):
    def __init__(self, parent):
        super(QWebView, self).__init__()
        self.parent = parent
        self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.loadStarted.connect(self.on_webview_loadstarted)
        self.loadProgress.connect(self.on_webview_loadprogress)
        self.loadFinished.connect(self.on_webview_loadfinished)
        self.page().linkHovered.connect(self.on_link_hovered)
        self.page().networkAccessManager().sslErrors.connect(self.sslErrorHandler)
        #忽略js关闭窗口事件, chrome无父窗口的page无法使用js关闭窗口

    def test_local_file(self, url):
        url = urllib.parse.unquote(url)
        if re.match('^\w:', url):
            if os.name == 'nt':
                return True, url.replace('\\', '//')
            else:
                return True, url
        else:
            return False, url

    def load(self, qurl):
        _url = qurl.toString()
        _local_file, _url = self.test_local_file(_url)
        if _local_file:
            QWebView.load(self, QUrl(_url))
        else:
            try:
                parse_result = urllib.parse.urlparse(_url)
                if not parse_result.scheme and not parse_result.netloc: #处理不带scheme的url
                    nslookup_url = _url.split('/')[0]
                    if '.' in nslookup_url:
                        socket.getaddrinfo(nslookup_url, 0, 0, 0, 0)
                        _url = '%s://%s'%(DEFAULT_SCHEME, _url)
                    else:
                        _url = SEARCH_ENGINE % _url
                elif parse_result.scheme in ['about']: #空白页
                    pass
                elif parse_result.scheme == PLUS_SCHEME: #浏览器配置页
                    pass
                QWebView.load(self, QUrl(_url))
            except socket.error: #nslookup failed #需要修复, 当不能解析的时候不能改变url
                self.setHtml('<html><body><center>找不到该服务器IP地址: %s</center></body></html>'%_url)

    def createWindow(self, QWebPageWebWindowType):
        new_webview = self.parent.tab_browsers.createTab()
        return new_webview

    @pyqtSlot()
    def on_webview_loadstarted(self):
        self.parent.loading_progress_label.setStyleSheet('background-color:green')

    @pyqtSlot(int)
    def on_webview_loadprogress(self, progress):
        self.parent.loading_progress_label.setFixedWidth(self.parent.main_widget.width()*progress/100)

    @pyqtSlot()
    def on_webview_loadfinished(self):
        self.parent.loading_progress_label.setStyleSheet('background-color:transparent')
        self.parent.loading_progress_label.setFixedWidth(2)
        _load_url = self.url().toString()
        self.parent.text_url_navigation.setText(_load_url)
        webpage = self.page()
        tab_index = self.parent.tab_browsers.indexOf(self)
        self.parent.tab_browsers.setTabText(tab_index, self.title())
        #加载图标
        if _load_url.startswith('http'):
            icon_url = _load_url + '/favicon.ico'
            pixmap = QPixmap()
            try:
                req = requests.get(icon_url)
                if req.status_code == 200:
                    pixmap.loadFromData(requests.get(icon_url).content)
                    self.parent.tab_browsers.setTabIcon(tab_index, QIcon(pixmap))
            except:
                pass
        if webpage.history().canGoBack():
            self.parent.btn_back.setEnabled(True)
        if webpage.history().canGoForward():
            self.parent.btn_forward.setEnabled(True)
        parse_result = urllib.parse.urlparse(self.url().toString())
        if parse_result.scheme in ['http', 'https']:
            self.parent.btn_fav.setEnabled(True)
            #pyqt4没有cookie added/removed事件, 无法捕捉cookie变化, 所以每次刷新页面都dump一次cookie
            if parse_result.netloc:
                db.dump_cookies(parse_result.netloc, self.page().networkAccessManager().cookieJar().allCookies(), COOKIES_PATH)

    @pyqtSlot(str, str, str)
    def on_link_hovered(self, url, title, element):
        #print(url, title, element)
        if url.startswith('http'):
            self.parent.tooltip.setText(url)
            self.parent.tooltip.show()
        else:
            self.parent.tooltip.setVisible(False)

    @pyqtSlot(QNetworkReply, list)
    def sslErrorHandler(self, reply, errorList):
        reply.ignoreSslErrors()
        print("SSL error ignored")

class Tab_Browsers(QTabWidget):
    def __init__(self, parent):
        super(QTabWidget, self).__init__()
        self.parent = parent
        tabBar = self.tabBar()
        self.setTabShape(QTabWidget.Triangular)
        self.setDocumentMode(True)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.on_close_tab)
        self.setIconSize(QSize(12, 12))
        self.currentChanged.connect(self.on_tab_changed)
        self.createTab('https://www.baidu.com')

    def createTab(self, url=''):
        webview = MyWebView(self.parent)
        current_index = self.addTab(webview, '新标签页')
        self.setCurrentIndex(current_index)
        if url:
            webview.load(QUrl(url))
        else:
            webview.load(QUrl('https://cn.bing.com'))
        return webview

    @pyqtSlot(int)
    def on_close_tab(self, index):
        if self.count() > 1:
            self.removeTab(index)

    @pyqtSlot(int)
    def on_tab_changed(self, index):
        self.parent.text_url_navigation.setText(self.currentWidget().url().toString())

class BrowserWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle('浏览器Plus')
        #主框架
        main_layout = QVBoxLayout(self)
        self.main_widget = QWidget(self)
        self.main_widget.setLayout(main_layout)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        #菜单
        #self.add_menus()
        #工具栏
        toolbar_layout = QHBoxLayout()
        self.toolbar_widget = QWidget(self)
        self.toolbar_widget.setFixedHeight(30)
        self.toolbar_widget.setLayout(toolbar_layout)
        toolbar_layout.setSpacing(0)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toolbar_widget)
        self.add_widgets_to_toolbar(toolbar_layout)
        #进度条
        self.loading_progress_label = QLabel(' ')
        self.loading_progress_label.setFixedHeight(2)
        self.loading_progress_label.setFixedWidth(2)
        self.loading_progress_label.setStyleSheet('background-color:transparent')
        main_layout.addWidget(self.loading_progress_label)
        #多选项卡浏览器
        self.tab_browsers = Tab_Browsers(self)
        #调试控制台
        self.debugview = QWebInspector(self)
        #分隔主窗口和控制台
        splitter = QSplitter(self)
        splitter.addWidget(self.tab_browsers)
        splitter.addWidget(self.debugview)
        splitter.setOrientation(Qt.Vertical)
        self.debugview.setVisible(False)
        self.last_dev_page = None
        main_layout.addWidget(splitter)
        #webview tooltip
        self.tooltip = QLabel_tooltip(self)
        self.tooltip.move(0, self.height()-20)
        self.tooltip.setVisible(False)
        self.tooltip.raise_()

        self.setCentralWidget(self.main_widget)
        #读取配置

    def add_menus(self):
        menubar = self.menuBar()
        #
        menu_webview = menubar.addMenu('浏览器')
        ##
        menu_home = QMenu('设置主页', self)
        action_set_current_url = QAction('设置当前页为主页', self)
        action_set_current_url.triggered.connect(self.on_set_current_url_homepage_click)
        menu_home.addAction(action_set_current_url)
        action_set_custom_url = QAction('自定义主页', self)
        action_set_custom_url.triggered.connect(self.on_set_custome_url_homepage_click)
        menu_home.addAction(action_set_custom_url)
        menu_webview.addMenu(menu_home)
        ##
        menu_record_fill = QMenu('记录填充', self)
        action_start_record = QAction('开始记录', self, checkable=True)
        menu_record_fill.addAction(action_start_record)
        action_page_autologin = QAction('此页自动登录', self, checkable=True)
        menu_record_fill.addAction(action_page_autologin)
        action_clear_fill = QAction('清除所有填充', self)
        menu_record_fill.addAction(action_clear_fill)
        menu_webview.addMenu(menu_record_fill)

    def add_widgets_to_toolbar(self, toolbar):
        '''添加工具栏按钮及导航条'''
        self.btn_back = Nav_Button('nav_back.png', '', self)
        self.btn_back.clicked.connect(self.on_btn_back_click)
        toolbar.addWidget(self.btn_back)
        self.btn_back.setEnabled(False)
        self.btn_forward = Nav_Button('nav_forward.png', '', self)
        self.btn_forward.clicked.connect(self.on_btn_forward_click)
        toolbar.addWidget(self.btn_forward)
        self.btn_forward.setEnabled(False)
        self.btn_refresh = Nav_Button('nav_refresh.png', '', self)
        self.btn_refresh.clicked.connect(self.on_btn_refresh_click)
        toolbar.addWidget(self.btn_refresh)
        self.btn_fav = Nav_Button('nav_fav.png', '', self)
        toolbar.addWidget(self.btn_fav)
        self.text_url_navigation = Nav_LineEdit(self)
        toolbar.addWidget(self.text_url_navigation)

    @pyqtSlot()
    def on_set_custome_url_homepage_click(self):
        dialog = HomePageDialog(self)
        dialog.exec_()

    @pyqtSlot()
    def on_set_current_url_homepage_click(self):
        ShowMessageDialog(self, '当前url', self.webview.url().url())

    @pyqtSlot()
    def on_btn_back_click(self):
        self.tab_browsers.currentWidget().page().history().back()
        if self.tab_browsers.currentWidget().page().history().currentItemIndex() == 0:
            self.btn_back.setEnabled(False)

    @pyqtSlot()
    def on_btn_forward_click(self):
        self.tab_browsers.currentWidget().page().history().forward()
        if self.tab_browsers.currentWidget().page().history().currentItemIndex() == \
            len(self.tab_browsers.currentWidget().page().history().items()) - 1:
            self.btn_forward.setEnabled(False)

    @pyqtSlot()
    def on_btn_refresh_click(self):
        self.tab_browsers.currentWidget().load(self.tab_browsers.currentWidget().url())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F12:
            if self.debugview.isVisible():
                self.debugview.setVisible(False)
            else:
                if not self.last_dev_page or self.last_dev_page != self.tab_browsers.currentWidget().page():
                    self.debugview.setPage(self.tab_browsers.currentWidget().page())
                self.debugview.show()
            self.last_dev_page = self.tab_browsers.currentWidget().page()

    def resizeEvent(self, event):
        #调整tooltip的位置
        height = self.height()-20
        horizontal_scrollbar = self.tab_browsers.currentWidget().page().mainFrame().scrollBarGeometry(Qt.Horizontal)
        if horizontal_scrollbar: #减去水平滚动条的高度
            height -= horizontal_scrollbar.height()
        self.tooltip.move(0, height)

if __name__=='__main__':
    app = QApplication(sys.argv)
    translator = QTranslator()
    translator.load('qt_' + QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(translator)
    w = BrowserWindow()
    w.showMaximized()
    sys.exit(app.exec_())