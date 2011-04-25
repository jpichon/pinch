class Dent():

    def __init__(self, id, author, message, tstamp):
        self.id = id
        self.author = author
        self.message = message
        self.tstamp = tstamp


def create_fake_dents():
    dents = []

    dents.append(Dent(1, "bob", "I like cheese!", "about 6 minutes ago"))
    dents.append(Dent(2, "alice", "Cool atmo at #RandomConference", "about 19 minutes ago"))
    dents.append(Dent(2, "someonewitharidiculouslylongnameabcdefghijklmnopqrstuvwxyz", "lol", "about 41 minutes ago"))
    dents.append(Dent(4, "Lort43", "An effort at writing a message that is one hundred and forty characters long, a message that is one hundred and forty characters long. Yes!", "about 1 hour ago"))

    return dents

