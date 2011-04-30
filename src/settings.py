import os

app_name = 'Pinch'

data_path = os.path.expanduser('~/.' + app_name)
db_name = 'data.db'
db_path =  data_path + '/' + db_name

debug = True
log_file = data_path + '/log.txt'
log_level = 'DEBUG'

# TODO: For dev only
user = 'jpichon'
