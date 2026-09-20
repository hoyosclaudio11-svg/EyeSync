"""EyeSync - cuida tus ojos mientras trabajás.

MVP: detector de parpadeo por webcam, ajuste de brillo/contraste según
miopía y pausas cada 30 minutos con aviso.

    python main.py                 sesión normal
    python main.py --vista         ver la webcam con el EAR en vivo
    python main.py --reporte       informe de la métrica
    python main.py --sin-camara    solo pausas y ajuste de pantalla
"""
import argparse
import time

from eyesync import config, metricas
from eyesync.descansos import RecordadorDescansos, VigiaFatiga, notificar
from eyesync.detector import DetectorParpadeo
from eyesync.vision import GammaPantalla, ajustes_por_miopia


def _argumentos():
    p = argparse.ArgumentParser(description="EyeSync - salud visual frente a la pantalla")
    p.add_argument("--miopia", type=float, default=None, help="dioptrías de miopía")
    p.add_argument("--minutos-pausa", type=int, default=None,
                   help="minutos entre pausas (30)")
    p.add_argument("--camara", type=int, default=0, help="índice de la webcam (0)")
    p.add_argument("--vista", action="store_true",
                   help="mostrar ventana con la webcam y el EAR")
    p.add_argument("--sin-camara", action="store_true",
                   help="no usar webcam (solo pausas y ajuste de pantalla)")
    p.add_argument("--reporte", action="store_true",
                   help="mostrar el informe de la métrica y salir")
    p.add_argument("--duracion", type=int, default=None,
                   help="(para pruebas) cortar la sesión tras N segundos")
    return p.parse_args()


def _pedir_miopia(perfil):
    try:
        texto = input(
            "¿Cuántas dioptrías de miopía tenés? (0 si ninguna): "
        ).strip().replace(",", ".")
        valor = float(texto) if texto else 0.0
    except (ValueError, EOFError):
        valor = 0.0
    perfil["miopia"] = max(0.0, valor)
    config.guardar_perfil(perfil)


def _estado(det, recordador):
    cola = f"pausa en {recordador.minutos_restantes():4.1f} min"
    if det is None:
        return f"[EyeSync] cámara apagada | {cola}"
    s = det.snapshot()
    if s.get("recuperando"):
        return f"[EyeSync] cámara caída, reconectando... | {cola}"
    ear = "--" if s["ear"] is None else f"{s['ear']:.2f}"
    rostro = "sí" if s["rostro"] else "no"
    return f"[EyeSync] EAR {ear} | {s['ppm']:2d} parp/min | rostro {rostro} | {cola}"


def main():
    args = _argumentos()
    if args.reporte:
        metricas.imprimir_reporte()
        return

    perfil = config.cargar_perfil()
    if args.minutos_pausa:
        perfil["minutos_pausa"] = args.minutos_pausa
    if args.miopia is not None:
        perfil["miopia"] = args.miopia
    config.guardar_perfil(perfil)
    if perfil["miopia"] is None:
        _pedir_miopia(perfil)
    miopia = perfil["miopia"]

    # 1) Pantalla según la miopía
    gamma = GammaPantalla()
    ajustes = None
    if gamma.guardar_original():
        ajustes = ajustes_por_miopia(miopia or 0.0)
        if not gamma.aplicar(**ajustes):
            print("[EyeSync] El driver no dejó ajustar la gamma; sigo sin tocar la pantalla.")
            ajustes = None
    else:
        print("[EyeSync] No pude leer la gamma actual; sigo sin tocar la pantalla.")

    # 2) Detector de parpadeo
    det = None
    if not args.sin_camara:
        det = DetectorParpadeo(camara=args.camara, vista=args.vista)
        det.start()
        time.sleep(1.5)
        if det.error:
            print(f"[EyeSync] Webcam: {det.error}. Sigo con pausas y ajuste de pantalla.")
            det = None

    # 3) Registro, pausas y vigía de fatiga
    sesion_id = metricas.iniciar_sesion(miopia or 0.0)

    def _reg(tipo, valor=None):
        metricas.registrar(sesion_id, tipo, valor)

    if det is not None:
        det.on_parpadeo = lambda ear: _reg("parpadeo", ear)
        det.on_cierre_largo = lambda ear: _reg("cierre_largo", ear)
        det.on_entrecerrado = lambda ear: _reg("entrecerrado", ear)

    recordador = RecordadorDescansos(
        minutos=perfil["minutos_pausa"],
        segundos_descanso=perfil["segundos_descanso"],
        on_pausa=lambda: _reg("pausa"),
    )
    recordador.start()

    vigia = None
    if det is not None:
        vigia = VigiaFatiga(det, umbral_ppm=perfil["umbral_ppm_bajo"],
                            on_alerta=lambda tipo: _reg(tipo))
        vigia.start()

    notificar("EyeSync activo",
              f"Pausas cada {perfil['minutos_pausa']} min. Miopía: {miopia} dioptrías.")
    print("[EyeSync] Corriendo. Cerrá con Ctrl+C para guardar la sesión y ver el resumen.")
    if ajustes:
        print(f"[EyeSync] Pantalla ajustada por {miopia} dioptrías "
              f"(brillo x{ajustes['brillo']}, contraste x{ajustes['contraste']}).")
    print("[EyeSync] '--reporte' para la métrica | '--vista' para ver la cámara.\n")

    t0 = time.time()
    try:
        while True:
            time.sleep(1)
            print("\r" + _estado(det, recordador) + "   ", end="", flush=True)
            if args.duracion is not None and time.time() - t0 >= args.duracion:
                print("\n[EyeSync] Fin del tiempo de prueba.")
                break
    except KeyboardInterrupt:
        print()
    finally:
        print()
        if vigia is not None:
            vigia.parar()
        recordador.parar()
        if det is not None:
            det.parar()
            det.join(timeout=5)
        gamma.restaurar()
        metricas.cerrar_sesion(sesion_id)
        r = metricas.resumen_sesion(sesion_id)
        minutos = (time.time() - t0) / 60
        print(f"[EyeSync] Sesión de {minutos:.0f} min guardada | "
              f"{r.get('parpadeo', 0)} parpadeos | {r.get('cierre_largo', 0)} aprietes | "
              f"{r.get('pausa', 0)} pausas avisadas | "
              f"{r.get('alerta_fatiga', 0)} alertas de fatiga")


if __name__ == "__main__":
    main()
