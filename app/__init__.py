from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import redirect, url_for
from flask_migrate import Migrate
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()

basedir = os.path.abspath(os.path.dirname(__file__))

def create_app():
    # Cargar variables de entorno
    load_dotenv()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sicred_secret')
    
    # Configuración de la base de datos PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Asegurarse de que la URL comience con postgresql:// (no postgres://)
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback a SQLite si no hay DATABASE_URL
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sicred.sqlite3')
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)

    # Configuración de logging para registrar errores
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/error.log', maxBytes=10240, backupCount=5)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.ERROR)

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
