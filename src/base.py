import logging
import os
import sqlite3

import gtk
import hildon
from pango import WRAP_WORD_CHAR

from models import Notice, NoticeLoader
from identica import NoticeFetcher
import settings

class NoticeBox():

    read_markup = '<span foreground="#808080">%s</span>'

    def __init__(self, notice, parent, previous=None, size_group=None):
        self.notice = notice
        self.parent = parent
        self.previous = previous
        self.size_group = size_group

        self.box = self.create_notice_box()

    def mark_all_as_read(self, widget):
        sql = "update notices set read = 1 where tstamp <= ?"
        conn = sqlite3.connect(settings.db_path)
        conn.execute(sql, (self.notice.tstamp,))
        conn.commit()
        conn.close()

        self.redraw_all_as_read()
        self.parent.find_first_unread()

    def redraw_all_as_read(self):
        if not self.notice.read:
            self.notice.read = True
            self.box.remove(self.box.get_children()[0])

            notice_box = gtk.HBox(False, 0)
            notice_box.pack_start(self.create_name_box(), False, False, 2)
            notice_box.pack_start(self.create_message_box(), True, True, 0)

            self.box.pack_start(notice_box, False, False, 10)
            self.box.show_all()

            if self.previous is not None:
                self.previous.redraw_all_as_read()

    def create_mark_as_read_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH |
                               gtk.HILDON_SIZE_FINGER_HEIGHT,
                               hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_text("", "Mark all as read so far")
        button.connect("clicked", self.mark_all_as_read)

        image = gtk.image_new_from_stock(gtk.STOCK_APPLY, gtk.ICON_SIZE_BUTTON)
        button.set_image(image)
        button.set_image_position(gtk.POS_RIGHT)

        return button

    def create_message_box(self):
        msg_label = gtk.Label(self.notice.message)
        msg_label.set_line_wrap(True)
        msg_label.set_alignment(0, 0)

        time_label = gtk.Label()
        time_label.set_markup("<i>%s</i>" % self.notice.tstamp_datetime())
        time_label.set_alignment(0, 0)

        action_button = self.create_mark_as_read_button()

        hbox = gtk.HBox(False, 0)
        hbox.pack_start(time_label, False, False, 0)

        if self.notice.read:
            msg_label.set_markup(self.read_markup % msg_label.get_label())
            time_label.set_markup(self.read_markup % time_label.get_label())
        else:
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
        author = self.notice.author
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

        if self.notice.read:
            name_label.set_markup(self.read_markup % name_label.get_label())

        name_box = gtk.VBox(False, 0)
        name_box.pack_start(avatar, False, False, 0)
        name_box.pack_start(label_box, False, False, 0)

        return name_box

    def create_notice_box(self):
        notice_box = gtk.HBox(False, 0)
        notice_box.pack_start(self.create_name_box(), False, False, 2)
        notice_box.pack_start(self.create_message_box(), True, True, 0)

        padded_box = gtk.VBox(False)
        padded_box.pack_start(notice_box, False, False, 10)

        return padded_box

class TimelineView():

    size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
    first_unread = None

    def __init__(self):
        self.notice_boxes = []
        self.notices = self.fetch_notices()
        self.box = self.create_timeline()

        if self.first_unread is None:
            if len(self.notice_boxes) > 0:
                self.first_unread = self.notice_boxes[-1].box
            else:
                self.first_unread = self.box

    def create_timeline(self):
        vbox = gtk.VBox(False, 0)

        found = False
        previous = None

        for notice in self.notices:
            notice_box = NoticeBox(notice=notice,
                                   parent=self,
                                   previous=previous,
                                   size_group=self.size_group)
            vbox.pack_start(notice_box.box, False, False, 0)

            previous = notice_box
            self.notice_boxes.append(notice_box)

            if not found and notice.read == False:
                self.first_unread = notice_box.box
                found = True

        return vbox

    def fetch_notices(self):
        loader = NoticeLoader()
        return loader.notices

    def find_first_unread(self):
        for notice_box in self.notice_boxes:
            if not notice_box.notice.read:
                self.first_unread = notice_box.box
                break
        return None

    def remove_read_notices(self):
        for notice_box in self.notice_boxes:
            if notice_box.notice.read:
                notice_box.box.destroy()
        self.notice_boxes[:] = [nb for nb in self.notice_boxes
                                if not nb.notice.read]

