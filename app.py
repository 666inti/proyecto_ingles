# app.py 
from flask import Flask, jsonify, redirect, request, render_template, flash, session, url_for 
from database import db 
from config import Config
import datetime 
from werkzeug.security import generate_password_hash, check_password_hash # ¡NUEVO! Importa estas funciones
from functools import wraps # ¡NUEVO! Para el decorador de login

# --- Inicialización de la aplicación Flask ---
app = Flask(__name__) 
app.config.from_object(Config) 

# Inicializa la extensión SQLAlchemy con la aplicación Flask
db.init_app(app) 

# --- Definición de Modelos (Clases que representan las tablas) ---

# Base class for common methods (optional, but good practice)
class BaseModel(db.Model):
    __abstract__ = True # Indica que esta clase es abstracta y no se mapeará a una tabla

    def save(self):
        """Guarda la instancia actual en la base de datos."""
        db.session.add(self)
        db.session.commit()
        # print(f"Guardado: {self.__class__.__name__} con ID {getattr(self, self.__mapper__.primary_key[0].name)}")

    def delete(self):
        """Elimina la instancia actual de la base de datos."""
        db.session.delete(self)
        db.session.commit()
        # print(f"Eliminado: {self.__class__.__name__} con ID {getattr(self, self.__mapper__.primary_key[0].name)}")

    @classmethod
    def get_all(cls):
        """Obtiene todas las instancias de esta clase."""
        return cls.query.all()

    @classmethod
    def get_by_id(cls, id):
        """Obtiene una instancia por su ID."""
        return cls.query.get(id)


