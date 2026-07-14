# wsgi.py - Entry point for Gunicorn on Render

from app import app

if __name__ == "__main__":
    app.run()
