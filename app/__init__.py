from flask import Flask
from flask_cors import CORS
from config import Config
from .database import db


def create_app(config_class=Config):
    app = Flask(__name__)
    cors = CORS(app)
    app.config.from_object(config_class)

    from .routes import main as main_blueprint

    app.register_blueprint(main_blueprint)

    return app
