import sys
import os
import json
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout, QMessageBox, QWidget, \
    QLabel, QHBoxLayout, QFileDialog, QLineEdit, QPushButton, QDialog, QInputDialog, QListWidget, QAction
from PyQt5.QtGui import QIntValidator, QIcon, QCursor
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QUrl, pyqtSignal, QThread, Qt, QObject, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView
import pandas as pd
import clean


class ApplicationWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("非矿数据清洗工具")
        self.setWindowFlags(
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowCloseButtonHint)
        # self.styleComboBox.setCurrentIndex('Fusion')
        self.file_menu = QMenu('&操作', self)
        self.file_menu.addAction('&退出', self.fileQuit)
        self.file_menu.addAction('&导入数据', self.import_csv)
        self.file_menu.addAction('&同步数据字段名', self.update_name)
        self.menuBar().addMenu(self.file_menu)

        self.help_menu = QMenu('&帮助', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)

        self.help_menu.addAction('&关于', self.about)

        self.pbar = DialogWindow(self)  # 进度条

        self.main_widget = QWidget(self)
        main_box = QHBoxLayout(self.main_widget)

        # 左侧输入栏
        hbox_left = QVBoxLayout()
        hbox_start = QHBoxLayout()
        hbox_end = QHBoxLayout()
        hbox_btn = QHBoxLayout()
        hbox_list = QHBoxLayout()
        lable_start = QLabel('起始:', self)
        lable_end = QLabel('结束:', self)

        lable_list = QLabel('字段列表:', self)
        hbox_list.addWidget(lable_list)
        hbox_list.addStretch(2)

        int_validato = QIntValidator(0, 100000, self)  # 实例化整型验证器

        # 自定义edit控件
        self.edit_start = MyLineEdit()
        self.edit_end = MyLineEdit()
        self.edit_start.clicked.connect(self.set_staus_start)
        self.edit_end.clicked.connect(self.set_staus_end)
        self.edit_start.setValidator(int_validato)
        self.edit_end.setValidator(int_validato)

        hbox_start.addWidget(lable_start)
        hbox_end.addWidget(lable_end)
        hbox_start.addWidget(self.edit_start)
        hbox_end.addWidget(self.edit_end)

        self.list_view = ListView()
        self.list_view.index.connect(self.update_items)

        self.btn_1 = QPushButton("导出Excel")
        self.btn_1.setDefault(True)
        self.btn_1.clicked.connect(lambda: self.export_csv())

        self.btn_2 = QPushButton('增加数据点')
        self.btn_2.setDefault(True)
        self.btn_2.clicked.connect(lambda: self.add_point())

        self.btn_3 = QPushButton('同步折线图')
        self.btn_3.setDefault(True)
        self.btn_3.clicked.connect(lambda: self.synchronize_chart())

        hbox_btn.addWidget(self.btn_2)
        hbox_btn.addWidget(self.btn_3)

        hbox_left.addStretch(1)
        hbox_left.addLayout(hbox_start)
        hbox_left.addStretch(1)
        hbox_left.addLayout(hbox_end)
        hbox_left.addStretch(1)
        hbox_left.addLayout(hbox_list)
        hbox_left.addWidget(self.list_view)
        hbox_left.addLayout(hbox_btn)
        hbox_left.addStretch(1)
        hbox_left.addWidget(self.btn_1)
        hbox_left.addStretch(8)

        main_box.addLayout(hbox_left)

        # 添加web view
        hbox_right = QVBoxLayout()
        self.view = QWebEngineView()
        url = os.getcwd() + '/templates/echarts.html'
        self.view.load(QUrl.fromLocalFile(url))
        self.init_channel()
        hbox_right.addWidget(self.view)
        main_box.addLayout(hbox_right)

        main_box.setStretch(0, 1)
        main_box.setSpacing(3)
        main_box.setStretch(1, 6)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.clean_state = False
        self.count = 0
        self.data_source = '主西矿体'

        self.edit_state = 0  # 0:edit都未选中，1:start选中， 2:end选中
        # self.legend = ['pressure', 'height', 'v_in', 'c_in', 'v_out', 'c_out', 'flocculant']
        # self.index = ['17', '1', '16', '4', '14', '11', '5']
        self.legend = None
        self.index = None
        self.input_index = None
        self.path = 'IDtoName.xls'
        self.items = []  # ListWidget初始值

    def init_channel(self):
        """
        为webview绑定交互对象
        """
        self.interact_obj = TInteractObj(self)
        self.interact_obj.receive_str_from_js_callback = self.receive_webdata
        channel = QWebChannel(self.view.page())
        # interact_obj 为交互对象的名字,js中使用
        channel.registerObject("interact_obj", self.interact_obj)
        self.view.page().setWebChannel(channel)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def about(self):
        QMessageBox.about(self, "About", "开发者微信：lijia_5601")

    def update_items(self, i):
        """
        删除操作同步items
        """
        self.items.pop(i)

    def update_name(self):
        data = pd.read_excel(self.path)
        index_data = data['Index'].tolist()
        message_data = data['message'].tolist()
        remove_list = []
        if self.input_index is None:
            QMessageBox.about(self, "提示", "请先导入数据进行清洗！ ")
            return
        else:
            for i, message in enumerate(message_data):
                if '不要' in message or '没用' in message:
                    remove_list.append(i)
            index_data = [str(index_data[i]) for i in range(0, len(index_data), 1) if i not in remove_list]
            message_data = [message_data[i] for i in range(0, len(message_data), 1) if i not in remove_list]
            assert len(index_data) == len(message_data)
            self.index = list(set(index_data).intersection(set(self.input_index)))
            inter_index = [index_data.index(x) for x in self.index]
            self.legend = [message_data[i] for i in inter_index]
            for i, item in enumerate(self.items):
                if item not in self.legend:
                    self.list_view.remove_externalcall(i)
                    self.synchronize_chart()

    def table_show(self):
        self.table.show()

    def set_staus_start(self):
        print('start')
        self.edit_state = 1

    def set_staus_end(self):
        print('end')
        self.edit_state = 2

    def receive_webdata(self, data):
        """
        接收来自js中的数据，并setText
        """
        if data == '':
            QMessageBox.warning(self, "错误", "起点、终点不能为空！")
        elif self.edit_state == 0:
            QMessageBox.about(self, "提示", "请选中输入框！")
        elif self.edit_state == 1:
            self.edit_start.setText(data)
        elif self.edit_state == 2:
            self.edit_end.setText(data)

    def add_point(self):
        if self.clean_state:
            items = list(set(self.legend).difference(set(self.items)))
            value, ok = QInputDialog.getItem(self, "提示信息", "请选择点位:", items, 0, False)
            if ok is False:
                return
            else:
                self.items.append(value)
                self.list_view.view.addItem(value)
        else:
            QMessageBox.about(self, "提示", "请先导入数据进行清洗！ ")
            return

    def import_csv(self):
        """导入CSV文件，执行数据清洗，并传给echarts显示"""
        items = ["主西矿体", "东南矿体"]
        self.data_source, ok = QInputDialog.getItem(self, "提示信息", "请选择数据来源(默认：主西):", items, 0, False)
        self.file_path = QFileDialog.getOpenFileName(self, '选择文件', '', 'Excel files(*.xlsx , *.xls, *.csv)')
        if self.file_path[0] is '':
            return
        else:
            self.pbar.show()
            # 创建并启用子线程
            self.thread = CleanThread(self.file_path)
            self.thread.progressBarValue.connect(self.set_pbar)
            self.thread.start()
            return

    def synchronize_chart(self):
        if self.clean_state:
            data_dic = {}
            for item in self.items:
                i = self.legend.index(item)
                data_dic[item] = self.clean_data[self.index[i]].tolist()
            l = len(self.clean_data['Timestamp'])
            data_dic['timestamp'] = [i for i in range(l)]
            data_json = json.dumps(data_dic)
            self.view.page().runJavaScript('getJson({});'.format(data_json))
        else:
            QMessageBox.about(self, "提示", "请先导入数据进行清洗！ ")
            return

    def set_pbar(self, i):
        """
        使用子线程信号更新 pbar;
        子线程清洗数据结果通过json字符串传给主线程
        """
        if len(i) < 4:
            i = int(i)
            if i >= 0 and i < 101:
                self.pbar.update_progressbar(i)
            elif i == -1:
                self.pbar.setVisible(False)
                self.pbar.update_progressbar(0)
        else:
            self.clean_data = pd.DataFrame(json.loads(i))
            self.input_index = self.clean_data.columns
            self.update_name()
            self.clean_state = True
            self.list_view.view.addItems(self.items)
            self.synchronize_chart()
            print(str(self.input_index))
            QMessageBox.about(self, "提示", "数据清洗完成！")
            return

    def export_csv(self):
        """导出csv文件"""
        if self.edit_start.text() is '' or self.edit_end.text() is '':
            print('请输入起始和结束点!')
            QMessageBox.about(self, "提示", "请输入起始和结束点！ ")
        elif self.clean_state is False:
            QMessageBox.about(self, "提示", "请先导入数据进行清洗！ ")
        else:
            try:
                start = int(self.edit_start.text())
                end = int(self.edit_end.text())
                if start >= end:
                    QMessageBox.warning(self, "错误", '结束点必须大于起始点！')
                    return
                items = ["全部字段", "列表中字段"]
                self.data_field, ok = QInputDialog.getItem(self, "提示信息", "请选择数据字段(默认：全部字段):", items, 0, False)
                save_dir = QFileDialog.getExistingDirectory(self, "选取文件夹", "./")
                if save_dir is '':
                    return
                file_name = self.file_path[0].split('/')[-1]
                if self.data_field is None or self.data_field == '全部字段':
                    export_data = self.clean_data[start: end + 1]
                    result_name = file_name[:-4] + '_' + str(start) + '_' + str(end) + '_all_' + '.csv'
                elif self.data_field == '列表中字段':
                    col = ['Timestamp']
                    for i in self.items:
                        col.append(self.index[self.legend.index(i)])
                    export_data = self.clean_data[col][start: end + 1]
                    result_name = file_name[:-4] + '_' + str(start) + '_' + str(end) + '_part_' + '.csv'
                export_data.to_csv(os.path.join(save_dir, result_name))
                QMessageBox.about(self, "提示", result_name + '导出excel文件成功！')
            except Exception as ex:
                QMessageBox.warning(self, "错误", str(ex))


