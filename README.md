# GitHub Actions Workflow Run Data Extractor

Este proyecto permite **extraer, organizar y almacenar automáticamente información detallada** sobre las ejecuciones de GitHub Actions (*workflow runs*) de múltiples repositorios públicos, permitiendo crear un dataset para análisis, debugging de pipelines, auditoría de ejecuciones fallidas y más.

## ¿Qué hace este software?

El script principal (`script.py`) recorre una lista de repositorios especificados en un archivo `repos.csv` y:

- Extrae hasta `MAX_RUNS` ejecuciones recientes de cada repositorio.
- Descarga los siguientes elementos de cada ejecución:
  - Metadata general (`workflow_run.json`)
  - Detalles de jobs (`jobs.json`)
  - Archivo YAML del workflow
  - Logs comprimidos (`logs.zip`)
- Clasifica cada ejecución en carpetas organizadas según su estado:
  - Todas las ejecuciones
  - Solo ejecuciones fallidas
  - Solo ejecuciones que fueron rerun

Para mayor detalle, leer documentación en notebook.ipynb.

## Estructura esperada del proyecto

```
github-actions-workflow-run-data-extractor/
├── env                      ← Entorno de python
├── .env                     ← Token de GitHub
├── .gitignore               ← Gitignore para protección de token
├── notebook.ipynb           ← Notebook con documentación y ejecución del script
├── README.md                ← Readme del proyecto
├── repos.csv                ← Lista de repositorios a analizar
├── requirements.txt         ← Librerías necesarias
├── script.py                ← Script principal del software
├── owner1_repo1/            ← Carpeta por cada repositorio procesado
│   ├── all_workflow_runs/
│   ├── failure_workflow_runs/
│   └── retry_workflow_runs/
```

## Pasos para preparar entorno y ejecutar software

### 1. Crear, activar entorno virtual y seleccionar kernel

#### En Windows:
```bash
python -m venv env
env\Scripts\activate
```

#### En macOS/Linux:
```bash
python3 -m venv env
source env/bin/activate
```

#### Seleccionar kernel en notebook.ipynb

### 2. Instalar dependencias

Con el entorno virtual activado, ejecutar:

```bash
pip install -r requirements.txt
```

> Esto instalará:
> - `requests`: Para interactuar con la API de GitHub
> - `python-dotenv`: Para cargar variables de entorno desde `.env`
> - `notebook`: Para trabajar con jupyter notebook

### 3. Crear el archivo `.env`

En la raíz del proyecto, crear archivo llamado `.env` con el siguiente contenido:

```
GITHUB_TOKEN=token
```

> El token debe tener permisos para leer información pública de los repositorios (permisos de scope `repo`).

### 4. Crear el archivo `.gitignore`

En la raíz del proyecto, crear archivo llamado `.gitignore` con el siguiente contenido:

```
.env
__pycache__/
*.pyc
env/
```

> Esto asegurará que no se suba ningún contenido sensible a ningún repositorio.

### 5. Verificar o editar `repos.csv`

El archivo `repos.csv` ya viene con **10 repositorios de ejemplo**, uno por línea en el siguiente formato:

```csv
owner,repo
vercel,next.js
...,...
```

Es posible **editar este archivo** para agregar o quitar repositorios a procesar, pero no debe ser eliminado, **debe existir** en la raíz del proyecto y seguir el formato `owner,repo`.

### 6. Verificar o editar el número de workflow runs que extraeremos por repositorio (`MAX_RUNS`)

En el archivo `script.py`, se encuentra una variable al principio:

```python
MAX_RUNS = 100
```

Es posible reducirla o aumentarla. En el estado actual, el software extraerá 100 workflow runs por cada uno de los repositorios en repos.csv.

## ¿Cómo ejecutar el script?

Abrir el archivo `notebook.ipynb` y ejecutar la celda con:

```python
!python script.py
```

Esto iniciará la extracción y guardado de data de todos los repositorios listados en `repos.csv`.