class Usuario(BaseModel):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # CAMBIADO: 'password' a 'contrasena_hash' y con un largo mayor para el hash
    contrasena_hash = db.Column(db.String(255), nullable=False) 
    rol = db.Column(db.String(50), nullable=False) # 'admin', 'profesor', 'estudiante' 
    
    # NUEVOS: fecha_registro y activo (si no los tenías)
    fecha_registro = db.Column(db.DateTime, default=datetime.datetime.now)
    activo = db.Column(db.Boolean, default=True)

    # Relaciones (con ondelete/cascade para mejor manejo de eliminación)
    # un usuario puede ser un estudiante o un profesor (o ambos, pero con roles distintos)
    estudiante_rel = db.relationship('Estudiante', backref='usuario', uselist=False, lazy=True, cascade="all, delete-orphan")
    profesor_rel = db.relationship('Profesor', backref='usuario', uselist=False, lazy=True, cascade="all, delete-orphan")

    # --- NUEVOS MÉTODOS PARA CONTRASEÑAS ---
    def set_password(self, password):
        """Hashea la contraseña y la guarda en contrasena_hash."""
        self.contrasena_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña dada coincide con el hash guardado."""
        return check_password_hash(self.contrasena_hash, password)
    # -------------------------------------

    def __repr__(self):
        return f'<Usuario {self.nombre} ({self.rol})>'


class Nivel(BaseModel):
    __tablename__ = 'niveles'
    id_nivel = db.Column(db.Integer, primary_key=True)
    niveles = db.Column(db.String(80), unique=True, nullable=False)

    # Relaciones
    estudiantes = db.relationship('Estudiante', backref='nivel_obj', lazy=True)
    profesores = db.relationship('Profesor', backref='nivel_obj', lazy=True)
    lecciones = db.relationship('Leccion', backref='nivel_obj', lazy=True) # Si las lecciones tienen un nivel específico

    def __repr__(self):
        return f'<Nivel {self.niveles}>'


class Estudiante(BaseModel):
    __tablename__ = 'estudiantes'
    id_estudiante = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), unique=True, nullable=False)
    id_nivel = db.Column(db.Integer, db.ForeignKey('niveles.id_nivel'), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f'<Estudiante {self.usuario.nombre}>'


class Profesor(BaseModel):
    __tablename__ = 'profesores'
    id_profesor = db.Column(db.Integer, primary_key=True)
    # MODIFICADO: Si el usuario asociado se elimina, el profesor también se elimina.
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), unique=True, nullable=False)
    asignatura = db.Column(db.String(100), nullable=False) # Ej: 'Gramática Inglesa', 'Conversación'
    id_nivel = db.Column(db.Integer, db.ForeignKey('niveles.id_nivel'), nullable=True) # Opcional: si el profesor se especializa en un nivel (Aquí no se necesita ondelete si el Nivel no lo tiene)

    # MODIFICADO: Si se elimina un Profesor, todas sus Lecciones asociadas también se ELIMINAN.
    lecciones = db.relationship('Leccion', backref='profesor', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Profesor {self.usuario.nombre} - {self.asignatura}>'


class Leccion(BaseModel):
    __tablename__ = 'lecciones'
    id_leccion = db.Column(db.Integer, primary_key=True)
    # MODIFICADO: CLAVE PARA TU ERROR. Si el Profesor se elimina, esta Lección también se ELIMINA.
    id_profesor = db.Column(db.Integer, db.ForeignKey('profesores.id_profesor', ondelete='CASCADE'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    video = db.Column(db.String(255), nullable=True) # URL de video
    
    # MODIFICADO: Si el Nivel se elimina, el id_nivel en esta Lección se pone a NULL.
    id_nivel = db.Column(db.Integer, db.ForeignKey('niveles.id_nivel', ondelete='SET NULL'), nullable=True) 

    # MODIFICADO: Si se elimina una Lección, todos sus Ejercicios asociados también se ELIMINAN.
    ejercicios = db.relationship('Ejercicio', backref='leccion', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Leccion {self.titulo}>'


class Ejercicio(BaseModel):
    __tablename__ = 'ejercicios'
    id_ejercicio = db.Column(db.Integer, primary_key=True)
    # MODIFICADO: Si la Lección se elimina, este Ejercicio también se ELIMINA.
    id_leccion = db.Column(db.Integer, db.ForeignKey('lecciones.id_leccion', ondelete='CASCADE'), nullable=False)
    pregunta = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), nullable=False) # Ej: 'multiple_choice', 'fill_in_the_blank', 'short_answer'
    opciones = db.Column(db.Text, nullable=True) # Para opciones, separadas por coma si es multiple_choice
    respuesta = db.Column(db.Text, nullable=False)
    def __repr__(self):
        return f'<Ejercicio {self.id_ejercicio} - {self.pregunta[:30]}...>'


class ProgresoEstudiante(BaseModel):
    __tablename__ = 'progreso_estudiantes'
    id_progreso = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiantes.id_estudiante'), nullable=False)
    id_ejercicio = db.Column(db.Integer, db.ForeignKey('ejercicios.id_ejercicio'), nullable=False)
    fecha_completado = db.Column(db.DateTime, default=datetime.datetime.now)
    puntuacion = db.Column(db.Integer, nullable=True)
    respuesta_estudiante = db.Column(db.Text, nullable=True)

    # Relaciones
    estudiante = db.relationship('Estudiante', backref='progresos', lazy=True)
    ejercicio = db.relationship('Ejercicio', backref='progresos', lazy=True)

    def __repr__(self):
        return f'<Progreso: Estudiante {self.id_estudiante} - Ejercicio {self.id_ejercicio}>'


# --- Rutas de Autenticación (Login y Logout) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el inicio de sesión del usuario."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Usuario.query.filter_by(email=email).first()

        if user and user.check_password(password): # Usa check_password
            session['user_id'] = user.id_usuario
            session['user_email'] = user.email
            session['user_rol'] = user.rol
            flash('Inicio de sesión exitoso!', 'success')
            
            # Redirigir según el rol
            if user.rol == 'admin':
                return redirect(url_for('usuarios_web')) # O un panel de admin específico
            elif user.rol == 'profesor':
                return redirect(url_for('lecciones_web')) # O un panel de profesor
            elif user.rol == 'estudiante':
                return redirect(url_for('index')) # O un panel de estudiante
            else:
                return redirect(url_for('index')) # Redirección por defecto
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')

def logout():
    """Cierra la sesión del usuario."""
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_rol', None)
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

# --- Decorador para proteger rutas ---

def login_required(f):
    """
    Decorador para proteger rutas, asegurando que un usuario esté logueado.
    Redirige a la página de login si no hay sesión activa.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# --- Rutas Web ---

