from datetime import datetime
import logging
import sqlite3

import settings

class Notice():

    def __init__(self, id=0, author='', message='', tstamp='', avatar_url=None,
                 highlighted=False, read=False):
        self.id = int(id) # Notice id
        self.author = author
        self.avatar_url = None
        self.message = message
        self.tstamp = tstamp
        self.highlighted = highlighted
        self.read = read

    def tstamp_datetime(self):
        return datetime.strptime(self.tstamp[:-6], '%Y-%m-%dT%H:%M:%S')

    def __str__(self):
        notice = '#%d %s: %s (%s)' % (self.id,
                                      self.author,
                                      self.message,
                                      self.tstamp)
        return unicode(notice).encode("utf-8")

class NoticeLoader():

    def __init__(self):
        self.notices = []
        self.logger = logging.getLogger('NoticeLoader')

        self.load_notices()

    def load_notices(self):
        sql = """select id, author, avatar_url, message, tstamp,
                        highlighted, read
                 from notices
                 order by tstamp"""
        conn = sqlite3.connect(settings.db_path)
        c = conn.execute(sql)

        for row in c:
            d = Notice(id=row[0],
                       author=row[1],
                       avatar_url=row[2],
                       message=row[3],
                       tstamp=row[4],
                       highlighted=row[5],
                       read=row[6])
            self.logger.debug('Notice fetched from db: ' + str(d))
            self.notices.append(d)

        conn.close()
