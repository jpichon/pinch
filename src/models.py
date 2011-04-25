from datetime import datetime
import os
import sqlite3

import settings

class Dent():

    def __init__(self, id='', author='', message='', tstamp=''):
        self.id = id
        self.author = author
        self.message = message
        self.tstamp = tstamp

    def tstamp_datetime(self):
        return datetime.strptime(self.tstamp[:-6], '%Y-%m-%dT%H:%M:%S')

    def __repr__(self):
        return u'#%d %s: %s (%s)' % (self.id,
                                     self.author,
                                     self.message,
                                     self.tstamp)

class DentLoader():

    def __init__(self):
        self.dents = []
        self.db_path = os.path.expanduser(settings.db_path)

        self.load_dents()

    def load_dents(self):
        if not os.path.exists(self.db_path):
            self._create_db()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("select * from dents order by tstamp desc")

        for row in c:
            d = Dent(id=row[0], author=row[1], message=row[2], tstamp=row[3])
            self.dents.append(d)

        c.close()
        conn.close()

    def _create_db(self):
        if not os.path.exists(os.path.expanduser(settings.data_path)):
            os.system('mkdir -p ' + os.path.expanduser(settings.data_path))

        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""create table dents
                      (id int, author text, message text, tstamp text)""")
            conn.commit()
            c.close()
            conn.close()

        if settings.debug:
            self.create_fake_dents()

    def create_fake_dents(self):
        dents = []

        dents.append(Dent(1, "bob", "I like cheese!", "2011-04-25T14:00:14+00:00"))
        dents.append(Dent(2, "alice", "Cool atmo at #RandomConference", "2011-04-25T13:54:00+00:00"))
        dents.append(Dent(3, "someonewitharidiculouslylongnameabcdefghijklmnopqrstuvwxyz", "lol", "2011-04-25T13:40:40+00:00"))
        dents.append(Dent(4, "Lort43", "An effort at writing a message that is one hundred and forty characters long, a message that is one hundred and forty characters long. Yes!", "2011-04-25T13:12:04+00:00"))

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        for dent in dents:
            c.execute("insert into dents values (?, ?, ?, ?)",
                      (dent.id, dent.author, dent.message, dent.tstamp))

        conn.commit()
        c.close()
        conn.close()

        return dents
