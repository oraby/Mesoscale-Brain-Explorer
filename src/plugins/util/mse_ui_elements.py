#!/usr/bin/env python3
import os
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import QtCore
from . import fileloader

class Video_Selector:
    def __init__(self, project, view):
        self.project = project
        self.view = view

    def selected_video_changed(self, selected, deselected):
        if not selected.indexes():
            return

        for index in deselected.indexes():
            vidpath = str(os.path.join(self.project.path,
                                     index.data(Qt.DisplayRole))
                              + '.npy')
            self.selected_videos = [x for x in self.selected_videos if x != vidpath]
        for index in selected.indexes():
            vidpath = str(os.path.join(self.project.path,
                                     index.data(Qt.DisplayRole))
                              + '.npy')
        if vidpath not in self.selected_videos and vidpath != 'None':
            self.selected_videos = self.selected_videos + [vidpath]

        self.shown_video_path = str(os.path.join(self.project.path,
                                           selected.indexes()[0].data(Qt.DisplayRole))
                              + '.npy')
        frame = fileloader.load_reference_frame(self.shown_video_path)
        self.view.show(frame)