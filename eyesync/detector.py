"""Detector de parpadeos con webcam: MediaPipe FaceMesh + Eye Aspect Ratio."""
import math
import threading
import time
from collections import deque

import cv2
import mediapipe as mp

# Landmarks de los ojos en FaceMesh (6 puntos por ojo para calcular el EAR)
OJO_DERECHO = [33, 160, 158, 133, 153, 144]
OJO_IZQUIERDO = [362, 385, 387, 263, 373, 380]

DURACION_PARPADEO = 0.5      # s: un cierre más largo que esto es un parpadeo lento
DURACION_CIERRE_LARGO = 1.2  # s: ojos cerrados/apretados más tiempo = posible apriete
SEGUNDOS_ENTRECERRADOS = 3.0 # s sostenidos con el ojo a medio cerrar = señal de fatiga
FRAMES_CALIBRACION = 45
VENTANA_PPM = 60             # s: ventana para contar parpadeos por minuto


def _ear(puntos, ancho, alto, indices):
    """Eye Aspect Ratio de un ojo a partir de sus 6 landmarks."""
    p = [(puntos[i].x * ancho, puntos[i].y * alto) for i in indices]
    vertical = math.dist(p[1], p[5]) + math.dist(p[2], p[4])
    horizontal = math.dist(p[0], p[3])
    return vertical / (2 * horizontal) if horizontal > 0 else 1.0


class DetectorParpadeo(threading.Thread):
    """Corre la webcam en un hilo y expone EAR, parpadeos por minuto y eventos.

    Callbacks (se llaman desde este hilo): on_parpadeo(ear),
    on_cierre_largo(ear), on_entrecerrado(ear).
    """

    def __init__(self, camara=0, vista=False,
                 on_parpadeo=None, on_cierre_largo=None, on_entrecerrado=None):
        super().__init__(daemon=True)
        self.camara = camara
        self.vista = vista
        self.on_parpadeo = on_parpadeo
        self.on_cierre_largo = on_cierre_largo
        self.on_entrecerrado = on_entrecerrado

        self.activo = True
        self.error = None
        self.ear = None          # EAR actual (promedio de los dos ojos)
        self.ppm = 0             # parpadeos en los últimos 60 s
        self.rostro = False
        self.umbral = 0.19       # umbral de "ojo cerrado"; se recalibra al arrancar
        self._base = 0.30        # EAR típico con el ojo abierto en esta sesión

        self._parpadeos = deque()       # timestamps de parpadeos
        self._cierres_largos = deque()  # timestamps de aprietes
        self._entrecerrados = deque()   # timestamps de tramos entrecerrados
        self._lock = threading.Lock()

    # ---------- consultas desde otros hilos ----------
    def snapshot(self):
        ahora = time.time()
        with self._lock:
            while self._parpadeos and ahora - self._parpadeos[0] > VENTANA_PPM:
                self._parpadeos.popleft()
            while self._cierres_largos and ahora - self._cierres_largos[0] > 120:
                self._cierres_largos.popleft()
            while self._entrecerrados and ahora - self._entrecerrados[0] > 300:
                self._entrecerrados.popleft()
            self.ppm = len(self._parpadeos)
            return {
                "ear": self.ear,
                "ppm": self.ppm,
                "rostro": self.rostro,
                "umbral": self.umbral,
                "cierres_largos": list(self._cierres_largos),
                "entrecerrados": list(self._entrecerrados),
            }

    def parar(self):
        self.activo = False

    # ---------- hilo de captura ----------
    def run(self):
        cap = cv2.VideoCapture(self.camara, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camara)
        if not cap.isOpened():
            self.error = "no se pudo abrir la webcam"
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        calibracion = []
        t_cierre = None
        t_entrecerrado = None

        try:
            while self.activo:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                alto, ancho = frame.shape[:2]
                res = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                ahora = time.time()

                if not res.multi_face_landmarks:
                    self.rostro = False
                    self.ear = None
                    t_cierre = None
                    t_entrecerrado = None
                else:
                    self.rostro = True
                    puntos = res.multi_face_landmarks[0].landmark
                    ear = (_ear(puntos, ancho, alto, OJO_DERECHO)
                           + _ear(puntos, ancho, alto, OJO_IZQUIERDO)) / 2
                    self.ear = ear

                    if len(calibracion) < FRAMES_CALIBRACION:
                        calibracion.append(ear)
                        if len(calibracion) == FRAMES_CALIBRACION:
                            # EAR típico de ojo abierto: percentil 25 ignorando cierres
                            abiertos = sorted(e for e in calibracion if e > 0.15) \
                                or sorted(calibracion)
                            self._base = abiertos[len(abiertos) // 4]
                            self.umbral = max(0.10, min(0.25, self._base * 0.75))
                    else:
                        t_cierre, t_entrecerrado = self._evaluar(
                            ear, ahora, t_cierre, t_entrecerrado)

                if self.vista:
                    s = self.snapshot()
                    texto = (f"EAR {'--' if self.ear is None else format(self.ear, '.2f')}"
                             f"  umbral {self.umbral:.2f}  {s['ppm']} ppm")
                    cv2.putText(frame, texto, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    estado = "calibrando..." if len(calibracion) < FRAMES_CALIBRACION \
                        else "activo (Q: cerrar solo la vista)"
                    cv2.putText(frame, estado, (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
                    cv2.imshow("EyeSync", frame)
                    if cv2.getWindowProperty("EyeSync", cv2.WND_PROP_VISIBLE) < 1:
                        self.vista = False
                    elif cv2.waitKey(1) & 0xFF == ord("q"):
                        self.vista = False
                    if not self.vista:
                        cv2.destroyAllWindows()
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def _evaluar(self, ear, ahora, t_cierre, t_entrecerrado):
        """Máquina de estados de apertura; devuelve los timestamps actualizados."""
        if ear < self.umbral:
            # Ojo cerrado: se resuelve cuando vuelve a abrir
            if t_cierre is None:
                t_cierre = ahora
            return t_cierre, None

        if t_cierre is not None:
            duracion = ahora - t_cierre
            with self._lock:
                self._parpadeos.append(ahora)
                if duracion >= DURACION_CIERRE_LARGO:
                    self._cierres_largos.append(ahora)
                    cb = self.on_cierre_largo
                else:
                    cb = self.on_parpadeo
            if cb:
                cb(ear)
            t_cierre = None

        # Ojos a medio cerrar de forma sostenida (fatiga / entrecerrados)
        if ear < self._base * 0.85:
            if t_entrecerrado is None:
                t_entrecerrado = ahora
            elif ahora - t_entrecerrado >= SEGUNDOS_ENTRECERRADOS:
                with self._lock:
                    self._entrecerrados.append(ahora)
                if self.on_entrecerrado:
                    self.on_entrecerrado(ear)
                t_entrecerrado = ahora  # uno nuevo cada 3 s sostenidos
        else:
            t_entrecerrado = None
        return t_cierre, t_entrecerrado
