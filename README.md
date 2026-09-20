# EyeSync (MVP)

App de escritorio que cuida tus ojos mientras trabajás: detecta parpadeos con la
webcam, ajusta brillo y contraste según tu miopía, y te avisa cuándo hacer
pausas — y cuándo ve señales de fatiga ocular.

## El problema en criollo

En la pantalla no parpadeás como la gente. Mirás la compu, se te olvida
parpadear, los ojos se te secan, los apretás, y a los años de eso tenés vista
cansada, ojo seco y dolores de cabeza. No te das cuenta porque pasa de a
poquito. EyeSync es un vigilante mirándote la cara por la webcam:

- **Cuenta cuánto parpadeás** — y si dejás de hacerlo como corresponde, avisa
  antes de que lo sientas vos.
- **Te patea de la silla cada 30 minutos** — "mirá lejos 20 segundos", la regla
  de los oftalmólogos que nadie cumple porque nadie se acuerda.
- **Acomoda la pantalla a tu vista** según tu miopía, así no forzás.

En una frase: **es el que te acuerda que tenés ojos cuando vos te olvidaste.**
No reemplaza al oftalmólogo — te hace llegar mejor al día en que lo visitás.

## Qué hace este MVP

1. **Detector de parpadeo con webcam** — MediaPipe FaceMesh + Eye Aspect Ratio.
   Cuenta parpadeos por minuto, se calibra solo con los primeros segundos de uso
   y detecta cierres fuertes sostenidos (apretar los ojos) y ojos entrecerrados
   por mucho rato.
2. **Calibración de pantalla según miopía** — pregunta tus dioptrías una vez y
   aplica brillo/contraste/gamma por rampa de video (se restaura sola al salir).
3. **Pausas cada 30 minutos** — notificación de Windows con la regla 20-20-20
   (mirar a 6 metros durante 20 segundos).

Además: vigilante de fatiga (parpadeo lento sostenido, aprietes repetidos,
entrecerrados) con notificaciones, y registro de todo en SQLite.

## Cómo se mide que funciona

```
python main.py --reporte
```

Por día: horas de cámara, parpadeos por minuto promedio, alertas de fatiga y la
métrica clave: **horas de pantalla sin alertas de fatiga ocular**.

## Cómo empezar

Doble clic en `iniciar.bat` (la primera vez crea el entorno e instala
dependencias). Pregunta la miopía y arranca.

| Comando | Qué hace |
|---|---|
| `--miopia 2.5` | pasa las dioptrías sin preguntar |
| `--vista` | muestra la webcam con el EAR en vivo (Q para cerrar) |
| `--minutos-pausa 30` | cambia el intervalo de pausas |
| `--sin-camara` | solo pausas + ajuste de pantalla |
| `--reporte` | informe de la métrica |
| `--camara 1` | usa otra webcam |

## Privacidad

Todo corre en tu máquina: la webcam nunca sale de ella y no hay conexión a
internet salvo la primera instalación de paquetes. Los datos quedan en
`datos/eyesync.db`.

## Qué quedó fuera del MVP

- Detección de *frotarse* los ojos (requiere seguimiento de manos; hoy detecta
  apretar los ojos y entrecerrarlos).
- Aprendizaje de patrones a largo plazo y "distancia virtual".
- Ajuste de brillo por DDC/CI en monitores externos (hoy ajusta por gamma de
  video, que funciona en cualquier monitor).
