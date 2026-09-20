"""Pausas programadas, notificaciones de Windows y vigilancia de fatiga."""
import threading
import time

try:
    from winotify import Notification, audio
    _HAY_WINOTIFY = True
except ImportError:
    _HAY_WINOTIFY = False

APP = "EyeSync"


def notificar(titulo, mensaje):
    """Toast de Windows; si falla, cae a la consola."""
    if _HAY_WINOTIFY:
        try:
            n = Notification(app_id=APP, title=titulo, msg=mensaje, duration="long")
            n.set_audio(audio.Silent, loop=False)
            n.show()
            return
        except Exception:
            pass
    print(f"\n[{APP}] {titulo} - {mensaje}")


class RecordadorDescansos(threading.Thread):
    """Avisa pausa cada N minutos (regla 20-20-20 adaptada)."""

    def __init__(self, minutos=30, segundos_descanso=20, on_pausa=None):
        super().__init__(daemon=True)
        self.minutos = minutos
        self.segundos = segundos_descanso
        self.on_pausa = on_pausa
        self.activo = True
        self.proximo = time.time() + minutos * 60

    def run(self):
        while self.activo:
            if time.time() >= self.proximo:
                notificar(
                    "Hora de la pausa",
                    f"Mirá algo a 6 metros durante {self.segundos} segundos.",
                )
                if self.on_pausa:
                    self.on_pausa()
                self.proximo = time.time() + self.minutos * 60
            time.sleep(1)

    def parar(self):
        self.activo = False

    def minutos_restantes(self):
        return max(0.0, (self.proximo - time.time()) / 60)


class VigiaFatiga(threading.Thread):
    """Detecta señales de fatiga con la cámara y avisa (con enfriamiento)."""

    ENFRIAMIENTO = {"fatiga": 600, "apriete": 300, "entrecerrados": 300}  # s

    def __init__(self, detector, umbral_ppm=8, on_alerta=None):
        super().__init__(daemon=True)
        self.detector = detector
        self.umbral_ppm = umbral_ppm
        self.on_alerta = on_alerta  # on_alerta("alerta_fatiga" | "alerta_apriete" | ...)
        self.activo = True
        self._segundos_ppm_bajo = 0
        self._ultimo_aviso = {}

    def run(self):
        while self.activo:
            snap = self.detector.snapshot()
            ahora = time.time()

            # Parpadeo lento sostenido = posible fatiga
            if snap["rostro"] and snap["ppm"] < self.umbral_ppm:
                self._segundos_ppm_bajo += 10
            else:
                self._segundos_ppm_bajo = 0
            if self._segundos_ppm_bajo >= 180:
                self._avisar(
                    "fatiga", "Fatiga ocular",
                    f"Solo {snap['ppm']} parpadeos/min en los últimos minutos. "
                    "Hacé una pausa corta y mirá lejos.")
                self._segundos_ppm_bajo = 0

            # Aprieta los ojos: 2+ cierres fuertes en 2 minutos
            if len([t for t in snap["cierres_largos"] if ahora - t < 120]) >= 2:
                self._avisar(
                    "apriete", "Estás apretando los ojos",
                    "Detecté cierres fuertes repetidos. "
                    "Soltá la mandíbula y parpadeá despacio.")

            # Ojos entrecerrados sostenidos: 2+ tramos en 5 minutos
            if len([t for t in snap["entrecerrados"] if ahora - t < 300]) >= 2:
                self._avisar(
                    "entrecerrados", "Ojos entrecerrados",
                    "Los tenés muy entrecerrados hace rato. "
                    "¿Está bien el brillo? ¿La pantalla está muy cerca?")

            time.sleep(10)

    def _avisar(self, tipo, titulo, mensaje):
        ultimo = self._ultimo_aviso.get(tipo, 0)
        if time.time() - ultimo < self.ENFRIAMIENTO[tipo]:
            return
        self._ultimo_aviso[tipo] = time.time()
        notificar(titulo, mensaje)
        if self.on_alerta:
            self.on_alerta("alerta_" + tipo)

    def parar(self):
        self.activo = False
