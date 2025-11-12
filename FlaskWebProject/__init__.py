"""
The flask application package.
"""
import logging
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session

app = Flask(__name__)
app.config.from_object(Config)
# Configuración de logging para App Service / Log Stream
# Nivel INFO para ver tanto éxitos como fallos (warning/error)
app.logger.setLevel(logging.INFO)
if not app.logger.handlers:
	streamHandler = logging.StreamHandler()
	streamHandler.setLevel(logging.INFO)
	formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
	streamHandler.setFormatter(formatter)
	app.logger.addHandler(streamHandler)
Session(app)
db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = 'login'

import FlaskWebProject.views
