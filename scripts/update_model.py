import os
import subprocess

# Archivo donde guardamos el estado
STATUS_FILE = "training_status.txt"

# Rutas de scripts
PREPARE_SCRIPT = "scripts/prepare_dataset.py"
FINE_TUNE_SCRIPT = "scripts/fine_tune.py"

def set_status(status: str):
    """Escribe el estado actual del entrenamiento."""
    with open(STATUS_FILE, "w") as f:
        f.write(status)

def run_script(script_path):
    """Ejecuta un script Python y muestra logs."""
    print(f"[RUN] {script_path}")
    result = subprocess.run(["python", script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Error ejecutando {script_path}")

if __name__ == "__main__":
    try:
        # Estado inicial
        set_status("training_started")
        print("[INFO] Entrenamiento iniciado...")

        # Paso 1: Preparar dataset
        run_script(PREPARE_SCRIPT)

        # Paso 2: Fine-tuning
        run_script(FINE_TUNE_SCRIPT)

        # Estado final: éxito
        set_status("training_completed")
        print("[OK] Modelo actualizado y listo para usarse.")

    except Exception as e:
        set_status("training_failed")
        print(f"[ERROR] Entrenamiento fallido: {e}")
