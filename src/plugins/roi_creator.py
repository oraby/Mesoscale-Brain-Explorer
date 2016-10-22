# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import sys
import numpy as np

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from .util.mygraphicsview import MyGraphicsView
from .util import fileloader
from .util import project_functions as pfs

sys.path.append('..')
import qtutil
import uuid

#todo: Explain this model to me in depth
class RoiItemModel(QAbstractListModel):
    textChanged = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super(RoiItemModel, self).__init__(parent)
        self.rois = []

    def appendRoi(self, name):
        self.rois.append(name)
        row = len(self.rois) - 1
        self.dataChanged.emit(self.index(row), self.index(row))

    def edit_roi_name(self, name, index):
        self.rois.append(name)
        row = len(self.rois) - 1
        self.dataChanged.emit(self.index(row), self.index(row))

    def rowCount(self, parent):
        return len(self.rois)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.rois[index.row()]
        return

    def setData(self, index, value, role):
      if role == Qt.EditRole:
        value = str(value)
        if value in self.rois[index.row()]:
          pass
        elif value in self.rois:
          qtutil.critical('Roi name taken.')
        else:
          self.textChanged.emit(self.rois[index.row()], value)
          self.rois[index.row()] = value
        return True
      return super(RoiItemModel, self).setData(index, value, role)

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def removeRow(self, roi_to_remove):
        for roi in self.rois:
            if roi == roi_to_remove:
                del roi
                break