@app.route('/')
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def index():
    """Ruta principal que muestra la página de inicio."""
    return render_template('index.html')

# --- Rutas CRUD para Niveles ---

@app.route('/niveles_web')
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def niveles_web():
    """Muestra la lista de todos los niveles."""
    niveles = Nivel.get_all()
    return render_template('niveles.html', niveles=niveles)

@app.route('/nuevo_nivel_web', methods=['GET', 'POST'])
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def nuevo_nivel_web():
    """Muestra el formulario para crear un nuevo nivel y maneja su envío."""
    if request.method == 'POST':
        nombre_nivel = request.form['niveles']

        if not nombre_nivel:
            flash('El nombre del nivel es obligatorio.', 'danger')
            return render_template('nuevo_nivel.html')

        if Nivel.query.filter_by(niveles=nombre_nivel).first():
            flash('Ya existe un nivel con ese nombre.', 'warning')
            return render_template('nuevo_nivel.html')

        try:
            nuevo_nivel = Nivel(niveles=nombre_nivel)
            nuevo_nivel.save()
            flash('Nivel creado exitosamente!', 'success')
            return redirect(url_for('niveles_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el nivel: {e}', 'danger')
            return render_template('nuevo_nivel.html')
    
    return render_template('nuevo_nivel.html')

@app.route('/ver_nivel_web/<int:id_nivel>')
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def ver_nivel_web(id_nivel):
    """Muestra los detalles de un nivel específico."""
    nivel = Nivel.query.get_or_404(id_nivel)
    return render_template('ver_nivel.html', nivel=nivel)

@app.route('/editar_nivel_web/<int:id_nivel>', methods=['GET', 'POST'])
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def editar_nivel_web(id_nivel):
    """Muestra el formulario para editar un nivel y maneja su envío."""
    nivel = Nivel.query.get_or_404(id_nivel)

    if request.method == 'POST':
        nuevo_nombre = request.form['niveles']
        
        if Nivel.query.filter_by(niveles=nuevo_nombre).first() and nuevo_nombre != nivel.niveles:
            flash('Ya existe un nivel con ese nombre.', 'warning')
            return render_template('editar_nivel.html', nivel=nivel)

        try:
            nivel.niveles = nuevo_nombre
            db.session.commit()
            flash('Nivel actualizado exitosamente!', 'success')
            return redirect(url_for('niveles_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el nivel: {e}', 'danger')
    
    return render_template('editar_nivel.html', nivel=nivel)

@app.route('/eliminar_nivel_web/<int:id_nivel>', methods=['POST'])
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def eliminar_nivel_web(id_nivel):
    """Elimina un nivel de la base de datos."""
    nivel = Nivel.query.get_or_404(id_nivel)
    try:
        db.session.delete(nivel)
        db.session.commit()
        flash('Nivel eliminado exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el nivel: {e}', 'danger')
    
    return redirect(url_for('niveles_web'))


# --- Rutas CRUD para Usuarios ---

@app.route('/usuarios_web')
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def usuarios_web():
    """Muestra la lista de todos los usuarios."""
    usuarios = Usuario.get_all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/nuevo_usuario_web', methods=['GET', 'POST'])
def nuevo_usuario_web():
    """Muestra el formulario para crear un nuevo usuario y maneja su envío."""
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password'] # Obtienes la contraseña del formulario
        rol = request.form['rol']

        if not all([nombre, email, password, rol]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('nuevo_usuario.html')

        if Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email.', 'warning')
            return render_template('nuevo_usuario.html')

        try:
            # CAMBIO CLAVE AQUÍ: No pases 'password' al constructor
            nuevo_usuario = Usuario(nombre=nombre, email=email, rol=rol)
            # Luego, llama al método set_password para hashear y guardar la contraseña
            nuevo_usuario.set_password(password) 
            
            nuevo_usuario.save() # Esto guardará el usuario con la contraseña hasheada
            flash('Usuario creado exitosamente!', 'success')
            return redirect(url_for('usuarios_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el usuario: {e}', 'danger')
            return render_template('nuevo_usuario.html')
    
    return render_template('nuevo_usuario.html')

@app.route('/ver_usuario_web/<int:id_usuario>')
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def ver_usuario_web(id_usuario):
    """Muestra los detalles de un usuario específico."""
    usuario = Usuario.query.get_or_404(id_usuario)
    return render_template('ver_usuario.html', usuario=usuario)

@app.route('/editar_usuario_web/<int:id_usuario>', methods=['GET', 'POST'])
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def editar_usuario_web(id_usuario):
    """Muestra el formulario para editar un usuario y maneja su envío."""
    usuario = Usuario.query.get_or_404(id_usuario)

    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.email = request.form['email']
        # Solo actualiza la contraseña si se proporciona una nueva
        if request.form['password']:
            usuario.password = request.form['password'] # En una app real, aquí se debería hashear
        usuario.rol = request.form['rol']

        try:
            db.session.commit() # BaseModel.save() hace add y commit, aquí solo necesitamos commit
            flash('Usuario actualizado exitosamente!', 'success')
            return redirect(url_for('usuarios_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el usuario: {e}', 'danger')
            # Si hay un error, vuelve a renderizar el formulario con los datos actuales
            return render_template('editar_usuario.html', usuario=usuario)
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/eliminar_usuario_web/<int:id_usuario>', methods=['POST'])
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def eliminar_usuario_web(id_usuario):
    """Elimina un usuario de la base de datos."""
    usuario = Usuario.query.get_or_404(id_usuario)
    try:
        usuario.delete() # Usa el método delete de BaseModel
        flash('Usuario eliminado exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {e}', 'danger')
    
    return redirect(url_for('usuarios_web'))

# --- Rutas CRUD para Estudiantes ---

@app.route('/estudiantes_web')
@login_required # Protege la ruta para que solo usuarios logueados puedan acceder
def estudiantes_web():
    """Muestra la lista de todos los estudiantes."""
    estudiantes = Estudiante.get_all()
    return render_template('estudiantes.html', estudiantes=estudiantes)

@app.route('/nuevo_estudiante_web', methods=['GET', 'POST'])
@login_required
def nuevo_estudiante_web():
    """Muestra el formulario para crear un nuevo estudiante y maneja su envío."""
    usuarios_disponibles = Usuario.query.filter_by(rol='estudiante').all() # Filtrar por rol 'estudiante'
    niveles_disponibles = Nivel.get_all()

    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        id_nivel = request.form['id_nivel']
        fecha_nacimiento_str = request.form['fecha_nacimiento']

        if not all([id_usuario, id_nivel, fecha_nacimiento_str]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('nuevo_estudiante.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)
        
        # Convertir la fecha de string a objeto date
        try:
            fecha_nacimiento = datetime.datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha de nacimiento inválido.', 'danger')
            return render_template('nuevo_estudiante.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)

        # Verificar si el usuario ya está asociado a un estudiante
        if Estudiante.query.filter_by(id_usuario=id_usuario).first():
            flash('Este usuario ya está registrado como estudiante.', 'warning')
            return render_template('nuevo_estudiante.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)


        try:
            nuevo_estudiante = Estudiante(
                id_usuario=id_usuario,
                id_nivel=id_nivel,
                fecha_nacimiento=fecha_nacimiento
            )
            nuevo_estudiante.save()
            flash('Estudiante registrado exitosamente!', 'success')
            return redirect(url_for('estudiantes_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el estudiante: {e}', 'danger')
            return render_template('nuevo_estudiante.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)
    
    return render_template('nuevo_estudiante.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)


@app.route('/ver_estudiante_web/<int:id_estudiante>')
@login_required
def ver_estudiante_web(id_estudiante):
    """Muestra los detalles de un estudiante específico."""
    estudiante = Estudiante.query.get_or_404(id_estudiante)
    return render_template('ver_estudiante.html', estudiante=estudiante)

@app.route('/editar_estudiante_web/<int:id_estudiante>', methods=['GET', 'POST'])
@login_required
def editar_estudiante_web(id_estudiante):
    """Muestra el formulario para editar un estudiante y maneja su envío."""
    estudiante = Estudiante.query.get_or_404(id_estudiante)
    usuarios_disponibles = Usuario.query.filter_by(rol='estudiante').all() # Filtrar por rol 'estudiante'
    niveles_disponibles = Nivel.get_all()

    if request.method == 'POST':
        nuevo_id_usuario = request.form['id_usuario']
        nuevo_id_nivel = request.form['id_nivel']
        nueva_fecha_nacimiento_str = request.form['fecha_nacimiento']

        # Verificar si el usuario seleccionado ya está asignado a otro estudiante (si cambió)
        if nuevo_id_usuario != str(estudiante.id_usuario): # Compara con string porque form data es string
            if Estudiante.query.filter_by(id_usuario=nuevo_id_usuario).first():
                flash('Este usuario ya está registrado como estudiante en otra entrada.', 'warning')
                return render_template('editar_estudiante.html', estudiante=estudiante, usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)

        try:
            estudiante.id_usuario = nuevo_id_usuario
            estudiante.id_nivel = nuevo_id_nivel
            estudiante.fecha_nacimiento = datetime.datetime.strptime(nueva_fecha_nacimiento_str, '%Y-%m-%d').date()
            
            db.session.commit()
            flash('Estudiante actualizado exitosamente!', 'success')
            return redirect(url_for('estudiantes_web'))
        except ValueError:
            flash('Formato de fecha de nacimiento inválido.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el estudiante: {e}', 'danger')
    
    return render_template('editar_estudiante.html', estudiante=estudiante, usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)


@app.route('/eliminar_estudiante_web/<int:id_estudiante>', methods=['POST'])
@login_required
def eliminar_estudiante_web(id_estudiante):
    """Elimina un estudiante de la base de datos."""
    estudiante = Estudiante.query.get_or_404(id_estudiante)
    try:
        estudiante.delete()
        flash('Estudiante eliminado exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el estudiante: {e}', 'danger')
    
    return redirect(url_for('estudiantes_web'))

# --- Rutas CRUD para Profesores ---

@app.route('/profesores_web')
@login_required
def profesores_web():
    """Muestra la lista de todos los profesores."""
    profesores = Profesor.get_all()
    return render_template('profesores.html', profesores=profesores)

@app.route('/nuevo_profesor_web', methods=['GET', 'POST'])
def nuevo_profesor_web():
    """Muestra el formulario para registrar un nuevo profesor y maneja su envío."""
    usuarios_disponibles = Usuario.query.filter_by(rol='profesor').all() # Filtrar por rol 'profesor'
    niveles_disponibles = Nivel.get_all()

    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        asignatura = request.form['asignatura']
        id_nivel = request.form.get('id_nivel') # Puede ser None si no se selecciona

        if not all([id_usuario, asignatura]):
            flash('El usuario y la asignatura son obligatorios.', 'danger')
            return render_template('nuevo_profesor.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)

        # Verificar si el usuario ya está asociado a un profesor
        if Profesor.query.filter_by(id_usuario=id_usuario).first():
            flash('Este usuario ya está registrado como profesor.', 'warning')
            return render_template('nuevo_profesor.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)

        try:
            nuevo_profesor = Profesor(
                id_usuario=id_usuario,
                asignatura=asignatura,
                id_nivel=id_nivel if id_nivel else None # Guardar como None si no se seleccionó
            )
            nuevo_profesor.save()
            flash('Profesor registrado exitosamente!', 'success')
            return redirect(url_for('profesores_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el profesor: {e}', 'danger')
            return render_template('nuevo_profesor.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)
    
    return render_template('nuevo_profesor.html', usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)


@app.route('/ver_profesor_web/<int:id_profesor>')
@login_required
def ver_profesor_web(id_profesor):
    """Muestra los detalles de un profesor específico."""
    profesor = Profesor.query.get_or_404(id_profesor)
    return render_template('ver_profesor.html', profesor=profesor)

@app.route('/editar_profesor_web/<int:id_profesor>', methods=['GET', 'POST'])
@login_required
def editar_profesor_web(id_profesor):
    """Muestra el formulario para editar un profesor y maneja su envío."""
    profesor = Profesor.query.get_or_404(id_profesor)
    usuarios_disponibles = Usuario.query.filter_by(rol='profesor').all()
    niveles_disponibles = Nivel.get_all()

    if request.method == 'POST':
        nuevo_id_usuario = request.form['id_usuario']
        nueva_asignatura = request.form['asignatura']
        nuevo_id_nivel = request.form.get('id_nivel')

        # Verificar si el usuario seleccionado ya está asignado a otro profesor (si cambió)
        if nuevo_id_usuario != str(profesor.id_usuario):
            if Profesor.query.filter_by(id_usuario=nuevo_id_usuario).first():
                flash('Este usuario ya está registrado como profesor en otra entrada.', 'warning')
                return render_template('editar_profesor.html', profesor=profesor, usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)

        try:
            profesor.id_usuario = nuevo_id_usuario
            profesor.asignatura = nueva_asignatura
            profesor.id_nivel = nuevo_id_nivel if nuevo_id_nivel else None
            
            db.session.commit()
            flash('Profesor actualizado exitosamente!', 'success')
            return redirect(url_for('profesores_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el profesor: {e}', 'danger')
    
    return render_template('editar_profesor.html', profesor=profesor, usuarios_disponibles=usuarios_disponibles, niveles_disponibles=niveles_disponibles)


@app.route('/eliminar_profesor_web/<int:id_profesor>', methods=['POST'])
@login_required
def eliminar_profesor_web(id_profesor):
    """Elimina un profesor de la base de datos."""
    profesor = Profesor.query.get_or_404(id_profesor)
    try:
        profesor.delete()
        flash('Profesor eliminado exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el profesor: {e}', 'danger')
    
    return redirect(url_for('profesores_web'))

# --- Rutas CRUD para Lecciones (PLACEHOLDER - si ya las tienes, intégralas aquí) ---
# Si aún no tienes estas, no causarán error, pero no funcionarán si haces clic en sus enlaces.
@app.route('/lecciones_web')
@login_required
def lecciones_web():
    lecciones = Leccion.get_all()
    return render_template('lecciones.html', lecciones=lecciones)

@app.route('/nuevo_leccion_web', methods=['GET', 'POST'])
@login_required
def nuevo_leccion_web():
    profesores_disponibles = Profesor.get_all()
    niveles_disponibles = Nivel.get_all()
    # Lógica para nuevo_leccion_web
    if request.method == 'POST':
        id_profesor = request.form['id_profesor']
        titulo = request.form['titulo']
        contenido = request.form['contenido']
        video = request.form.get('video')
        id_nivel = request.form.get('id_nivel')

        if not all([id_profesor, titulo, contenido]):
            flash('Profesor, título y contenido son obligatorios.', 'danger')
            return render_template('nuevo_leccion.html', profesores_disponibles=profesores_disponibles, niveles_disponibles=niveles_disponibles)
        
        try:
            nueva_leccion = Leccion(
                id_profesor=id_profesor,
                titulo=titulo,
                contenido=contenido,
                video=video,
                id_nivel=id_nivel if id_nivel else None
            )
            nueva_leccion.save()
            flash('Lección creada exitosamente!', 'success')
            return redirect(url_for('lecciones_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la lección: {e}', 'danger')
            return render_template('nuevo_leccion.html', profesores_disponibles=profesores_disponibles, niveles_disponibles=niveles_disponibles)
    return render_template('nuevo_leccion.html', profesores_disponibles=profesores_disponibles, niveles_disponibles=niveles_disponibles)


@app.route('/ver_leccion_web/<int:id_leccion>')
@login_required
def ver_leccion_web(id_leccion):
    leccion = Leccion.query.get_or_404(id_leccion)
    return render_template('ver_leccion.html', leccion=leccion)

@app.route('/editar_leccion_web/<int:id_leccion>', methods=['GET', 'POST'])
def editar_leccion_web(id_leccion):
    leccion = Leccion.query.get_or_404(id_leccion)
    profesores_disponibles = Profesor.get_all()
    niveles_disponibles = Nivel.get_all()
    if request.method == 'POST':
        leccion.id_profesor = request.form['id_profesor']
        leccion.titulo = request.form['titulo']
        leccion.contenido = request.form['contenido']
        leccion.video = request.form.get('video')
        leccion.id_nivel = request.form.get('id_nivel')
        try:
            db.session.commit()
            flash('Lección actualizada exitosamente!', 'success')
            return redirect(url_for('lecciones_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la lección: {e}', 'danger')
    return render_template('editar_leccion.html', leccion=leccion, profesores_disponibles=profesores_disponibles, niveles_disponibles=niveles_disponibles)

@app.route('/eliminar_leccion_web/<int:id_leccion>', methods=['POST'])
@login_required
def eliminar_leccion_web(id_leccion):
    leccion = Leccion.query.get_or_404(id_leccion)
    try:
        leccion.delete()
        flash('Lección eliminada exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la lección: {e}', 'danger')
    return redirect(url_for('lecciones_web'))

# --- Rutas CRUD para Ejercicios (PLACEHOLDER - si ya las tienes, intégralas aquí) ---
@app.route('/ejercicios_web')
@login_required
def ejercicios_web():
    ejercicios = Ejercicio.get_all()
    return render_template('ejercicios.html', ejercicios=ejercicios)

@app.route('/nuevo_ejercicio_web', methods=['GET', 'POST'])
@login_required
def nuevo_ejercicio_web():
    lecciones_disponibles = Leccion.get_all()
    # Lógica para nuevo_ejercicio_web
    if request.method == 'POST':
        id_leccion = request.form['id_leccion']
        pregunta = request.form['pregunta']
        tipo = request.form['tipo']
        opciones = request.form.get('opciones')
        respuesta = request.form['respuesta']

        if not all([id_leccion, pregunta, tipo, respuesta]):
            flash('Lección, pregunta, tipo y respuesta son obligatorios.', 'danger')
            return render_template('nuevo_ejercicio.html', lecciones_disponibles=lecciones_disponibles)
        
        try:
            nuevo_ejercicio = Ejercicio(
                id_leccion=id_leccion,
                pregunta=pregunta,
                tipo=tipo,
                opciones=opciones,
                respuesta=respuesta
            )
            nuevo_ejercicio.save()
            flash('Ejercicio creado exitosamente!', 'success')
            return redirect(url_for('ejercicios_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el ejercicio: {e}', 'danger')
            return render_template('nuevo_ejercicio.html', lecciones_disponibles=lecciones_disponibles)
    return render_template('nuevo_ejercicio.html', lecciones_disponibles=lecciones_disponibles)

@app.route('/ver_ejercicio_web/<int:id_ejercicio>')
@login_required
def ver_ejercicio_web(id_ejercicio):
    ejercicio = Ejercicio.query.get_or_404(id_ejercicio)
    return render_template('ver_ejercicio.html', ejercicio=ejercicio)

@app.route('/editar_ejercicio_web/<int:id_ejercicio>', methods=['GET', 'POST'])
@login_required
def editar_ejercicio_web(id_ejercicio):
    ejercicio = Ejercicio.query.get_or_404(id_ejercicio)
    lecciones_disponibles = Leccion.get_all()
    if request.method == 'POST':
        ejercicio.id_leccion = request.form['id_leccion']
        ejercicio.pregunta = request.form['pregunta']
        ejercicio.tipo = request.form['tipo']
        ejercicio.opciones = request.form.get('opciones')
        ejercicio.respuesta = request.form['respuesta']
        try:
            db.session.commit()
            flash('Ejercicio actualizado exitosamente!', 'success')
            return redirect(url_for('ejercicios_web'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el ejercicio: {e}', 'danger')
    return render_template('editar_ejercicio.html', ejercicio=ejercicio, lecciones_disponibles=lecciones_disponibles)


@app.route('/eliminar_ejercicio_web/<int:id_ejercicio>', methods=['POST'])
@login_required
def eliminar_ejercicio_web(id_ejercicio):
    ejercicio = Ejercicio.query.get_or_404(id_ejercicio)
    try:
        ejercicio.delete()
        flash('Ejercicio eliminado exitosamente!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el ejercicio: {e}', 'danger')
    return redirect(url_for('ejercicios_web'))


# --- Ejecución de la aplicación ---
if __name__ == '__main__': 
    with app.app_context(): 
        db.create_all() 
        # Opcional: crea algunos datos de prueba iniciales si la DB está vacía 
        if not Nivel.query.first(): 
            nivel_principiante = Nivel(niveles="Principiante") 
            nivel_intermedio = Nivel(niveles="Intermedio") 
            nivel_avanzado = Nivel(niveles="Avanzado") 
            db.session.add(nivel_principiante) 
            db.session.add(nivel_intermedio) 
            db.session.add(nivel_avanzado) 
            db.session.commit() 
            print("Datos de niveles de prueba creados.") 

        if not Usuario.query.first(): 
            print("Creando datos de prueba iniciales (usuarios, profesores, estudiantes, lecciones, ejercicios)...")
            
            # Crear usuarios - ¡AHORA CON set_password!
            usuario1 = Usuario(nombre="Admin General", email="admin@example.com", rol="admin")
            usuario1.set_password("admin123") # <--- Contraseña para el admin
            db.session.add(usuario1)

            usuario2 = Usuario(nombre="Profesor Juan", email="juan@example.com", rol="profesor")
            usuario2.set_password("juan123") # <--- Contraseña para Juan
            db.session.add(usuario2)
        
            usuario3 = Usuario(nombre="Estudiante Ana", email="ana@example.com", rol="estudiante")
            usuario3.set_password("ana123") # <--- Contraseña para Ana
            db.session.add(usuario3)
            
            usuario4 = Usuario(nombre="Estudiante Pedro", email="pedro@example.com", rol="estudiante")
            usuario4.set_password("pedro123") # <--- Contraseña para Pedro
            db.session.add(usuario4)
            
            usuario5 = Usuario(nombre="Profesor Maria", email="maria@example.com", rol="profesor")
            usuario5.set_password("maria123") # <--- Contraseña para María
            db.session.add(usuario5)
            db.session.commit() # ¡Commit aquí para que los usuarios existan antes de usarlos!

            # ... (el resto de tu creación de datos de prueba para profesores, estudiantes, lecciones, ejercicios) ... 
            
            print("Todos los datos de prueba iniciales creados exitosamente.") 

        app.run(debug=True)


# --- ASEGÚRATE DE QUE ESTE BLOQUE ESTÉ AL FINAL DEL ARCHIVO app.py ---
# --- Ejecución de la aplicación ---
if __name__ == '__main__': 
    # Esto creará la base de datos (site.db) y las tablas
    # la primera vez que ejecutes el script. 
    # En un entorno de producción, usarías migraciones (como Flask-Migrate). 
    with app.app_context(): 
        db.create_all() 
        # Opcional: crea algunos datos de prueba iniciales si la DB está vacía
        if not Nivel.query.first(): 
            nivel_primaria = Nivel(niveles="Principiante")
            nivel_secundaria = Nivel(niveles="Intermedio")
            nivel_avanzado = Nivel(niveles="Avanzado")
            db.session.add(nivel_primaria) 
            db.session.add(nivel_secundaria) 
            db.session.add(nivel_avanzado)
            db.session.commit() 
    app.run(debug=True) # debug=True es solo para desarrollo

# --- Ejecución de la aplicación ---
if __name__ == '__main__':
    # Esto creará la base de datos (site.db) y las tablas
    # la primera vez que ejecutes el script.
    # En un entorno de producción, usarías migraciones (como Flask-Migrate).
    with app.app_context():
        db.create_all()
    app.run(debug=True) # debug=True es solo para desarrollo