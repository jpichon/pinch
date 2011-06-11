import logging
import os
import sqlite3
from urllib import urlretrieve

import gtk
import hildon
from pango import WRAP_WORD_CHAR

from models import Notice, NoticeLoader
from identica import NoticeFetcher, UserFetcher, NoSuchUserException
import settings

class NoticeBox():

    read_markup = '<span foreground="#808080">%s</span>'
    hilight_markup = '<span foreground="#FDD017">%s</span>'

    def __init__(self, notice, parent, previous=None, size_group=None):
        self.notice = notice
        self.parent = parent
        self.previous = previous
        self.size_group = size_group

        self.box = self.create_notice_box()

    def highlight_action(self, widget, event):
        if self.notice.highlighted:
            self.notice.highlighted = False
            sql = "update notices set highlighted = 0 where id=?"
        else:
            self.notice.highlighted = True
            sql = "update notices set highlighted = 1 where id=?"

        conn = sqlite3.connect(settings.db_path)
        conn.execute(sql, (self.notice.id,))
        conn.commit()
        conn.close()

        self.redraw()

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
            self.redraw()

            if self.previous is not None:
                self.previous.redraw_all_as_read()

    def redraw(self):
        self.box.remove(self.box.get_children()[0])

        notice_box = gtk.HBox(False, 0)
        notice_box.pack_start(self.create_name_box(), False, False, 2)
        notice_box.pack_start(self.create_message_box(), True, True, 0)

        self.box.pack_start(notice_box, False, False, 10)
        self.box.show_all()

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

        if self.notice.highlighted:
            msg_label.set_markup(self.hilight_markup % msg_label.get_label())
            time_label.set_markup(self.hilight_markup % time_label.get_label())
        elif self.notice.read:
            msg_label.set_markup(self.read_markup % msg_label.get_label())
            time_label.set_markup(self.read_markup % time_label.get_label())

        if not self.notice.read:
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
        avatar = self.load_avatar()
        name_label = gtk.Label(self.wrap_author_name())
        name_label.set_line_wrap_mode(WRAP_WORD_CHAR)
        name_label.set_line_wrap(True)
        name_label.set_justify(gtk.JUSTIFY_CENTER)
        self.size_group.add_widget(name_label)

        label_box = gtk.HBox(False, 0)
        label_box.pack_start(name_label, False, False, 10)

        if self.notice.highlighted:
            name_label.set_markup(self.hilight_markup % name_label.get_label())
        elif self.notice.read:
            name_label.set_markup(self.read_markup % name_label.get_label())

        name_box = gtk.VBox(False, 0)

        if self.notice.highlighted:
            image = self.get_highlighted_icon()
            name_box.pack_start(image, False, False, 10)

        name_box.pack_start(avatar, False, False, 0)
        name_box.pack_start(label_box, False, False, 0)

        event_box = gtk.EventBox()
        event_box.add(name_box)
        event_box.connect('button-press-event', self.highlight_action)

        return event_box

    def load_avatar(self):
        img_path = settings.cache_path + '/%s.png' % self.notice.author

        if not os.path.exists(settings.cache_path):
            os.makedirs(settings.cache_path)

        if not os.path.exists(img_path):
            if self.notice.avatar_url:
                urlretrieve(self.notice.avatar_url, img_path)

        avatar = gtk.Image()
        avatar.set_from_file(img_path)

        return avatar

    def get_highlighted_icon(self):
        current_path = os.path.dirname(__file__)
        img_path = os.path.join(os.path.dirname(__file__), '../data/star.png')

        highlight = gtk.Image()
        highlight.set_from_file(img_path)
        return highlight

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

        if len(self.notices) == 0:
            label = gtk.Label("No new notices.")
            vbox.pack_start(label)

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
            if notice_box.notice.read and not notice_box.notice.highlighted:
                notice_box.box.destroy()
        self.notice_boxes[:] = [nb for nb in self.notice_boxes
                                if not nb.notice.read
                                or notice_box.notice.highlighted]

class Setup():

    def __init__(self):
        self.logger = logging.getLogger('Setup')

        self.create_app_directory()
        self.create_db()

    def create_app_directory(self):
        if not os.path.exists(settings.data_path):
            self.logger.info('Creating app directory')
            os.makedirs(settings.data_path)

    def create_db(self):
        if not os.path.exists(settings.data_path):
            self.logger.info('Creating app path')
            os.makedirs(settings.data_path)

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
            conn.execute("create table config (name text unique, value text)")
            conn.commit()
            conn.close()

def remove_read_notices(widget, timeline):
    sql = "delete from notices where read = 1 and highlighted = 0"
    conn = sqlite3.connect(settings.db_path)
    conn.execute(sql)
    conn.commit()
    conn.close()

    timeline.remove_read_notices()
    hildon.hildon_banner_show_information(widget, '', "Removed read notices")