class MyLineEdit(QLineEdit):
    """
    输入框封装
    """
    clicked = pyqtSignal()  # 定义clicked信号

    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.clicked.emit()  # 发送clicked信号


class Ui_Dialog(object):
    """
    进度条弹窗的封装
    """

    def setupUi(self, Dialog):
        Dialog.setObjectName("数据清洗进度")
        Dialog.resize(369, 128)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.progressBar = QtWidgets.QProgressBar(Dialog)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout.addWidget(self.progressBar, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        # self.buttonBox.accepted.connect(Dialog.accept)
        # self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle('数据清洗进度')
        pass


class DialogWindow(QDialog, Ui_Dialog):
    """
    进度条弹窗封装
    """

    def __init__(self, parent=None):
        super(DialogWindow, self).__init__(parent)
        self.setupUi(self)
        # self.setWindowFlags(Qt.FramelessWindowHint)

    def update_progressbar(self, p_int):
        self.progressBar.setValue(p_int)  # 更新进度条


class ListView(QWidget):
    """
    对列表框的封装
    """
    index = pyqtSignal(int)  # 删除时传递索引信号

    def __init__(self, parent=None):
        self.f = ""
        super(ListView, self).__init__(parent)
        self.layout = QVBoxLayout()
        # self.resize(400,300)
        self.view = QListWidget()
        # self.view.setViewMode(QListWidget.ListMode) #QListWidget.IconMode

        self.view.setLineWidth(50)
        # self.view.addItems(["C", "A", "D", "S"])
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

        self.view.clicked.connect(self.check)  # 单击选中某一个选项
        # 创建右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # 创建QMenu
        self.contextMenu = QMenu(self)
        self.actionA = self.contextMenu.addAction(QIcon("images/0.png"), u'删除')
        # 显示菜单
        self.customContextMenuRequested.connect(self.showContextMenu)
        # 点击删除menu
        self.contextMenu.triggered[QAction].connect(self.remove)

    def check(self, index):
        r = index.row()
        self.f = r

    def showContextMenu(self):
        # 如果有选中项，则显示显示菜单
        items = self.view.selectedIndexes()
        if items:
            self.contextMenu.show()
            self.contextMenu.exec_(QCursor.pos())  # 在鼠标位置显示

    def remove(self, qAction):
        """
        此删除是右键菜单栏点击事件
        """
        if self.f is '':
            QMessageBox.about(self, "提示", "请先单击再右键删除！ ")
            return
        self.index.emit(int(self.f))
        # self.view.takeItem(self.f)#删除行(实际上是断开了与list的联系)
        # 注意：removeItemWidget(self, QListWidgetItem)  # 移除一个Item，无返回值
        # 注意：takeItem(self, int)  # 切断一个Item与List的联系，返回该Item
        self.view.removeItemWidget(self.view.takeItem(self.f))  # 删除

    def remove_externalcall(self, index):
        self.index.emit(int(index))
        self.view.removeItemWidget(self.view.takeItem(index))  # 删除

class CleanThread(QThread):
    """
    把清洗数据封装成QThread，实现进度条实时更新
    """
    progressBarValue = pyqtSignal(str)  # 更新进度条

    def __init__(self, file_path):
        super(CleanThread, self).__init__()
        self.file_path = file_path

    def run(self):
        clean_data = clean.run(self.file_path[0], self.progressBarValue)
        # index = clean_data.columns.values.tolist()
        # data_dic = {}
        # for i in index:
        #     data_dic[i] = clean_data[i].tolist()
        data_dic = clean_data.to_dict('list')
        data_json = json.dumps(data_dic)
        self.progressBarValue.emit('100')
        self.progressBarValue.emit('-1')  # 关闭进度条
        self.progressBarValue.emit(data_json)
        print("加载成功")


class TInteractObj(QObject):
    """
    一个槽函数供js调用(内部最终将js的调用转化为了信号),
    一个信号供js绑定, 这个一个交互对象最基本的组成部分.
    """
    # 该信号会在js中绑定一个js方法.
    sig_send_to_js = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 交互对象接收到js调用后执行的回调函数
        self.receive_str_from_js_callback = None

    # str表示接收str类型的信号,信号是从js发出的.
    @pyqtSlot(str)
    def receive_str_from_js(self, str):
        self.receive_str_from_js_callback(str)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.setFixedSize(1280, 800)
    aw.show()
    app.exec_()
