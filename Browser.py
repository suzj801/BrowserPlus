import os
import sys
import requests
import urllib.parse
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtNetwork import *
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

def translate_menu(menu):
    _translate = {
        'Undo': '撤消',
        'Redo': '恢复',
        'Cut': '剪切',
        'Copy': '复制',
        'Paste': '粘贴',
        'Paste and match style': '保持格式粘贴',
        'Select all': '全选',
        '&Back': '后退',
        '&Forward': '前进',
        '&Reload': '刷新',
        'Save page': '保存',
        'View page source': '查看网页源码',
    }
    for action in menu.actions():
        if action.text() in _translate:
            action.setText(_translate[action.text()])

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
            if current_view.url().url() in ['', 'about:blank']:
                current_view.load(QUrl(self.text()))
            else:
                self.parent.tab_browsers.createTab(self.text())
        QLineEdit.keyPressEvent(self, QKeyEvent)

class MyWebView(QWebEngineView):
    def __init__(self, parent):
        super(QWebEngineView, self).__init__()
        self.parent = parent
        self.loadStarted.connect(self.on_webview_loadstarted)
        self.loadProgress.connect(self.on_webview_loadprogress)
        self.loadFinished.connect(self.on_webview_loadfinished)
        self.page().urlChanged.connect(self.on_url_changed)
        self.page().linkHovered.connect(self.on_link_hovered)

    def load(self, qurl):
        _url = qurl.url()
        parse = urllib.parse.urlparse(_url)
        retry_url = []
        if not parse.scheme:
            retry_url.append('http://'+_url)
            retry_url.append('https://'+_url)
        else:
            retry_url = [_url]
        for r_url in retry_url:
            QWebEngineView.load(self, QUrl(r_url))
            if self.url().url() in retry_url:
                break

    def createWindow(self, QWebEnginePageWebWindowType):
        new_webview = self.parent.tab_browsers.createTab()
        return new_webview

    def contextMenuEvent(self, event):
        menu = self.page().createStandardContextMenu()
        translate_menu(menu)
        menu.exec(event.globalPos())

    @pyqtSlot()
    def on_webview_loadstarted(self):
        self.parent.loading_progress_label.setStyleSheet('background-color:green')

    @pyqtSlot(int)
    def on_webview_loadprogress(self, progress):
        #print(progress) #部分网页加载到100%之后长时间挂起,无法进入loadfinished事件,待分析(如:baidu搜索)
        self.parent.loading_progress_label.setFixedWidth(self.parent.main_widget.width()*progress/100)

    @pyqtSlot()
    def on_webview_loadfinished(self):
        self.parent.loading_progress_label.setStyleSheet('background-color:transparent')
        self.parent.loading_progress_label.setFixedWidth(2)
        _load_url = self.url().url()
        self.parent.text_url_navigation.setText(_load_url)
        webpage = self.page()
        tab_current_index = self.parent.tab_browsers.currentIndex()
        self.parent.tab_browsers.setTabText(tab_current_index, webpage.title())
        #加载图标
        if _load_url.startswith('http'):
            icon_url = _load_url + '/favicon.ico'
            pixmap = QPixmap()
            try:
                req = requests.get(icon_url)
                if req.status_code == 200:
                    pixmap.loadFromData(requests.get(icon_url).content)
                    self.parent.tab_browsers.setTabIcon(tab_current_index, QIcon(pixmap))
            except:
                pass
        if webpage.history().canGoBack():
            self.parent.btn_back.setEnabled(True)
        if webpage.history().canGoForward():
            self.parent.btn_forward.setEnabled(True)
        if urllib.parse.urlparse(self.url().url()).scheme:
            self.parent.btn_fav.setEnabled(True)

    @pyqtSlot(QUrl)
    def on_url_changed(self, url):
        print(url)

    @pyqtSlot(str)
    def on_link_hovered(self, url):
        if url.startswith('http'):
            QToolTip.showText(QCursor.pos(), url, None)

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
        #QWebEngineProfile 抓取cookie
        self.webprofile = QWebEngineProfile.defaultProfile()
        self.webprofile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self.webprofile.setCachePath(CACHES_PATH)
        self.webprofile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.webprofile.setPersistentStoragePath(COOKIES_PATH)
        self.webprofile.cookieStore().cookieAdded.connect(self.on_cookie_added)
        self.createTab('https://www.baidu.com')

    def createTab(self, url=''):
        webview = MyWebView(self.parent)
        current_index = self.addTab(webview, '新标签页')
        self.setCurrentIndex(current_index)
        if url:
            webview.load(QUrl(url))
        else:
            webview.load(QUrl('https://cn.bing.com'))
        #for child in self.tabBar().findChildren(QAbstractButton):#tabbar上close tab的提示修改为中文
        #    if child.inherits('CloseButton'):
        #        child.setToolTip('关闭')
        return webview

    @pyqtSlot(int)
    def on_close_tab(self, index):
        if self.count() > 1:
            self.removeTab(index)

    @pyqtSlot(int)
    def on_tab_changed(self, index):
        self.parent.text_url_navigation.setText(self.currentWidget().url().url())

    @pyqtSlot(QNetworkCookie)
    def on_cookie_added(self, cookie):
        #print(cookie.domain(), cookie.path(), cookie.name(), cookie.value())
        db.add_cookie(cookie.domain(), str(cookie.name(), 'utf-8'), str(cookie.value(), 'utf-8'))

    def createRequest(operation, request, body=None):
        print(operation, request, body)

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
        main_layout.addWidget(self.tab_browsers)

        self.setCentralWidget(self.main_widget)
        #读取配置

    def add_menus(self):#QWebEnginePage不再与QNetworkAccessManager交互, 暂时无法从page中抓取提交数据
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

if __name__=='__main__':
    app = QApplication(sys.argv)
    translator = QTranslator()
    translator.load('qt_' + QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(translator)
    w = BrowserWindow()
    w.showMaximized()
    sys.exit(app.exec_())