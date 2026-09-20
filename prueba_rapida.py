"""Prueba rápida de los componentes de EyeSync: gamma, toast y webcam (12 s)."""
import time

print("[1/3] Gamma de pantalla: aplicar y restaurar (la pantalla puede titilar)...")
from eyesync.vision import GammaPantalla, ajustes_por_miopia

g = GammaPantalla()
if g.guardar_original():
    ajustes = ajustes_por_miopia(2.5)
    ok = g.aplicar(**ajustes)
    time.sleep(1.0)
    g.restaurar()
    print(f"    aplicar: {ok} {ajustes} -> restaurado")
else:
    print("    no se pudo leer la rampa de gamma")

print("[2/3] Toast de Windows (debería aparecer una notificación)...")
from eyesync.descansos import notificar

notificar("EyeSync", "Prueba de notificación: si lees esto, los avisos funcionan.")
time.sleep(1.0)

print("[3/3] Webcam: 12 segundos midiendo EAR y parpadeos...")
from eyesync.detector import DetectorParpadeo

d = DetectorParpadeo(camara=0)
d.start()
t0 = time.time()
while time.time() - t0 < 12 and d.is_alive():
    time.sleep(1)
    s = d.snapshot()
    ear = "--" if s["ear"] is None else f"{s['ear']:.3f}"
    print(f"    ear={ear} ppm={s['ppm']} rostro={s['rostro']} umbral={d.umbral:.3f}")
d.parar()
d.join(timeout=5)
if d.error:
    print(f"    ERROR webcam: {d.error}")
else:
    s = d.snapshot()
    print(f"    Webcam OK. Parpadeos en la prueba: {s['ppm']} (ventana 60 s)")
print("LISTO")
