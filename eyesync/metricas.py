"""Registro de sesiones y eventos en SQLite + reporte de la métrica clave."""
import sqlite3
from datetime import datetime, timedelta

from eyesync import config

DB = config.DATOS / "eyesync.db"


def _con():
    config.DATOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS sesiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inicio TEXT NOT NULL,
        fin TEXT,
        miopia REAL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sesion_id INTEGER,
        ts TEXT NOT NULL,
        tipo TEXT NOT NULL,
        valor REAL)""")
    return con


def iniciar_sesion(miopia):
    con = _con()
    try:
        cur = con.execute(
            "INSERT INTO sesiones (inicio, miopia) VALUES (?, ?)",
            (datetime.now().isoformat(timespec="seconds"), miopia),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def registrar(sesion_id, tipo, valor=None):
    con = _con()
    try:
        con.execute(
            "INSERT INTO eventos (sesion_id, ts, tipo, valor) VALUES (?, ?, ?, ?)",
            (sesion_id, datetime.now().isoformat(timespec="seconds"), tipo, valor),
        )
        con.commit()
    finally:
        con.close()


def cerrar_sesion(sesion_id):
    con = _con()
    try:
        con.execute(
            "UPDATE sesiones SET fin = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), sesion_id),
        )
        con.commit()
    finally:
        con.close()


def resumen_sesion(sesion_id):
    con = _con()
    try:
        filas = con.execute(
            "SELECT tipo, COUNT(*) FROM eventos WHERE sesion_id = ? GROUP BY tipo",
            (sesion_id,),
        ).fetchall()
        return {tipo: n for tipo, n in filas}
    finally:
        con.close()


def _fmt_horas(horas):
    h = int(horas)
    m = int(round((horas - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h}h {m:02d}m"


def _racha_sin_alerta(dia, alertas_fatiga, sesiones):
    """Mayor tramo continuo del día dentro de sesiones sin alerta de fatiga (h)."""
    tramos = []
    for inicio, fin in sesiones:
        if not fin or not inicio.startswith(dia):
            continue
        try:
            t0 = datetime.fromisoformat(inicio)
            t1 = datetime.fromisoformat(fin)
        except ValueError:
            continue
        tramos.append((t0, t1))
    if not tramos:
        return 0.0
    alertas = []
    for ts in alertas_fatiga:
        try:
            alertas.append(datetime.fromisoformat(ts))
        except ValueError:
            continue
    mejor = 0.0
    for t0, t1 in tramos:
        puntos = [t0] + [a for a in alertas if t0 < a < t1] + [t1]
        for a, b in zip(puntos, puntos[1:]):
            mejor = max(mejor, (b - a).total_seconds())
    return mejor / 3600


def imprimir_reporte(dias=14):
    con = _con()
    try:
        desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        sesiones = con.execute(
            "SELECT inicio, fin FROM sesiones WHERE inicio >= ? ORDER BY inicio",
            (desde,),
        ).fetchall()
        eventos = con.execute(
            "SELECT substr(ts,1,10) dia, tipo, COUNT(*) FROM eventos "
            "WHERE ts >= ? GROUP BY dia, tipo",
            (desde,),
        ).fetchall()
        fatigas = con.execute(
            "SELECT substr(ts,1,10) dia, ts FROM eventos "
            "WHERE tipo = 'alerta_fatiga' AND ts >= ? ORDER BY ts",
            (desde,),
        ).fetchall()
    finally:
        con.close()

    horas_dia, minutos_dia = {}, {}
    for inicio, fin in sesiones:
        if not fin:
            continue
        try:
            t0 = datetime.fromisoformat(inicio)
            t1 = datetime.fromisoformat(fin)
        except ValueError:
            continue
        dia = t0.strftime("%Y-%m-%d")
        horas = (t1 - t0).total_seconds() / 3600
        horas_dia[dia] = horas_dia.get(dia, 0.0) + horas
        minutos_dia[dia] = minutos_dia.get(dia, 0.0) + horas * 60

    conteos = {}
    for dia, tipo, n in eventos:
        conteos.setdefault(dia, {})[tipo] = n
    fatigas_dia = {}
    for dia, ts in fatigas:
        fatigas_dia.setdefault(dia, []).append(ts)

    dias_con_datos = sorted(set(horas_dia) | set(conteos))
    if not dias_con_datos:
        print(f"(Sin datos en los últimos {dias} días: usá EyeSync un rato y volvé.)")
        return

    print(f"\nEyeSync - reporte de los últimos {dias} días")
    print("-" * 66)
    print(f"{'Día':<12}{'Horas cam':>10}{'Ppm prom.':>10}{'Fatiga':>8}{'Sin alerta':>14}")
    total_horas = total_sin_alerta = 0.0
    for dia in dias_con_datos:
        horas = horas_dia.get(dia, 0.0)
        total_horas += horas
        c = conteos.get(dia, {})
        ppm = c.get("parpadeo", 0) / minutos_dia[dia] if minutos_dia.get(dia) else 0.0
        n_fatiga = c.get("alerta_fatiga", 0)
        racha = _racha_sin_alerta(dia, fatigas_dia.get(dia, []), sesiones)
        total_sin_alerta += racha
        print(f"{dia:<12}{horas:>9.1f}h{ppm:>9.1f}{n_fatiga:>8}{_fmt_horas(racha):>14}")
    print("-" * 66)
    print(f"TOTAL: {_fmt_horas(total_horas)} de pantalla | "
          f"{_fmt_horas(total_sin_alerta)} sin alertas de fatiga ocular")
