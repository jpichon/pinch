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


class DentFetcher():

    def __init__(self, user, base_url='http://identi.ca'):
        self.logger = logging.getLogger('DentFetcher')
        self.user = user
        self.base_url = base_url

        self.conn = sqlite3.connect(settings.db_path)

        self.user_id = None
        self._load_user_id()

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
            else:
                sql = "update config set name=?, value=?"

            self.conn.execute(sql, ('user', self.user))
            self.conn.commit()
            self.conn.execute(sql, ('user_id', self.user_id))
            self.conn.commit()
        else:
            c = self.conn.execute("select value from config where name=?",
                                  ('user_id',))
            self.user_id = c.fetchone()[0]

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
        user_id = self.get_user_id()
        url = '%s/api/statuses/home_timeline/%s.atom' % (self.base_url, user_id)

        if user_id is None:
            return

        try:
            self.logger.debug('Fetching notices feed %s' % url)
            response = urllib.urlopen(url)

            np = NoticeParser(response)
            notices = np.parse()

            for n in notices:
                sql = """insert into notices
                          (id, author, avatar_url, message, tstamp)
                          values (?, ?, ?, ?, ?)"""
                self.conn.execute(sql, (n.id, n.author, n.avatar_url, n.message, n.tstamp))
            self.conn.commit()
        except Exception, e:
            print type(e), e
            self.logger.error("Could not fetch notices from url %s: %s (%s)",
                              url, str(type(e)), e)

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
    df = DentFetcher(settings.user)
    df.fetch()
