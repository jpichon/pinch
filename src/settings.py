import os

app_name = 'Pinch'

data_path = os.path.expanduser('~/.' + app_name.lower())
db_name = 'data.db'
db_path =  data_path + '/' + db_name

debug = False
log_file = data_path + '/log.txt'
log_level = 'DEBUG'

# TODO: For dev only
user = 'jpichon'
