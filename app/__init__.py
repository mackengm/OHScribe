# Debugging is per https://stackoverflow.com/questions/17309889/how-to-debug-a-flask-app

import os
import logging
from logging.handlers import RotatingFileHandler
from os import environ
from flask_bootstrap import Bootstrap
from flask import Flask, flash
from config import Config
from flask_debugtoolbar import DebugToolbarExtension  # for debugging

# Constants/secrets moved to .master.env, accessed using os.environ below

# Initialize the app... populate app.config[]
app = Flask(__name__)
app.config.from_object(Config)
host = environ.get('OHSCRIBE_HOST_ADDR')
app.static_folder = 'static'
app.debug = True                        # for debugging...set False to turn off the DebugToolbarExtension

toolbar = DebugToolbarExtension(app)    # for debugging

# From The Flask Mega-Tutorial Part VII: Error Handling
if not os.path.exists('logs'):
  os.mkdir('logs')
file_handler = RotatingFileHandler('logs/ohscribe.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
  '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))

file_handler.setLevel(logging.DEBUG)    # set to INFO for less verbose output
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)      # set to INFO for less verbose output

app.logger.debug('OHScribe startup.')

# Moved to config.py...
#
# app.config['UPLOAD_FOLDER'] = environ.get('OHSCRIBE_UPLOAD_FOLDER')
# msg = "UPLOAD_FOLDER config item is: {}".format(app.config['UPLOAD_FOLDER'])
# flash(msg, 'info')
#
# app.config['SECRET_KEY'] = environ.get('OHSCRIBE_SECRET_KEY') or 'i-hope-you-never-guess-this'
# msg = "SECRET_KEY config item is: {}".format(app.config['SECRET_KEY'])
# flash(msg, 'info')
#

bootstrap = Bootstrap(app)

from app import routes, errors, actions

# Use the host's IP address per https://stackoverflow.com/questions/7023052/configure-flask-dev-server-to-be-visible-across-the-network
# Always encapsulate the '.run' call per https://stackoverflow.com/questions/29356224/error-errno-98-address-already-in-use
if __name__ == '__main__':
  app.run(host=host, port=5000)    # for PROD host='0.0.0.0' and for DEV host='127.0.0.1'
