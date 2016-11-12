#!/usr/bin/env python3

import os
import numpy as np
import uuid

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from .util import fileloader
from .util import project_functions as pfs
from .util.qt import FileTable, FileTableModel, qtutil
from .videoplayer import PlayerDialog

import sys
from .chebyshev_filter import *


class Widget(QWidget):
    def __init__(self, project, parent=None):
        super(Widget, self).__init__(parent)

        if not project:
            return
        self.project = project

        # define ui components and global data
        self.view = MyGraphicsView(self.project)
        self.video_list = QListView()
        self.video_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.left = QFrame()
        self.right = QFrame()
        self.open_dialogs = []

        self.setup_ui()
        self.selected_videos = []

        self.video_list.setModel(QStandardItemModel())
        self.video_list.selectionModel().selectionChanged[QItemSelection,
                                                          QItemSelection].connect(self.selected_video_changed)
        self.video_list.doubleClicked.connect(self.video_triggered)
        for f in project.files:
            if f['type'] != 'video':
                continue
            item = QStandardItem(f['name'])
            item.setDropEnabled(False)
            self.video_list.model().appendRow(item)
        self.video_list.setCurrentIndex(self.video_list.model().index(0, 0))

    def video_triggered(self, index):
        filename = str(os.path.join(self.project.path, index.data(Qt.DisplayRole)) + '.npy')
        dialog = PlayerDialog(self.project, filename, self)
        dialog.show()
        self.open_dialogs.append(dialog)

    def setup_ui(self):
        vbox_view = QVBoxLayout()
        vbox_view.addWidget(self.view)
        self.view.vb.setCursor(Qt.CrossCursor)
        self.left.setLayout(vbox_view)

        vbox = QVBoxLayout()
        list_of_manips = pfs.get_list_of_project_manips(self.project)
        self.toolbutton = pfs.add_combo_dropdown(self, list_of_manips)
        self.toolbutton.activated.connect(self.refresh_video_list_via_combo_box)
        vbox.addWidget(self.toolbutton)
        vbox.addWidget(QLabel('Selection order determines concatenation order'))
        vbox.addWidget(QLabel('Drag and drop enabled'))
        self.video_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.video_list.setAcceptDrops(True)
        self.video_list.setDragEnabled(True)
        self.video_list.setDropIndicatorShown(True)
        self.video_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.video_list.setDefaultDropAction(Qt.MoveAction)
        self.video_list.setDragDropOverwriteMode(False)
        self.video_list.setStyleSheet('QListView::item { height: 26px; }')
        vbox.addWidget(self.video_list)
        hhbox = QHBoxLayout()
        concat_butt = QPushButton('Concatenate selected videos in selected order')
        hhbox.addWidget(concat_butt)
        vbox.addLayout(hhbox)
        vbox.addStretch()
        concat_butt.clicked.connect(self.concat_clicked)
        self.right.setLayout(vbox)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet('QSplitter::handle {background: #cccccc;}')
        splitter.addWidget(self.left)
        splitter.addWidget(self.right)
        hbox_global = QHBoxLayout()
        hbox_global.addWidget(splitter)
        self.setLayout(hbox_global)

    def refresh_video_list_via_combo_box(self, trigger_item=None):
        pfs.refresh_video_list_via_combo_box(self, trigger_item)

    def selected_video_changed(self, selected, deselected):
        pfs.selected_video_changed_multi(self, selected, deselected)

    def concat_clicked(self):
        paths = self.selected_videos
        if len(paths) < 2:
            qtutil.warning('Select multiple files to concatenate.')
            return
        frames = [fileloader.load_file(f) for f in paths]
        frames = np.concatenate(frames)
        # concat_name = '_'.join(filenames) + '.npy'
        # concat_path = os.path.join(self.project.path, concat_name)
        # First one has to take the name otherwise pfs.save_projects doesn't work
        filenames = [os.path.basename(path) for path in paths]
        pfs.save_project(paths[0], self.project, frames, 'concat_'+'_concat_'.join(filenames[1:]), 'video')
        pfs.refresh_all_list(self.project, self.video_list)

        # path = os.path.join(self.project.path, str(uuid.uuid4()) + 'Concat.npy')
        # np.save(path, frames)
        # self.project.files.append({
        #     'path': path,
        #     'type': 'video',
        #     'manipulations': 'concat',
        #     'source': filenames
        # })
        # self.project.save()


class MyPlugin:
    def __init__(self, project):
        self.name = 'Concatenation'
        self.widget = Widget(project)

    def run(self):
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(app.deleteLater)
    w = QMainWindow()
    w.setCentralWidget(Widget(None))
    w.show()
    app.exec_()
    sys.exit()