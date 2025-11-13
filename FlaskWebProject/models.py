
from datetime import datetime
from FlaskWebProject import app, db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
# 👇 Nuevo SDK (v12)
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

import string, random
from werkzeug.utils import secure_filename
from flask import flash

# =========================================
# Config & clientes de Blob Storage (v12)
# =========================================
blob_container = app.config['BLOB_CONTAINER']

# Usamos account_name + account_key (mismo esquema que tenías)
# Si preferís connection string: BlobServiceClient.from_connection_string(app.config['BLOB_CONNECTION_STRING'])
account_url = f"https://{app.config['BLOB_ACCOUNT']}.blob.core.windows.net"
blob_service = BlobServiceClient(account_url=account_url,
                                 credential=app.config['BLOB_STORAGE_KEY'])

# Cliente del contenedor (lo creamos si no existe)
container_client = blob_service.get_container_client(blob_container)
try:
    # create_container() falla si existe; por eso controlamos ResourceExistsError
    container_client.create_container()
except ResourceExistsError:
    pass

def id_generator(size=32, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    author = db.Column(db.String(75))
    body = db.Column(db.String(800))
    image_path = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    def save_changes(self, form, file, userId, new=False):
        self.title = form.title.data
        self.author = form.author.data
        self.body = form.body.data
        self.user_id = userId

        if file and getattr(file, "filename", ""):
            # Normalizamos el filename y generamos uno aleatorio preservando extensión (si tiene)
            original = secure_filename(file.filename)
            ext = ""
            if "." in original:
                ext = "." + original.rsplit(".", 1)[1].lower()

            filename = f"{id_generator()}{ext}"

            try:
                # Nota: file es un werkzeug.datastructures.FileStorage -> .stream es el binario
                container_client.upload_blob(name=filename, data=file.stream, overwrite=True)

                # Si ya había imagen anterior, intentamos borrarla
                if self.image_path:
                    try:
                        container_client.delete_blob(self.image_path)
                    except ResourceNotFoundError:
                        # Si no existe, no pasa nada
                        pass

                self.image_path = filename

            except Exception as e:
                # Mostramos feedback y dejamos trazas
                app.logger.exception("Blob upload failed")
                flash(f"Error subiendo imagen al blob: {e}")

        if new:
            db.session.add(self)
        db.session.commit()