class Widget(QWidget):
  def __init__(self, project, parent=None):
    super(Widget, self).__init__(parent)

    if not project:
      return
    self.project = project
    self.setup_ui()

    self.selected_videos = []

    self.listview.setModel(QStandardItemModel())
    self.listview.selectionModel().selectionChanged[QItemSelection,
      QItemSelection].connect(self.selected_video_changed)
    for f in project.files:
      if f['type'] != 'video':
        continue
      self.listview.model().appendRow(QStandardItem(f['name']))
    self.listview.setCurrentIndex(self.listview.model().index(0, 0))

    model = RoiItemModel() 
    model.textChanged.connect(self.roi_item_changed)
    self.roi_list.setModel(model)
    self.roi_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    # A flag to see whether selected_roi_changed is being entered for the first time
    self.selected_roi_changed_flag = 0
    self.roi_list.selectionModel().selectionChanged[QItemSelection,
      QItemSelection].connect(self.selected_roi_changed)
    roi_names = [f['name'] for f in project.files if f['type'] == 'roi']
    for roi_name in roi_names:
      model.appendRoi(roi_name)
    #self.roi_list.setCurrentIndex(model.index(0, 0))
    self.view.vb.roi_placed.connect(self.update_project_roi)

  def roi_item_edited(self, item):
    new_name = item.text()
    prev_name = item.data(Qt.UserRole)
    # disconnect and reconnect signal
    self.roi_list.itemChanged.disconnect()
    item.setData(new_name, Qt.UserRole)
    self.roi_list.model().itemChanged[QStandardItem.setData].connect(self.roi_item_edited)

  def setup_ui(self):
    hbox = QHBoxLayout()
  
    self.view = MyGraphicsView(self.project)
    hbox.addWidget(self.view)

    vbox = QVBoxLayout()
    vbox.addWidget(QLabel('Choose video:'))
    self.listview = QListView()
    self.listview.setSelectionMode(QAbstractItemView.ExtendedSelection)
    self.listview.setStyleSheet('QListView::item { height: 26px; }')
    vbox.addWidget(self.listview)

    pb = QPushButton('Create poly ROI')
    pb.clicked.connect(self.create_roi)
    vbox.addWidget(pb)
    pb = QPushButton('Crop to poly ROI for selected files')
    pb.clicked.connect(self.crop_clicked)
    vbox.addWidget(pb)
    pb = QPushButton('Delete selected ROIs')
    pb.clicked.connect(self.delete_roi)
    vbox.addWidget(pb)

    vbox.addWidget(qtutil.separator())

    vbox2 = QVBoxLayout()
    w = QWidget()
    w.setLayout(vbox2)
    vbox.addWidget(w)

    vbox.addWidget(qtutil.separator())
    vbox.addWidget(QLabel('ROIs'))
    self.roi_list = QListView()
    vbox.addWidget(self.roi_list)

    hbox.addLayout(vbox)
    hbox.setStretch(0, 1)
    hbox.setStretch(1, 0)
    self.setLayout(hbox)

  def remove_all_rois(self):
    rois = self.view.vb.rois[:]
    for roi in rois:
      if not roi.isSelected:
        self.view.vb.selectROI(roi)
      self.view.vb.removeROI()

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

  def selected_roi_changed(self, selection):
    # if self.selected_roi_changed_flag == 0:
    #   self.selected_roi_changed_flag = self.selected_roi_changed_flag + 1
    #   return
    if not selection.indexes() or self.view.vb.drawROImode:
      return
    self.remove_all_rois()

    # todo: re-explain how you can figure out to go from commented line to uncommented line
    # rois_selected = str(selection.indexes()[0].data(Qt.DisplayRole).toString())
    rois_selected = [str(self.roi_list.selectionModel().selectedIndexes()[x].data(Qt.DisplayRole))
                     for x in range(len(self.roi_list.selectionModel().selectedIndexes()))]
    rois_in_view = [self.view.vb.rois[x].name for x in range(len(self.view.vb.rois))]
    rois_to_add = [x for x in rois_selected if x not in rois_in_view]
    for roi_to_add in rois_to_add:
      self.view.vb.loadROI([self.project.path + '/' + roi_to_add + '.roi'])

  def roi_item_changed(self, prev_name, new_name):
    # todo: Why not pass the paramaters as strings? Is it important to have them in this format?
    if prev_name == '':
      raise ValueError("The ROI already has no name... you monster")
    prev_name_str = str(prev_name)
    new_name_str = str(new_name)
    self.remove_all_rois()
    old_path = self.project.path + '/' + str(prev_name_str) + '.roi'
    self.view.vb.loadROI([old_path])
    roi = self.view.vb.rois[0]
    roi.setName(str(new_name_str))
    for i in range(len(self.project.files)):
      if self.project.files[i]['path'].endswith(str(prev_name_str) + '.roi'):
        os.rename(self.project.files[i]['path'], self.project.files[i]['path'].replace(prev_name_str, new_name_str))
        self.project.files[i]['path'] = self.project.files[i]['path'].replace(prev_name_str, new_name_str)
        self.project.files[i]['name'] = new_name_str
    self.project.save()

  def update_project_roi(self, roi):
    name = roi.name
    if not name:
      raise ValueError('ROI has no name')
    if self.view.vb.drawROImode:
      return

    roi.setName(name)
    path = os.path.join(self.project.path, name + '.roi')
    self.view.vb.saveROI(path)
    # TODO check if saved, notifiy user of save and save location (really needed if they can simply export?)
    if path not in [self.project.files[x]['path'] for x in range(len(self.project.files))]:
      self.project.files.append({
        'path': path,
        'type': 'roi',
        'source_video': self.shown_video_path,
        'name': name
      })
    else:
      for i, file in enumerate(self.project.files):
        if file['path'] == path:
          self.project.files[i]['source_video'] = self.shown_video_path
    self.project.save()

    roi_names = [f['name'] for f in self.project.files if f['type'] == 'roi']
    for roi_name in roi_names:
      if roi_name not in self.roi_list.model().rois:
        self.roi_list.model().appendRoi(roi_name)

  def create_roi(self):
    self.view.vb.addPolyRoiRequest()

  def delete_roi(self):
    rois_selected = [str(self.roi_list.selectionModel().selectedIndexes()[x].data(Qt.DisplayRole))
                     for x in range(len(self.roi_list.selectionModel().selectedIndexes()))]
    if rois_selected == None:
      return
    rois_dict = [self.project.files[x] for x in range(len(self.project.files))
                 if (self.project.files[x]['type'] == 'roi' and self.project.files[x]['name'] in rois_selected)]
    self.project.files = [self.project.files[x] for x in range(len(self.project.files))
                          if self.project.files[x] not in rois_dict]
    self.project.save()
    self.view.vb.setCurrentROIindex(None)

    for roi_to_remove in [rois_dict[x]['name'] for x in range(len(rois_dict))]:
      self.roi_list.model().removeRow(roi_to_remove)

  def crop_clicked(self):
      progress = QProgressDialog('Cropping for selection', 'Abort', 0, 100, self)
      progress.setAutoClose(True)
      progress.setMinimumDuration(0)

      def callback(x):
          progress.setValue(x * 100)
          QApplication.processEvents()

      self.crop_ROI(callback)

  def crop_ROI(self, progress_callback):
    for i, video_path in enumerate(self.selected_videos):
      progress_callback(i / len(self.selected_videos))
      frames = fileloader.load_file(video_path)
      # Return if there is no image or rois in view
      if self.view.vb.img == None or len(self.view.vb.rois) == 0:
        print("there is no image or rois in view ")
        return

      # swap axis for aligned_frames
      frames_swap = np.swapaxes(np.swapaxes(frames, 0, 1), 1, 2)
      # Collect ROI's and combine
      numROIs = len(self.view.vb.rois)
      arrRegion_masks = []
      for i in xrange(numROIs):
        roi = self.view.vb.rois[i]
        arrRegion_mask = roi.getROIMask(frames_swap, self.view.vb.img, axes=(0, 1))
        arrRegion_masks.append(arrRegion_mask)

      combined_mask = np.sum(arrRegion_masks, axis=0)
      # Make all rows with all zeros na
      # todo: figure out where zeros are converted to na. In BMD it isn't here...
      # combined_mask[(combined_mask == 0)] = None
      self.mask = combined_mask
      # TODO: save mask as well
      # #combined_mask.astype(dtype_string).tofile(os.path.expanduser('/Downloads/')+"mask.raw")
      # print("mask saved to " + os.path.expanduser('/Downloads/')+"mask.raw")

      # In imageJ - Gap Between Images The number of bytes from the end of one image to the beginning of the next.
      # Set this value to width × height × bytes-per-pixel × n to skip n images for each image read. So use 4194304
      # Dont forget to set Endian value and set to 64 bit
      roi_frames = (frames * combined_mask[np.newaxis, :, :])

      # todo: solve issue where rerunning this will overwrite any previous 'roi.npy'
      # path = os.path.join(self.project.path, 'roi' + '.npy')
      progress_callback(1)
      pfs.save_project(video_path, self.project, roi_frames, 'crop', 'video')

class MyPlugin:
  def __init__(self, project=None):
    self.name = 'Create ROIs'
    self.widget = Widget(project)
  
  def run(self):
    pass
