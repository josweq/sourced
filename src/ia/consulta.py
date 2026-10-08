"""Preguntas en español con respuesta citada o abstención explícita (CU-02, CU-04, CU-05, T04, T06).

Tres rutas, decididas por código:
1. Cifras oficiales: si la pregunta nombra un indicador y un país del snapshot, responde con el dato
   anual del Banco Mundial (país, año, unidad, fuente) y aclara que no es una medición actual. Si piden
   un año que no existe, se abstiene y muestra el último disponible como contexto.
2. Entorno logístico (CU-05): contexto sectorial con noticias citadas y el indicador de exportaciones;
   nunca un puntaje de clientes ni una alerta regulatoria.
3. Noticias: búsqueda semántica con regla de abstención calibrada sobre 12 preguntas reales
   (2026-10-07): con multilingual-e5-small la mejor pregunta sin respuesta dio 0,860 y la peor con
   respuesta 0,855, así que el umbral solo no basta y se exige también una palabra de contenido común.
"""
from __future__ import annotations

import re
import time

import numpy as np

from src.ia.embeddings import vectorizar
from src.ia.guardian import INSTRUCCIONES_PROHIBIDAS, normalizar, tokens

UMBRAL_DIRECTO = 0.88
UMBRAL_CON_COINCIDENCIA = 0.84
MAX_RESULTADOS = 3
MARGEN_SECUNDARIOS = 0.03  # un resultado secundario debe estar cerca del mejor
# Palabras demasiado frecuentes en el corpus para contar como coincidencia de contenido.
VACIAS = {"panama", "panamenos", "panameno", "panamena", "sobre", "cual", "cuales", "cuanto",
          "cuantos", "cuando", "donde", "como", "esta", "este", "estos", "hace", "segun", "noticia",
          "noticias", "dice", "dicen", "pasa", "paso", "tiene", "tienen", "puede", "hubo", "fueron",
          # Palabras de tiempo: «¿hubo sismos esta semana?» no debe coincidir con «Semana de la RSE».
          "semana", "semanas", "ayer", "manana", "ahora", "actual", "ultimo", "ultima", "ultimos",
          "ultimas", "reciente", "recientes", "dias", "meses", "anos"}

INDICADORES = {
    "FP.CPI.TOTL.ZG": ("inflacion", "precios al consumidor", "ipc"),
    "NY.GDP.MKTP.KD.ZG": ("pib", "crecimiento economico", "crecimiento del pib", "producto interno"),
    "SL.UEM.TOTL.ZS": ("desempleo", "desocupacion"),
    "SP.POP.TOTL": ("poblacion", "habitantes"),
    "IT.NET.USER.ZS": ("internet",),
    "NE.EXP.GNFS.ZS": ("exportaciones",),
}
PAISES = {
    "PAN": ("panama",), "CRI": ("costa rica",), "COL": ("colombia",),
    "DOM": ("republica dominicana", "dominicana"), "MEX": ("mexico",), "GTM": ("guatemala",),
}
NOMBRES_PAIS = {"PAN": "Panamá", "CRI": "Costa Rica", "COL": "Colombia", "DOM": "República Dominicana",
                "MEX": "México", "GTM": "Guatemala"}
# Países que la gente puede nombrar pero que el snapshot no incluye: se abstiene en vez de asumir Panamá.
PAISES_FUERA = ("argentina", "bolivia", "brasil", "chile", "ecuador", "el salvador", "honduras", "nicaragua",
                "paraguay", "peru", "uruguay", "venezuela", "cuba", "haiti", "estados unidos", "eeuu",
                "espana", "canada", "china", "japon", "jamaica", "puerto rico", "belice")
LOGISTICA = re.compile(r"\b(logistic\w*|canal|puerto\w*|navier\w*|carga|transito\w*|buques?)\b")
ENTORNO = re.compile(r"\b(senales?|entorno|sector\w*|monitorear|revisar)\b")


