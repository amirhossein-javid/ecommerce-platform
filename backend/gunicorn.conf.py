import os

wsgi_app = "config.wsgi:application"
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(t)s "%(m)s %(U)s %(H)s" %(s)s %(B)s %(L)s'

timeout = 30
graceful_timeout = 30
