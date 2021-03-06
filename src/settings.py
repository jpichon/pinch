import os

app_name = 'Pinch'

data_path = os.path.expanduser('~/.' + app_name.lower())
db_name = 'data.db'
db_path =  data_path + '/' + db_name

cache_path = os.path.expanduser('~/.cache/' + app_name.lower())

log_file = data_path + '/log.txt'
log_level = 'INFO'
log_format = '%(asctime)s - %(levelname)s:%(name)s:%(message)s'