def _cifra(valor: float, unidad: str) -> str:
    if "persona" in (unidad or ""):
        return f"{valor:,.0f}".replace(",", ".")
    return f"{valor:.1f}".replace(".", ",")


def _detectar(pregunta_norm: str, tabla: dict) -> str | None:
    for clave, alias in tabla.items():
        if any(re.search(rf"\b{re.escape(a)}\b", pregunta_norm) for a in alias):
            return clave
    return None


def _ruta_indicador(db, pregunta_norm: str) -> dict | None:
    indicador = _detectar(pregunta_norm, INDICADORES)
    if not indicador:
        return None
    pais = _detectar(pregunta_norm, PAISES)
    fuera = next((p for p in PAISES_FUERA if re.search(rf"\b{p}\b", pregunta_norm)), None)
    if not pais and fuera:
        return {"estado": "abstencion", "metodo": "indicador",
                "respuesta": (f"El snapshot no incluye datos de {fuera.title()}: solo Panamá, Costa Rica, Colombia, "
                              "República Dominicana, México y Guatemala. No se responde con otro país."),
                "afirmaciones": [], "vacios": [f"Serie oficial de {fuera.title()}: fuera del paquete de datos."]}
    asumido = pais is None
    pais = pais or "PAN"
    anio_pedido = next((int(a) for a in re.findall(r"\b(20\d\d|19\d\d)\b", pregunta_norm)), None)
    pide_actual = bool(re.search(r"\b(hoy|actual\w*|ahora|este ano|esta semana|este mes)\b", pregunta_norm))
    filas = db.execute(
        "SELECT id, anio, valor, unidad, fuente_url FROM indicadores "
        "WHERE pais_iso3=? AND indicador_id=? ORDER BY anio DESC", (pais, indicador)).fetchall()
    con_valor = [f for f in filas if f["valor"] is not None]
    if not con_valor:
        return {"estado": "abstencion", "metodo": "indicador",
                "respuesta": f"No hay valores de {indicador} para {NOMBRES_PAIS[pais]} en el snapshot.",
                "afirmaciones": [], "vacios": ["Serie oficial sin datos en el snapshot."]}
    ultimo = con_valor[0]
    nombre = NOMBRES_PAIS[pais]

    def afirmacion(f, tipo="hecho"):
        return {"texto": f"{nombre}, {f['anio']}: {_cifra(f['valor'], f['unidad'])} ({f['unidad']}). "
                         f"Dato anual del Banco Mundial; no es una medición actual.",
                "tipo": tipo, "cita": {"tipo": "indicador", "id": f["id"], "campo": "valor",
                                       "fuente": "Banco Mundial", "url": f["fuente_url"],
                                       "indicador": indicador, "anio": f["anio"]}}

    if anio_pedido is not None:
        exacto = next((f for f in con_valor if f["anio"] == anio_pedido), None)
        if exacto:
            return {"estado": "respondida", "metodo": "indicador",
                    "respuesta": f"Dato oficial de {anio_pedido} en el snapshot (Banco Mundial):",
                    "afirmaciones": [afirmacion(exacto)], "vacios": []}
        return {"estado": "abstencion", "metodo": "indicador",
                "respuesta": (f"No hay dato de {anio_pedido} para {nombre} en el snapshot (la serie llega a "
                              f"{ultimo['anio']}). No se estima ni se inventa una cifra."),
                "afirmaciones": [afirmacion(ultimo, "contexto")],
                "vacios": [f"Dato oficial de {anio_pedido}: consultar la fuente primaria nacional."]}
    vacios = []
    if asumido:
        vacios.append("No indicaste país: se asumió Panamá.")
    if pide_actual:
        vacios.append("Se pidió un dato actual: el snapshot solo tiene series anuales; el último año es "
                      f"{ultimo['anio']}. Para hoy hace falta la fuente primaria nacional.")
    return {"estado": "respondida", "metodo": "indicador",
            "respuesta": "Dato oficial más reciente en el snapshot (Banco Mundial):",
            "afirmaciones": [afirmacion(ultimo)], "vacios": vacios}


