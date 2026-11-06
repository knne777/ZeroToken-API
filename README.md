# ZeroToken API 🚀

**Universal AI Chat Gateway powered by your local subscriptions (Antigravity, Claude Code, Codex).**  
Zero API keys needed — zero per-token billing.

---

## Características Principales

* **Cero Factura de API:** Utiliza tus suscripciones activas existentes de Google Antigravity (`agy`), Claude Code (`claude`) o ChatGPT (`codex`).
* **Multi-Proveedor Unificado:** Un solo endpoint `POST /api/v1/chat` capaz de interactuar con cualquiera de los 3 motores mediante una respuesta JSON estandarizada.
* **Memoria Conversacional Nativa:** Pasa el `conversation_id` para continuar hilos multi-turno sin necesidad de gestionar bases de datos ni historiales manuales.
* **Aislamiento Seguro (*Sandbox*):** Cada llamada corre en un entorno temporal aislado, sin acceso a herramientas del sistema ni ejecución de scripts arbitrarios.
* **Documentación Interactiva:** Swagger UI en `http://localhost:8000/docs` y ReDoc en `http://localhost:8000/redoc`.

---

## Inicio Rápido

### 1. Iniciar el Servidor API

```bash
cd /home/knne/zerotoken-api
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Accede a la documentación interactiva en:  
**http://localhost:8000/docs**

---

## Ejemplos de Uso con `curl`

### 1. Iniciar una Conversación Nueva

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, mi nombre es Roberto",
    "provider": "agy",
    "model": "gemini-3.8-flash-high"
  }'
```

**Respuesta JSON:**
```json
{
  "provider": "agy",
  "model": "gemini-3.8-flash-high",
  "conversation_id": "2b744e4d-07a9-44ba-baad-a7d1dfca7685",
  "response": "¡Hola Roberto! Mucho gusto. ¿En qué te puedo ayudar hoy?",
  "status": "SUCCESS",
  "num_turns": 1,
  "duration_seconds": 2.1,
  "usage": {
    "input_tokens": 7425,
    "output_tokens": 164,
    "thinking_tokens": 138,
    "cache_read_tokens": 0,
    "total_tokens": 7589
  }
}
```

### 2. Continuar la Conversación (Multi-Turno con Memoria)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "2b744e4d-07a9-44ba-baad-a7d1dfca7685",
    "message": "¿Recuerdas cuál es mi nombre?",
    "provider": "agy"
  }'
```

**Respuesta:**
```json
{
  "provider": "agy",
  "model": "default",
  "conversation_id": "2b744e4d-07a9-44ba-baad-a7d1dfca7685",
  "response": "Sí, tu nombre es Roberto.",
  "status": "SUCCESS",
  "num_turns": 2,
  "duration_seconds": 1.8,
  "usage": {
    "input_tokens": 15222,
    "output_tokens": 25,
    "total_tokens": 15247
  }
}
```

### 3. Consultar Motores Instalados

```bash
curl -s http://localhost:8000/api/v1/providers
```

### 4. Consultar Modelos Disponibles

```bash
curl -s http://localhost:8000/api/v1/models
```

---

## Variables de Entorno Opcionales

* `ZEROTOKEN_PORT`: Puerto de escucha (por defecto `8000`).
* `ZEROTOKEN_HOST`: Host de enlace (por defecto `0.0.0.0`).
* `ZEROTOKEN_DEFAULT_PROVIDER`: Proveedor por defecto si no se especifica en el payload (por defecto `agy`).
* `ZEROTOKEN_TIMEOUT`: Timeout en segundos por llamada (por defecto `300.0`).
