import logging
import os

import gtk
import hildon
from pango import WRAP_WORD_CHAR

from models import Dent, DentLoader
import settings

class DentBox():

    def __init__(self, dent, size_group=None):
        self.dent = dent
        self.size_group = size_group

        self.box = self.create_dent_box()

    def mark_as_read(self, widget):
        print "Marked as read until %s" % self.dent.id

    def create_mark_as_read_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH |
                               gtk.HILDON_SIZE_FINGER_HEIGHT,
                               hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_text("", "Mark all as read so far")
        button.connect("clicked", self.mark_as_read)

        image = gtk.image_new_from_stock(gtk.STOCK_APPLY, gtk.ICON_SIZE_BUTTON)
        button.set_image(image)
        button.set_image_position(gtk.POS_RIGHT)

        return button

    def create_message_box(self):
        msg_label = gtk.Label(self.dent.message)
        msg_label.set_line_wrap(True)
        msg_label.set_alignment(0, 0)

        time_label = gtk.Label()
        time_label.set_markup("<i>%s</i>" % self.dent.tstamp_datetime())
        time_label.set_alignment(0, 0)

        action_button = self.create_mark_as_read_button()

        hbox = gtk.HBox(False, 0)
        hbox.pack_start(time_label, False, False, 0)
        hbox.pack_end(action_button, False, False, 50)

        sep = gtk.HSeparator()
        sep.set_size_request(gtk.HILDON_SIZE_FULLSCREEN_WIDTH, 2)

        content_box = gtk.VBox(False, 10)
        content_box.pack_start(msg_label, False, False, 0)
        content_box.pack_start(hbox, False, False, 0)
        content_box.pack_end(sep, False, False, 0)

        return content_box

    def wrap_author_name(self):
        max_length = 20
        author = self.dent.author
        wrapped = ''
        for i in range(0, max_length, 10):
            wrapped += author[i:i+10] + "\n"
        if len(wrapped) > 20:
            wrapped = wrapped[:19] + '...'
        return wrapped

    def create_name_box(self):
        avatar = gtk.Image()
        avatar.set_from_icon_name(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_BUTTON)
        name_label = gtk.Label(self.wrap_author_name())
        name_label.set_line_wrap_mode(WRAP_WORD_CHAR)
        name_label.set_line_wrap(True)
        name_label.set_justify(gtk.JUSTIFY_CENTER)
        self.size_group.add_widget(name_label)

        label_box = gtk.HBox(False, 0)
        label_box.pack_start(name_label, False, False, 10)

        name_box = gtk.VBox(False, 0)
        name_box.pack_start(avatar, False, False, 0)
        name_box.pack_start(label_box, False, False, 0)

        return name_box

    def create_dent_box(self):
        dent_box = gtk.HBox(False, 0)
        dent_box.pack_start(self.create_name_box(), False, False, 2)
        dent_box.pack_start(self.create_message_box(), True, True, 0)

        padded_box = gtk.VBox(False)
        padded_box.pack_start(dent_box, False, False, 10)

        return padded_box

class TimelineView():

    size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

    def __init__(self):
        self.dents = self.fetch_dents()
        self.box = self.create_timeline()

    def create_timeline(self):
        vbox = gtk.VBox(False, 0)

        for dent in self.dents:
            dent = DentBox(dent, self.size_group)
            vbox.pack_start(dent.box, False, False, 0)

        return vbox

    def fetch_dents(self):
        loader = DentLoader()
        return loader.dents

def main():
    if not os.path.exists(os.path.expanduser(settings.data_path)):
            os.system('mkdir -p ' + os.path.expanduser(settings.data_path))

    logging.basicConfig(filename=os.path.expanduser(settings.log_file),
                        filemode='w',
                        level=logging.getLevelName(settings.log_level))

    gtk.set_application_name(settings.app_name)
    program = hildon.Program.get_instance()

    win = hildon.StackableWindow()
    win.set_title(settings.app_name)
    win.connect("destroy", gtk.main_quit, None)

    timeline = TimelineView()

    pannable_area = hildon.PannableArea()
    pannable_area.add_with_viewport(timeline.box)

    win.add(pannable_area)
    win.show_all()

    gtk.main()

if __name__ == '__main__':
    main()