MESES = {"enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "setiembre", "octubre", "noviembre", "diciembre"}


def _contenido(texto: str) -> set[str]:
    # Años, cifras y meses no son tema: «turistas en septiembre de 2026» no debe coincidir con
    # «temporada de cruceros 2026-2027» solo por el «2026».
    return {t for t in tokens(texto) if t not in VACIAS and t not in MESES and not t.isdigit()}


def _ruta_noticias(db, pregunta: str, *, vectorizador=vectorizar, solo_logistica: bool = False,
                   modo: str = "semantico") -> dict:
    filas = db.execute(
        "SELECT n.id, n.titulo, n.medio, n.url, n.fecha_publicacion, n.fecha_deteccion, n.tema, "
        "gn.grupo_id FROM noticias n LEFT JOIN grupo_noticias gn ON gn.noticia_id=n.id "
        "AND gn.snapshot_id=n.snapshot_id").fetchall()
    if solo_logistica:
        filas = [f for f in filas if f["tema"] == "logistica_canal" or LOGISTICA.search(normalizar(f["titulo"]))]
    if not filas:
        return {"estado": "abstencion", "metodo": "noticias", "respuesta": "No hay noticias en el snapshot para esta consulta.",
                "afirmaciones": [], "vacios": ["Sin noticias pertinentes."], "mejor_similitud": None}
    pregunta_contenido = _contenido(pregunta)
    if modo == "lexico":
        # Línea base sin IA (palabras-clave-v1): proporción de palabras de contenido de la pregunta que
        # aparecen en el titular; responde solo si hay al menos una. Mismas reglas de cifras y abstención.
        sims = np.array([len(pregunta_contenido & _contenido(f["titulo"])) / max(1, len(pregunta_contenido))
                         for f in filas], dtype="float32")
    else:
        if vectorizador is vectorizar:
            V = np.asarray(vectorizar([f["titulo"] for f in filas], tipo="passage", db=db), dtype="float32")
        else:
            V = np.asarray(vectorizador([f["titulo"] for f in filas], tipo="passage"), dtype="float32")
        # El año pesa demasiado en preguntas cortas: «sismos en 2024» se parecía más a «Premios Victoria 2024»
        # que a cualquier nota de sismos. Se busca por el tema; la fecha la juzga quien lee la cita.
        consulta_texto = re.sub(r"\b(19|20)\d\d\b", " ", pregunta).strip() or pregunta
        q = np.asarray(vectorizador([consulta_texto], tipo="query"), dtype="float32")[0]
        sims = V @ q
    orden = np.argsort(-sims, kind="stable")
    elegidas, vistos_grupo = [], set()
    for i in orden[:20]:
        s = float(sims[i]); f = filas[int(i)]
        if elegidas and s < elegidas[0][1] - MARGEN_SECUNDARIOS:
            break
        comun = pregunta_contenido & _contenido(f["titulo"])
        acepta = bool(comun) if modo == "lexico" else (s >= UMBRAL_DIRECTO or (s >= UMBRAL_CON_COINCIDENCIA and comun))
        if not acepta:
            continue
        if f["grupo_id"] and f["grupo_id"] in vistos_grupo:
            continue
        vistos_grupo.add(f["grupo_id"])
        elegidas.append((f, s, sorted(comun)))
        if len(elegidas) >= MAX_RESULTADOS:
            break
    mejor = float(sims[orden[0]])
    if not elegidas and not solo_logistica:
        return {"estado": "abstencion", "metodo": "noticias", "mejor_similitud": round(mejor, 3),
                "respuesta": ("No encontré evidencia en el snapshot para responder esto. "
                              "Para responder haría falta una fuente que trate el tema."),
                "afirmaciones": [], "vacios": ["Ninguna noticia del snapshot supera la regla de evidencia."]}
    if solo_logistica and not elegidas:
        elegidas = [(filas[int(i)], float(sims[i]), []) for i in orden[:MAX_RESULTADOS]]
    afirmaciones = []
    for f, s, comun in elegidas:
        medios = []
        if f["grupo_id"]:
            medios = sorted({r[0] for r in db.execute(
                "SELECT n.medio FROM grupo_noticias gn JOIN noticias n ON n.id=gn.noticia_id "
                "AND n.snapshot_id=gn.snapshot_id WHERE gn.grupo_id=?", (f["grupo_id"],))})
        fecha = f["fecha_publicacion"] or f["fecha_deteccion"] or ""
        afirmaciones.append({
            "texto": f"Según {f['medio']}: «{f['titulo']}». Basado únicamente en titular/metadatos.",
            "tipo": "declaracion",
            "cita": {"tipo": "noticia", "id": f["id"], "campo": "titulo", "medio": f["medio"],
                     "url": f["url"], "fecha": fecha},
            "similitud": round(s, 3), "coincide": comun,
            "medios_del_evento": medios,
        })
    return {"estado": "respondida", "metodo": "noticias", "mejor_similitud": round(mejor, 3),
            "respuesta": f"{len(afirmaciones)} noticia(s) del snapshot tratan el tema; ninguna confirma el hecho por sí sola.",
            "afirmaciones": afirmaciones,
            "vacios": ["Confirmar con la fuente primaria; repetición entre medios no equivale a corroboración."]}


def responder(db, pregunta: str, *, vectorizador=vectorizar, modo: str = "semantico") -> dict:
    """modo="lexico" es la línea base sin IA para el benchmark; la interfaz usa siempre "semantico"."""
    inicio = time.perf_counter()
    pregunta = (pregunta or "").strip()
    if not pregunta:
        raise ValueError("Escribe una pregunta")
    if len(pregunta) > 300:
        raise ValueError("La pregunta es demasiado larga (máximo 300 caracteres)")
    norm = normalizar(pregunta)
    if INSTRUCCIONES_PROHIBIDAS.search(norm):
        res = {"estado": "abstencion", "metodo": "proteccion",
               "respuesta": ("La pregunta contiene instrucciones para cambiar el comportamiento de Lupa. "
                             "Las reglas no cambian: no se afirma nada sin evidencia ni se ejecutan órdenes. "
                             "Reformula la pregunta sobre el tema que quieres investigar."),
               "afirmaciones": [], "vacios": []}
    elif LOGISTICA.search(norm) and ENTORNO.search(norm):
        res = _ruta_noticias(db, pregunta, vectorizador=vectorizador, solo_logistica=True, modo=modo)
        expo = _ruta_indicador(db, "exportaciones panama")
        if expo and expo["afirmaciones"]:
            res["afirmaciones"].append(expo["afirmaciones"][0])
        res.update({"estado": "contexto_sectorial", "metodo": "entorno_logistico",
                    "respuesta": ("Contexto sectorial del entorno logístico: señales públicas para revisar, "
                                  "no un puntaje de clientes ni una alerta regulatoria."),
                    "vacios": res.get("vacios", []) + ["Sin datos de cartera ni de clientes: el análisis de exposición no corresponde a este snapshot."]})
    else:
        res = _ruta_indicador(db, norm) or _ruta_noticias(db, pregunta, vectorizador=vectorizador, modo=modo)
    res["pregunta"] = pregunta
    res["latencia_ms"] = round((time.perf_counter() - inicio) * 1000)
    res["reglas"] = {"umbral_directo": UMBRAL_DIRECTO, "umbral_con_coincidencia": UMBRAL_CON_COINCIDENCIA,
                     "modelo": "palabras-clave-v1" if modo == "lexico" else "intfloat/multilingual-e5-small"}
    return res
