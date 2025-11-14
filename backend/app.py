from flask import Flask
from flask_cors import CORS
from config import Config
from flask_migrate import Migrate
from database import db
from routes.chat_routes import chat_bp
from routes.auth_routes import auth_bp
import click
from flask.cli import with_appcontext
from seed_data import seed_data
from datetime import timedelta


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)
    migrate = Migrate(app, db)
    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:3000"]}},
        supports_credentials=True
    )


    
    app.secret_key = "LEGACY_SECRET_KEY"
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_TYPE'] = 'filesystem'
    

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    # -------------------------------------------------
    # Registrar el comando init-db dentro de create_app
    # -------------------------------------------------
    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command():
        """Inicializa la base de datos y carga los datos iniciales."""
        db.create_all()
        seed_data()
        click.echo("Base de datos inicializada y datos cargados correctamente.")

    return app


# Ejecutar servidor si se corre directamente
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
