# Gunicorn configuration
bind = "0.0.0.0:10000"  # Render expects this port
workers = 2
threads = 2
timeout = 120
