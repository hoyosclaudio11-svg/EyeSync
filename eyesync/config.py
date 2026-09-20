"""Configuración y perfil de usuario de EyeSync (JSON en datos/)."""
import json
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent
DATOS = CARPETA / "datos"
PERFIL_JSON = DATOS / "perfil.json"

DEFAULTS = {
    "miopia": None,           # dioptrías (float); None = preguntar la primera vez
    "minutos_pausa": 30,      # cada cuántos minutos avisar la pausa
    "segundos_descanso": 20,  # duración sugerida del descanso (regla 20-20-20)
    "umbral_ppm_bajo": 8,     # menos parpadeos por minuto que esto, sostenido = fatiga
}


def cargar_perfil():
    PERFIL_JSON.parent.mkdir(parents=True, exist_ok=True)
    perfil = dict(DEFAULTS)
    if PERFIL_JSON.exists():
        try:
            perfil.update(json.loads(PERFIL_JSON.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass  # perfil roto: se regenera con los defaults
    return perfil


def guardar_perfil(perfil):
    PERFIL_JSON.parent.mkdir(parents=True, exist_ok=True)
    PERFIL_JSON.write_text(
        json.dumps(perfil, indent=2, ensure_ascii=False), encoding="utf-8"
    )
