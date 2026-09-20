"""Espera hasta que se registre el primer parpadeo y termina (para monitoreo)."""
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent / "datos" / "eyesync.db"


def total():
    con = sqlite3.connect(str(DB))
    try:
        return con.execute(
            "SELECT COUNT(*) FROM eventos WHERE tipo='parpadeo'").fetchone()[0]
    finally:
        con.close()


base = total()
while True:
    time.sleep(5)
    n = total()
    if n > base:
        print(f"PARPADEOS DETECTADOS: {n} en total (antes: {base})")
        break
