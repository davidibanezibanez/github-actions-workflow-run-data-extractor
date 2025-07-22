import os
import re
import json
import requests
import base64
import shutil
import time
import csv
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Configuración global

load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN no encontrado. Asegúrate de tener un archivo .env con la variable.")

MAX_RUNS = 100
REPOS_CSV = "repos.csv"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Funciones Utilitarias

def read_repositories(csv_path):
    repos = []
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            owner = row.get("owner")
            repo = row.get("repo")
            if owner and repo:
                repos.append((owner.strip(), repo.strip()))
    return repos

def sanitize_filename(name, max_length=100):
    name = re.sub(r"[^a-zA-Z0-9 \-_]", "", name)
    return name.strip().replace(" ", "_")[:max_length]

def create_run_dir(base_dir, run_id, run_name):
    dir_path = base_dir / f"{run_id}_{sanitize_filename(run_name)}"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_text(data, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)

def save_logs_zip(run_id, output_path, base_api_url):
    url = f"{base_api_url}/actions/runs/{run_id}/logs"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        else:
            print(f"No se pudieron descargar los logs para run {run_id}. Código: {resp.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error al descargar logs para run {run_id}: {e}")
    return False

def get_file_content(owner, repo, path, ref=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref} if ref else {}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except requests.exceptions.RequestException as e:
        print(f"Error obteniendo archivo YAML {path}: {e}")
    return None

def get_workflow_runs(base_api_url, max_runs=None):
    runs = []
    page = 1
    while True:
        url = f"{base_api_url}/actions/runs"
        params = {"per_page": 100, "page": page}
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"Error en página {page}. Código: {resp.status_code}")
                break
            data = resp.json().get("workflow_runs", [])
            if not data:
                break
            runs.extend(data)
            if max_runs and len(runs) >= max_runs:
                break
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo workflow runs: {e}")
            break
    return runs[:max_runs] if max_runs else runs

def get_jobs_json(base_api_url, run_id):
    url = f"{base_api_url}/actions/runs/{run_id}/jobs"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"No se pudo obtener jobs para run {run_id}. Código: {resp.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener jobs para run {run_id}: {e}")
    return None

def get_run_detail(base_api_url, run_id):
    url = f"{base_api_url}/actions/runs/{run_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"No se pudo obtener detalle del run {run_id}. Código: {resp.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener detalle de run {run_id}: {e}")
    return None

# Ejecución principal

if not GITHUB_TOKEN:
    raise EnvironmentError("La variable de entorno GITHUB_TOKEN no está definida.")

repositories = read_repositories(REPOS_CSV)

for OWNER, REPO in repositories:
    print(f"\n==> Procesando repositorio: {OWNER}/{REPO}")
    BASE_API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"
    OUTPUT_DIR = Path(f"{OWNER}_{REPO}")
    ALL_DIR = OUTPUT_DIR / "all_workflow_runs"
    FAILURE_DIR = OUTPUT_DIR / "failure_workflow_runs"
    RETRY_DIR = OUTPUT_DIR / "retry_workflow_runs"

    ALL_DIR.mkdir(parents=True, exist_ok=True)
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    RETRY_DIR.mkdir(parents=True, exist_ok=True)

    workflow_runs = get_workflow_runs(BASE_API_URL, max_runs=MAX_RUNS)
    print(f"{len(workflow_runs)} workflow runs encontrados.")

    for run in workflow_runs:
        run_id = run["id"]
        run_name = run["name"]
        run_attempt = run.get("run_attempt", 1)
        run_conclusion = run.get("conclusion", "")

        print(f"\nProcesando run {run_id} - {run_name} (attempt: {run_attempt}, conclusion: {run_conclusion})")

        run_detail = get_run_detail(BASE_API_URL, run_id)
        jobs_data = get_jobs_json(BASE_API_URL, run_id)

        if not run_detail or not jobs_data:
            print("Run omitido por error en metadata.")
            continue

        workflow_path = run_detail.get("path")
        head_sha = run_detail.get("head_sha")
        yaml_content = get_file_content(OWNER, REPO, workflow_path, head_sha) if workflow_path else None
        yaml_filename = os.path.basename(workflow_path) if workflow_path else None

        all_dir = create_run_dir(ALL_DIR, run_id, run_name)
        save_json(run_detail, all_dir / "workflow_run.json")
        save_json(jobs_data, all_dir / "jobs.json")
        if yaml_content and yaml_filename:
            save_text(yaml_content, all_dir / yaml_filename)

        logs_zip_path = all_dir / "logs.zip"
        if not save_logs_zip(run_id, logs_zip_path, BASE_API_URL):
            print("No se guardaron logs.zip, run omitido en copias adicionales.")
            continue

        if run_conclusion == "failure":
            failure_dir = create_run_dir(FAILURE_DIR, run_id, run_name)
            shutil.copytree(all_dir, failure_dir, dirs_exist_ok=True)

        if run_attempt > 1:
            retry_dir = create_run_dir(RETRY_DIR, run_id, run_name)
            shutil.copytree(all_dir, retry_dir, dirs_exist_ok=True)

        time.sleep(1)

print("\nExtracción completada para todos los repositorios.")
