Aplicación de chat en tiempo real construida con FastAPI, WebSockets y PostgreSQL.

## Características

- **Mensajería en Tiempo Real**: Comunicación instantánea mediante WebSockets.
- **Perfiles Personalables**: Cambia tu apodo y color en tiempo real.
- **Soporte de Emojis**: Selector de emojis integrado.
- **Nuevo diseño**: UI rediseñada, optimizada para móvil y escritorio.
- **Seguridad**: Rate limiting, sanitize de inputs y headers de seguridad.

## Tecnologías

- **Backend**: Python, FastAPI, Uvicorn
- **Base de Datos**: PostgreSQL (asyncpg)
- **ORM**: SQLAlchemy 2.0
- **Validación**: Pydantic
- **Frontend**: JavaScript vainilla, CSS3

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/Joboufra/pythonChat
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno en el archivo `.env`.

## Ejecución

Inicia el servidor:
```bash
uvicorn app.main:app --reload
```

La aplicación estará disponible en `http://localhost:8000`.
