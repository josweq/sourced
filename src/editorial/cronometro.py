"""Cronometro de guion para lectura en voz alta."""
import re


DEFAULT_PPM = 160


def texto_cronometrable(texto: str) -> str:
    """Quita marcas de produccion que no se leen en voz alta."""
    limpio = re.sub(r"\[(?:VO|SOT)[^\]]*\]", " ", texto or "", flags=re.I)
    limpio = re.sub(r"\([^)]*\)", " ", limpio)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    return limpio


def contar_palabras(texto: str) -> int:
    return len(re.findall(r"\b[\wáéíóúÁÉÍÓÚñÑüÜ]+(?:[-'][\wáéíóúÁÉÍÓÚñÑüÜ]+)?\b", texto or ""))


def estimar_segundos(texto: str, ppm: int = DEFAULT_PPM) -> int:
    ppm = max(1, int(ppm or DEFAULT_PPM))
    palabras = contar_palabras(texto_cronometrable(texto))
    return round((palabras / ppm) * 60)


def estado_objetivo(segundos: int, minimo: int = 45, maximo: int = 60) -> str:
    if segundos < minimo:
        return "falta"
    if segundos > maximo:
        return "pasa"
    return "dentro"


def resumen_cronometro(texto: str, ppm: int = DEFAULT_PPM) -> dict:
    segundos = estimar_segundos(texto, ppm)
    estado = estado_objetivo(segundos)
    labels = {
        "falta": "falta para el objetivo",
        "pasa": "se pasa del objetivo",
        "dentro": "dentro del objetivo",
    }
    return {"ppm": int(ppm or DEFAULT_PPM), "segundos": segundos, "estado": estado,
            "texto": f"{segundos} s · {labels[estado]}"}