class Setup():

    def __init__(self):
        self.logger = logging.getLogger('Setup')

        self.create_app_directory()
        self.create_db()

    def create_app_directory(self):
        if not os.path.exists(os.path.expanduser(settings.data_path)):
            os.system('mkdir -p ' + os.path.expanduser(settings.data_path))

    def create_db(self):
        if not os.path.exists(os.path.expanduser(settings.data_path)):
            self.logger.info('Creating app path')
            os.system('mkdir -p ' + os.path.expanduser(settings.data_path))

        if not os.path.exists(settings.db_path):
            self.logger.info('Create app database')
            conn = sqlite3.connect(settings.db_path)
            conn.execute("""create table notices
                      (id int unique,
                       author text,
                       message text,
                       tstamp text,
                       avatar_url text default '',
                       highlighted int default 0,
                       read int default 0)""")
            conn.execute("create table config (name text, value text)")
            conn.commit()
            conn.close()

            if settings.debug:
                self.create_fake_notices()

    def create_fake_notices(self):
        self.logger.debug("Creating fake notices")
        notices = []

        notices.append(Notice(1, "bob", "I like cheese!", "2011-04-25T14:00:14+00:00"))
        notices.append(Notice(2, "alice", "Cool atmo at #RandomConference", "2011-04-25T13:54:00+00:00"))
        notices.append(Notice(3, "someonewitharidiculouslylongnameabcdefghijklmnopqrstuvwxyz", "lol", "2011-04-25T13:40:40+00:00"))
        notices.append(Notice(4, "Lort43", "An effort at writing a message that is one hundred and forty characters long, a message that is one hundred and forty characters long. Yes!", "2011-04-25T13:12:04+00:00", None, False, True))

        conn = sqlite3.connect(settings.db_path)

        for notice in notices:
            conn.execute("insert into notices values (?, ?, ?, ?, ?, ?, ?)",
                         (notice.id, notice.author, notice.message,
                          notice.tstamp, '', 0, notice.read))

        conn.commit()
        conn.close()

        return notices

def remove_read_notices(widget, timeline):
    hildon.hildon_banner_show_information(widget, '', "Removing read notices")
    sql = "delete from notices where read = 1 and highlighted = 0"
    conn = sqlite3.connect(settings.db_path)
    conn.execute(sql)
    conn.commit()
    conn.close()
    timeline.remove_read_notices()

def jump_to_unread(widget, pannable_area, timeline):
    pannable_area.scroll_to_child(timeline.first_unread)

def create_menu(pannable_area, timeline):
    menu = hildon.AppMenu()

    rm_read_button = gtk.Button('Remove read')
    rm_read_button.connect("clicked", remove_read_notices, timeline)
    jump_unread_button = gtk.Button('Jump to unread')
    jump_unread_button.connect("clicked",
                               jump_to_unread,
                               pannable_area,
                               timeline)

    menu.append(rm_read_button)
    menu.append(jump_unread_button)
    menu.show_all()

    return menu

def main():
    Setup()

    logging.basicConfig(filename=os.path.expanduser(settings.log_file),
                        filemode='w',
                        level=logging.getLevelName(settings.log_level))

    gtk.set_application_name(settings.app_name)
    program = hildon.Program.get_instance()

    win = hildon.StackableWindow()
    win.set_title(settings.app_name)
    win.connect("destroy", gtk.main_quit, None)

    # TODO: settings.user is hardcoded for now
    nf = NoticeFetcher(settings.user)
    nf.fetch()

    timeline = TimelineView()

    pannable_area = hildon.PannableArea()
    pannable_area.add_with_viewport(timeline.box)

    win.set_app_menu(create_menu(pannable_area, timeline))
    win.add(pannable_area)
    win.show_all()

    pannable_area.scroll_to_child(timeline.first_unread)

    gtk.main()

if __name__ == '__main__':
    main()
