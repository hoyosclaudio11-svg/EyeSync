"""Diagnóstico: qué índice de cámara ve una cara ahora mismo."""
import math

import cv2
import mediapipe as mp

fm = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.5, min_tracking_confidence=0.5)

OJO_D = [33, 160, 158, 133, 153, 144]
OJO_I = [362, 385, 387, 263, 373, 380]


def ear(puntos, w, h, idx):
    p = [(puntos[i].x * w, puntos[i].y * h) for i in idx]
    v = math.dist(p[1], p[5]) + math.dist(p[2], p[4])
    hz = math.dist(p[0], p[3])
    return v / (2 * hz) if hz > 0 else 1.0


for idx in range(4):
    cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
    if not cap.isOpened():
        print(f"[{idx}] no se pudo abrir (ocupada o inexistente)")
        continue
    caras = 0
    ears = []
    for _ in range(20):
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        res = fm.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if res.multi_face_landmarks:
            caras += 1
            pts = res.multi_face_landmarks[0].landmark
            ears.append((ear(pts, w, h, OJO_D) + ear(pts, w, h, OJO_I)) / 2)
    cap.release()
    if caras > 0:
        print(f"[{idx}] CARA en {caras}/20 frames, EAR promedio {sum(ears)/len(ears):.2f}")
    else:
        print(f"[{idx}] abre pero sin cara ({caras}/20)")
print("fin diagnostico")