def jump_to_unread(widget, pannable_area, timeline):
    pannable_area.scroll_to_child(timeline.first_unread)

def save_settings(widget, window, parent, entry):
    user = entry.get_text()

    conn = sqlite3.connect(settings.db_path)
    c = conn.execute("select value from config where name=?", ('user',))
    current_user = c.fetchone()

    if current_user is not None and current_user[0] == user:
        window.destroy()
        return

    # Get user id
    try:
        uf = UserFetcher(user)
        user_id = uf.user_id

        sql = "delete from config where name=? or name=? or name=?"
        conn.execute(sql, ('user', 'user_id', 'since_id'))
        sql = "insert into config values (?, ?)"
        conn.execute(sql, ('user', user))
        sql = "insert into config values (?, ?)"
        conn.execute(sql, ('user_id', user_id))
        sql = "delete from notices"
        conn.execute(sql)
        conn.commit()
        conn.close()

        hildon.hildon_banner_show_information(parent, '', "Settings saved.")

        window.destroy()
    except NoSuchUserException, nse:
        message = "User does not exist."
        hildon.hildon_banner_show_information(parent, '', message)
    except Exception, e:
        logging.error("Error getting user info | %s %s" % (str(type(e)), e))
        message = "Couldn't get user information."
        hildon.hildon_banner_show_information(parent, '', message)

def configure(widget, win):
    window = hildon.StackableWindow()
    window.set_title(settings.app_name + " - Settings")

    conn = sqlite3.connect(settings.db_path)
    c = conn.execute("select value from config where name=?", ('user',))
    user = c.fetchone()
    conn.close()

    label = gtk.Label("Username")
    entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
    entry.set_max_length(64)
    if user is not None:
        entry.set_text(user[0])

    save_button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH |
                                gtk.HILDON_SIZE_FINGER_HEIGHT,
                                hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
    save_button.set_text("Save new settings", "")
    save_button.connect("clicked", save_settings, window, win, entry)

    uname_box = gtk.HBox(False, 0)
    uname_box.pack_start(label, False, False, 20)
    uname_box.pack_start(entry, True, True, 10)

    save_box = gtk.HBox(False, 0)
    save_box.pack_start(save_button, True, False, 0)

    vbox = gtk.VBox(False, 0)
    vbox.pack_start(uname_box, False, False, 20)
    vbox.pack_start(save_box, False, False, 0)

    window.add(vbox)
    window.show_all()

def create_menu(win, pannable_area, timeline):
    menu = hildon.AppMenu()

    rm_read_button = gtk.Button('Remove read')
    rm_read_button.connect("clicked", remove_read_notices, timeline)
    jump_unread_button = gtk.Button('Jump to unread')
    jump_unread_button.connect("clicked",
                               jump_to_unread,
                               pannable_area,
                               timeline)
    settings_button = gtk.Button("Settings")
    settings_button.connect("clicked", configure, win)

    menu.append(rm_read_button)
    menu.append(jump_unread_button)
    menu.append(settings_button)
    menu.show_all()

    return menu

def main():
    Setup()

    logging.basicConfig(filename=os.path.expanduser(settings.log_file),
                        filemode='w',
                        format='%(asctime)s - %(levelname)s:%(name)s:%(message)s',
                        level=logging.getLevelName(settings.log_level))

    gtk.set_application_name(settings.app_name)
    program = hildon.Program.get_instance()

    win = hildon.StackableWindow()
    win.set_title(settings.app_name)
    win.connect("destroy", gtk.main_quit, None)

    hildon.hildon_gtk_window_set_progress_indicator(win, 1)
    win.show_all()

    pannable_area = hildon.PannableArea()

    conn = sqlite3.connect(settings.db_path)
    c = conn.execute("select value from config where name=?", ('user',))
    user = c.fetchone()
    conn.close()

    if user is None:
        message = "No user set up in database."
        logging.error("%s" % message)
        message += " Please go to Settings and enter a username."
        info = hildon.hildon_note_new_information(win, message)
        gtk.Dialog.run(info)

    try:
        if user is not None:
            user = user[0]
            logging.info("Loading notices for %s" % user)
            nf = NoticeFetcher(user)
            nf.fetch()
    except Exception, e:
        message = "Problem loading notices. Is the network down?"
        logging.error("%s | %s" % (message, e))
        hildon.hildon_banner_show_information(pannable_area, '', message)

    timeline = TimelineView()
    pannable_area.add_with_viewport(timeline.box)

    win.set_app_menu(create_menu(win, pannable_area, timeline))
    win.add(pannable_area)
    # scroll_to_child doesn't work if show_all() called twiced without hiding
    win.hide_all()
    win.show_all()

    hildon.hildon_gtk_window_set_progress_indicator(win, 0)
    pannable_area.scroll_to_child(timeline.first_unread)

    gtk.main()

if __name__ == '__main__':
    main()
