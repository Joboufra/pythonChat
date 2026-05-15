Aplicación de chat en tiempo real construida con FastAPI, WebSockets y PostgreSQL.

<img width="873" height="763" alt="image" src="https://github.com/user-attachments/assets/72d4e3dc-1df0-41c5-ad1d-2283331b42a4" />
<img width="1901" height="934" alt="image" src="https://github.com/user-attachments/assets/4da286fd-97b7-461e-b095-6f009a0c2ada" />
<img width="911" height="802" alt="image" src="https://github.com/user-attachments/assets/3a15e5f1-f098-4af5-89da-04d7a927c351" />


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
