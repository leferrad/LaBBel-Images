#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A tool to label images and their bounding boxes associated for object detection applications

Adapted from: https://github.com/puzzledqs/BBox-Label-Tool
"""

from __future__ import division, print_function
from Tkinter import *
import tkMessageBox
from PIL import Image, ImageTk
import os
import json


# --- Constants used ---

class ImageConfiguration(object):
    # colors for the bboxes
    COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
    # width of line for the bboxes
    BBOX_WIDTH = 2
    # image sizes for the examples
    SIZE = 256, 256
    # supported image formats
    SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg']


class OutputConfiguration(object):
    CATEGORY_NAME = 'category_name'


# --- Main Class ---

class LabelTool(object):
    def __init__(self, master, input_dir, output_dir):
        # set up the main frame
        self.parent = master
        self.parent.title("LaBBelImages")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=FALSE, height=FALSE)

        # Handled paths
        self.input_directory = input_dir
        self.output_directory = output_dir

        # initialize global state
        self.imageDir = ''
        self.imageList = []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load

        self.categories = os.listdir(input_dir)
        assert len(self.categories) > 0, ValueError("The input folder '%s' must contain sub-folders with images!")
        self.category_variable = StringVar(master)
        self.category_variable.set(self.categories[0])  # default value

        self.category_label = Label(self.frame, text='Category:')
        self.category_label.grid(row=0, column=0, sticky=E)
        self.category_menu = OptionMenu(self.frame, self.category_variable, *tuple(self.categories))
        self.category_menu.grid(row=0, column=1, sticky=W+E)

        self.load_button = Button(self.frame, text="Load", command=self.loadCategories)
        self.load_button.grid(row=0, column=2, sticky=W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row=1, column=1, rowspan=4, sticky=W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text='Bounding boxes:')
        self.lb1.grid(row=1, column=2,  sticky=W+N)
        self.listbox = Listbox(self.frame, width = 22, height = 12)
        self.listbox.grid(row = 2, column = 2, sticky = N)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 3, column = 2, sticky = W+E+N)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 4, column = 2, sticky = W+E+N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=5, column=1, columnspan=2, sticky=W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # example pannel for illustration
        #self.egPanel = Frame(self.frame, border = 10)
        #self.egPanel.grid(row = 1, column = 0, rowspan = 5, sticky = N)
        #self.tmpLabel2 = Label(self.egPanel, text = "Examples:")
        #self.tmpLabel2.pack(side = TOP, pady = 5)
        #self.egLabels = []
        #for i in range(3):
        #    self.egLabels.append(Label(self.egPanel))
        #    self.egLabels[-1].pack(side = TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(4, weight=1)

        # for debugging
##        self.setImage()
##        self.loadDir()

    def _get_line_color(self):
        if len(self.bboxList) > 0:
            color = ImageConfiguration.COLORS[(len(self.bboxList)-1) % len(ImageConfiguration.COLORS)]
        else:
            color = ImageConfiguration.COLORS[0]  # Just pick a color
        return color

    def loadCategories(self):
        current_category = self.category_variable.get()

        # get image list
        self.imageDir = os.path.abspath(os.path.join(self.input_directory, current_category))
        self.imageList = [os.path.join(self.imageDir, fn) for fn in os.listdir(self.imageDir)
                          if fn.split('.')[-1] in ImageConfiguration.SUPPORTED_FORMATS]
        if len(self.imageList) == 0:
            print("No images found for the category '%s'! " % current_category +
                  "Recall that they should belong to the supported formats: %s" % str(ImageConfiguration.SUPPORTED_FORMATS))
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        self.loadImage()
        print('%d images loaded from %s' % (self.total, self.imageDir))

    def loadLabels(self):
        try:
            with open(self.labelfilename) as f:
                category_json_config = json.load(f)

                for val in category_json_config['values']:
                    bboxes = val['bounding_boxes']
                    for bbox in bboxes:
                        x1, y1, x2, y2 = bbox['left'], bbox['bottom'], bbox['right'], bbox['top']
                        self.bboxList.append(bbox)
                        line_width = ImageConfiguration.BBOX_WIDTH
                        line_color = self._get_line_color()
                        tmpId = self.mainPanel.create_rectangle(x1, y1, x2, y2, width=line_width, outline=line_color)
                        self.bboxIdList.append(tmpId)
                        self.listbox.insert(END, '(%d, %d) -> (%d, %d)' % (x1, y1, x2, y2))
                        self.listbox.itemconfig(len(self.bboxIdList)-1, fg=line_color)
            success = True

        except Exception as e:
            success = False

        return success

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width=max(self.tkimg.width(), 400), height=max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=NW)
        self.progLabel.config(text="%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            self.loadLabels()

    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' %len(self.bboxList))
            for bbox in self.bboxList:
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' %self.cur)

    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '(%d, %d) -> (%d, %d)' %(x1, y1, x2, y2))
            self.listbox.itemconfig(len(self.bboxIdList) - 1,
                                    fg=self._get_line_color())
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text='x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'],
                                                          event.x, event.y,
                                                          width=2,
                                                          outline=self._get_line_color())

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

##    def setImage(self, imagepath = r'test2.png'):
##        self.img = Image.open(imagepath)
##        self.tkimg = ImageTk.PhotoImage(self.img)
##        self.mainPanel.config(width = self.tkimg.width())
##        self.mainPanel.config(height = self.tkimg.height())
##        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)

if __name__ == '__main__':
    # 1) Ask for the input directory
    input_directory = raw_input('Please indicate the directory containing all the input images: ')
    while os.path.exists(input_directory) is False:
        input_directory = raw_input("The specified directory doesn't exist! Please try again: ")

    # 2) Ask for the output directory
    output_directory = raw_input('Please indicate the directory for the output generated: ')
    while os.path.exists(os.path.dirname(output_directory)) is False:  # At least, it should have a valid parent
        output_directory = raw_input("The specified directory doesn't exist! Please try again: ")

    if os.path.exists(output_directory) is False:
        print("Creating output directory '%s'..." % output_directory)
        os.mkdir(output_directory)  # Create the output directory if it doesn't exist

    # 3) Start application!
    root = Tk()
    tool = LabelTool(root, input_dir=input_directory, output_dir=output_directory)
    root.resizable(width=True, height=True)
    root.mainloop()
