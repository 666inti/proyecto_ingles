# config.py

class Config:
    # Configuración de la base de datos SQLite (para un ejemplo simple)
    # Puedes cambiar esto a PostgreSQL, MySQL, etc., según tu necesidad.
    # Por ejemplo: 'postgresql://user:password@host:port/dbname'
    # o 'mysql+mysqlconnector://user:password@host/dbname'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Desactiva el seguimiento de modificaciones de SQLAlchemy
    SECRET_KEY = 'your_secret_key_here' # Clave secreta para seguridad de la aplicación Flask