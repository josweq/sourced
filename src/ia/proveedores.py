"""Proveedores de redaccion con salida JSON validada."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
import urllib.error
import urllib.request


DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


class ProviderUnavailable(RuntimeError):
    """El proveedor configurado no esta disponible o no tiene credenciales."""


class ProviderResponseError(RuntimeError):
    """El proveedor respondio, pero no devolvio JSON valido."""


@dataclass
class CallRecord:
    proveedor: str
    modelo: str
    parametros: dict
    milisegundos: int
    tokens: dict
    version: str = ""


ULTIMA_LLAMADA: CallRecord | None = None


def proveedor_activo() -> str:
    return os.environ.get("LUPA_PROVEEDOR", "ollama").strip().lower() or "ollama"


def modelo_activo() -> str:
    return os.environ.get("LUPA_MODELO_REDACCION", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, body, {"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def validar_json(texto: str, esquema: dict | None) -> dict:
    try:
        data = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("El modelo no devolvio JSON valido") from exc
    if esquema:
        required = esquema.get("required", [])
        missing = [key for key in required if key not in data]
        if missing:
            raise ProviderResponseError("Faltan campos requeridos: " + ", ".join(missing))
    return data


def _record(proveedor: str, modelo: str, parametros: dict, started: float, tokens: dict, version: str = "") -> dict:
    global ULTIMA_LLAMADA
    ULTIMA_LLAMADA = CallRecord(proveedor, modelo, parametros,
                                round((time.perf_counter() - started) * 1000),
                                tokens, version)
    return {"proveedor": proveedor, "modelo": modelo, "version": version,
            "parametros": parametros, "tokens": tokens, "milisegundos": ULTIMA_LLAMADA.milisegundos}


def generar_ollama(prompt: str, esquema: dict | None, *, timeout: int = 120) -> dict:
    host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")
    modelo = modelo_activo()
    parametros = {"temperature": 0.2, "num_ctx": 4096, "seed": 7, "think": False}
    payload = {"model": modelo, "prompt": prompt, "format": esquema or "json",
               "stream": False, "think": False, "options": parametros}
    started = time.perf_counter()
    try:
        raw = _post_json(f"{host}/api/generate", payload, timeout=timeout)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise ProviderUnavailable("Ollama no responde en " + host) from exc
    data = validar_json(raw.get("response", "{}"), esquema)
    meta = _record("ollama", modelo, parametros, started,
                   {"prompt": raw.get("prompt_eval_count"), "completion": raw.get("eval_count")},
                   raw.get("model", modelo))
    data["_meta_modelo"] = meta
    return data


def generar_openai_compat(prompt: str, esquema: dict | None, *, timeout: int = 120) -> dict:
    base = os.environ.get("LUPA_BASE_URL", "").strip().rstrip("/")
    key = os.environ.get("LUPA_API_KEY", "").strip()
    if not base or not key:
        raise ProviderUnavailable("Proveedor compatible apagado: falta LUPA_BASE_URL o LUPA_API_KEY")
    modelo = modelo_activo()
    parametros = {"temperature": 0.2}
    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        **parametros,
    }
    if esquema:
        payload["response_format"] = {"type": "json_object"}
    started = time.perf_counter()
    try:
        raw = _post_json(f"{base}/chat/completions", payload,
                         {"Authorization": f"Bearer {key}"}, timeout=timeout)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise ProviderUnavailable("El proveedor compatible no responde") from exc
    content = raw.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    data = validar_json(content, esquema)
    usage = raw.get("usage") or {}
    meta = _record("openai_compat", modelo, parametros, started,
                   {"prompt": usage.get("prompt_tokens"), "completion": usage.get("completion_tokens")},
                   raw.get("model", modelo))
    data["_meta_modelo"] = meta
    return data


def generar(prompt: str, esquema: dict | None, *, timeout: int = 120) -> dict:
    proveedor = proveedor_activo()
    if proveedor in {"openai_compat", "openai", "groq", "opencode"}:
        return generar_openai_compat(prompt, esquema, timeout=timeout)
    if proveedor == "ollama":
        return generar_ollama(prompt, esquema, timeout=timeout)
    raise ProviderUnavailable(f"Proveedor no soportado: {proveedor}")


def estado_proveedor(timeout: int = 2) -> dict:
    proveedor = proveedor_activo()
    modelo = modelo_activo()
    if proveedor != "ollama":
        return {"proveedor": proveedor, "modelo": modelo, "disponible": bool(os.environ.get("LUPA_API_KEY")),
                "motivo": "Proveedor compatible requiere clave por entorno."}
    host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except Exception:
        return {"proveedor": "ollama", "modelo": modelo, "disponible": False,
                "motivo": "Ollama no responde en " + host}
    models = [item.get("name", "") for item in raw.get("models", [])]
    return {"proveedor": "ollama", "modelo": modelo, "disponible": any(name.split(":")[0] == modelo.split(":")[0] for name in models),
            "motivo": "ok" if models else "Ollama responde, pero no listó modelos."}
