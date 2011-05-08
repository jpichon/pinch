import logging
import sqlite3
import urllib
import xml.dom.minidom as minidom
import xml.etree.ElementTree as etree

from models import Notice
import settings

class NoSuchUserException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NoticeFetcher():

    MAX_NOTICES = 100

    def __init__(self, user, base_url='http://identi.ca'):
        self.logger = logging.getLogger('NoticeFetcher')
        self.user = user
        self.base_url = base_url

        self.conn = sqlite3.connect(settings.db_path)

        self.user_id = None
        self._load_user_id()
        self.since_id = None
        self._load_since_id()

    def get_user_id(self):
        if self.user_id is None:
            return self._load_user_id()
        else:
            return self.user_id

    def _load_user_id(self):
        c = self.conn.execute("select value from config where name=?",
                              ('user',))
        value = c.fetchone()

        if value is None or value[0] != self.user:
            self.user_id = self._fetch_user_id()

            if value is None:
                sql = "insert into config values (?, ?)"
                self.conn.execute(sql, ('user', self.user))
                self.conn.execute(sql, ('user_id', self.user_id))
            else:
                sql = "update config set value=? where name=?"
                self.conn.execute(sql, (self.user, 'user'))
                self.conn.execute(sql, (self.user_id, 'user_id'))

            self.conn.execute("delete from notices")
            self.conn.commit()
        else:
            c = self.conn.execute("select value from config where name=?",
                                  ('user_id',))
            self.user_id = c.fetchone()[0]

    def get_since_id(self):
        if self.since_id is not None:
            return self.since_id
        else:
            self._load_since_id

    def _load_since_id(self):
        sql = "select value from config where name=?"
        c = self.conn.execute(sql, ('since_id',))
        result = c.fetchone()

        if result is not None:
            self.since_id = result[0]
        else:
            sql = "insert into config values (?, ?)"
            self.conn.execute(sql, ('since_id', '0'))
            self.conn.commit()

    def update_since_id(self):
        sql = "select id from notices order by tstamp desc limit 1"
        c = self.conn.execute(sql)
        result = c.fetchone()

        if result is not None:
            sql = "update config set value=? where name=?"
            self.conn.execute(sql, (result[0], 'since_id'))
            self.conn.commit()
            self.since_id = result[0]

    def _fetch_user_id(self):
        url = '%s/api/statusnet/app/service/%s.xml' % (self.base_url, self.user)

        try:
            self.logger.debug('Fetching user feed %s' % url)
            response = urllib.urlopen(url)
            content = response.read()

            if "No such user" in content:
                raise NoSuchUserException("User %s doesn't exist" % self.user)

            dom = minidom.parseString(content)
            collections = dom.getElementsByTagName("collection")

            user_id = None
            for item in collections:
                if item.attributes.has_key('href'):
                    import re
                    m = re.search('(\d+)(?=\.atom$)',
                                  item.attributes['href'].value)
                    if m is not None:
                        user_id = m.group(0)
                        break

            return user_id

        except Exception, e:
            self.logger.error("Could not fetch user information: %s (%s)",
                              str(type(e)), e)
            raise Exception("Could not fetch user information: %s", e)

    def fetch(self):
        if self.since_id is None or self.since_id == 0:
            self.fetch_latest()
        else:
            self.fetch_since(self.since_id)

        self.update_since_id()

    def fetch_latest(self):
        user_id = self.get_user_id()
        url = '%s/api/statuses/home_timeline/%s.atom' % (self.base_url, user_id)

        if user_id is None:
            return

        try:
            self.logger.debug('Fetching notices feed %s' % url)
            response = urllib.urlopen(url)

            np = NoticeParser(response)
            notices = np.parse()

            self.store_notices(notices)

        except Exception, e:
            print type(e), e
            self.logger.error("Could not fetch notices from url %s: %s (%s)",
                              url, str(type(e)), e)

    def fetch_since(self, since_id):
        user_id = self.get_user_id()
        max_id = 0
        url = '%s/api/statuses/home_timeline/%s.atom?max_id=%s&since_id=%s'

        if user_id is None:
            return

        if since_id is None:
            return self.fetch_latest()

        current_url = ''
        retrieved = 0
        new_notices_count = 2

        while new_notices_count > 1 and retrieved < self.MAX_NOTICES:
            try:
                current_url = url % (self.base_url, user_id, max_id, since_id)
                self.logger.debug('Fetching notices feed %s' % current_url)
                response = urllib.urlopen(current_url)

                np = NoticeParser(response)
                notices = np.parse()
                self.store_notices(notices)

                new_notices_count = len(notices)
                if new_notices_count > 0:
                    max_id = notices[-1].id

                retrieved += new_notices_count

            except Exception, e:
                print type(e), e
                self.logger.error(
                    "Could not fetch notices from url %s: %s (%s)",
                    current_url,
                    str(type(e)),
                    e)

    def store_notices(self, notices):
        ids = self.get_existing_ids()
        if self.since_id != None:
            ids.append(self.since_id)

        for n in notices:
            if n.id not in ids:
                sql = """insert into notices
                          (id, author, avatar_url, message, tstamp)
                          values (?, ?, ?, ?, ?)"""
                self.conn.execute(sql, (n.id,
                                        n.author,
                                        n.avatar_url,
                                        n.message,
                                        n.tstamp))
        self.conn.commit()

    def get_existing_ids(self):
        ids = []

        c = self.conn.execute("SELECT id from notices")
        results = c.fetchall()
        for res in results:
            ids.append(res[0])

        return ids

class NoticeParser():

    ATOM = '{http://www.w3.org/2005/Atom}'
    MEDIA = '{http://purl.org/syndication/atommedia}'
    STATUSNET = '{http://status.net/schema/api/1/}'

    def __init__(self, response):
        self.logger = logging.getLogger('NoticeParser')
        self.response = response

    def parse(self):
        notices = []

        try:
            tree = etree.parse(self.response)
            root = tree.getroot()
            entries = root.findall(self.ATOM + 'entry')

            for entry in entries:
                n = self.parse_entry(entry)
                notices.append(n)

            return notices

        except Exception, e:
            self.logger.error("Could not parse notices: %s (%s)",
                              str(type(e)), e)
            raise e

    def parse_entry(self, entry):
        author_info = entry.find(self.ATOM + 'author')

        id = entry.find(self.STATUSNET + 'notice_info').attrib['local_id']
        author = author_info.find(self.ATOM + 'name').text
        tstamp = entry.find(self.ATOM + 'published').text
        message = entry.find(self.ATOM + 'title').text
        message = message.replace('&', '&amp;')

        avatar_url = ''
        for link in author_info.findall(self.ATOM + 'link'):
            if link.attrib['rel'] == 'avatar' \
                    and link.attrib[self.MEDIA + 'width'] == '48':
                avatar_url = link.attrib['href']

        return Notice(id, author, message, tstamp, avatar_url)

if __name__ == '__main__':
    nf = NoticeFetcher(settings.user)
    nf.fetch()
