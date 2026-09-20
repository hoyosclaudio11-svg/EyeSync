"""Ajuste de brillo y contraste por rampa de gamma (Windows), según la miopía.

Usa SetDeviceGammaRamp de GDI: funciona en cualquier monitor sin depender de
DDC/CI ni de drivers del fabricante. Guarda la rampa original y la restaura.
"""
import ctypes
from ctypes import c_ushort


def ajustes_por_miopia(dioptrias):
    """Mapea dioptrías (0-8) a brillo/contraste/gamma.

    Pauta inicial (editable): a más dioptrías, menos brillo (menos
    deslumbramiento) y algo más de contraste para compensar. No es una
    prescripción médica.
    """
    d = max(0.0, min(float(dioptrias), 8.0)) / 8.0
    return {
        "brillo": round(1.0 - 0.15 * d, 3),      # 1.00 -> 0.85
        "contraste": round(1.0 + 0.15 * d, 3),   # 1.00 -> 1.15
        "gamma": round(1.0 + 0.05 * d, 3),       # 1.00 -> 1.05 (blanco más suave)
    }


class GammaPantalla:
    """Guarda la rampa de gamma original y permite aplicar/restaurar ajustes."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self._dc = self.user32.GetDC(0)
        self._original = None
        self.aplicada = False

    def guardar_original(self):
        rampa = (c_ushort * 768)()
        if self.gdi32.GetDeviceGammaRamp(self._dc, rampa):
            self._original = list(rampa)
        return self._original is not None

    def aplicar(self, brillo=1.0, contraste=1.0, gamma=1.0):
        rampa = (c_ushort * 768)()
        for i in range(256):
            x = i / 255.0
            y = (x - 0.5) * contraste + 0.5
            y = min(1.0, max(0.0, y)) ** gamma
            valor = min(65535, max(0, int(y * 255 * brillo) * 257))
            for c in range(3):
                rampa[c * 256 + i] = valor
        ok = bool(self.gdi32.SetDeviceGammaRamp(self._dc, rampa))
        self.aplicada = ok
        return ok

    def restaurar(self):
        if self._original is None:
            return True
        rampa = (c_ushort * 768)(*self._original)
        ok = bool(self.gdi32.SetDeviceGammaRamp(self._dc, rampa))
        self.aplicada = False
        return ok
