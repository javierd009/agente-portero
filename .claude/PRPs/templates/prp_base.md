name: "Template Base PRP v2 - Rico en Contexto con Bucles de Validación"
description: |

## Propósito
Template optimizado para agentes de IA para implementar features con suficiente contexto y capacidades de auto-validación para lograr código funcional a través de refinamiento iterativo.

## Principios Fundamentales
1. **El Contexto es Rey**: Incluye TODA la documentación necesaria, ejemplos y advertencias
2. **Bucles de Validación**: Proporciona tests/lints ejecutables que la IA pueda ejecutar y corregir
3. **Información Densa**: Usa keywords y patrones del codebase
4. **Éxito Progresivo**: Comienza simple, valida, luego mejora
5. **Reglas Globales**: Asegúrate de seguir todas las reglas en CLAUDE.md

---

## Objetivo
[Qué necesita construirse - sé específico sobre el estado final y deseos]

## Por Qué
- [Valor de negocio e impacto en usuarios]
- [Integración con features existentes]
- [Problemas que esto resuelve y para quién]

## Qué
[Comportamiento visible para el usuario y requerimientos técnicos]

### Criterios de Éxito
- [ ] [Resultados medibles específicos]

## Todo el Contexto Necesario

### Documentación & Referencias (lista todo el contexto necesario para implementar la feature)
```yaml
# LECTURA OBLIGATORIA - Incluye estos en tu ventana de contexto
- url: [URL de documentación oficial de la API]
  why: [Secciones/métodos específicos que necesitarás]

- file: [ruta/al/ejemplo.py]
  why: [Patrón a seguir, gotchas a evitar]

- doc: [URL de documentación de la librería]
  section: [Sección específica sobre errores comunes]
  critical: [Insight clave que previene errores comunes]

- docfile: [PRPs/ai_docs/archivo.md]
  why: [docs que el usuario ha pegado en el proyecto]

```

### Árbol del Codebase Actual (ejecuta `tree` en la raíz del proyecto) para obtener una visión general del codebase
```bash

```

### Árbol del Codebase Deseado con archivos a agregar y responsabilidad de cada archivo
```bash

```

### Gotchas Conocidos de nuestro codebase & Peculiaridades de Librerías
```python
# CRÍTICO: [Nombre de librería] requiere [configuración específica]
# Ejemplo: FastAPI requiere funciones async para endpoints
# Ejemplo: Este ORM no soporta inserts por lote de más de 1000 registros
# Ejemplo: Usamos pydantic v2 y
```

## Blueprint de Implementación

### Modelos de datos y estructura

Crea los modelos de datos principales, aseguramos seguridad de tipos y consistencia.
```python
Ejemplos:
 - modelos orm
 - modelos pydantic
 - schemas pydantic
 - validadores pydantic

```

### Lista de tareas a completar para cumplir el PRP en el orden en que deben completarse

```yaml
Tarea 1:
MODIFICAR src/existing_module.py:
  - ENCONTRAR patrón: "class OldImplementation"
  - INYECTAR después de la línea que contiene "def __init__"
  - PRESERVAR las firmas de métodos existentes

CREAR src/new_feature.py:
  - REFLEJAR patrón de: src/similar_feature.py
  - MODIFICAR nombre de clase y lógica principal
  - MANTENER patrón de manejo de errores idéntico

...(...)

Tarea N:
...

```


### Pseudocódigo por tarea según sea necesario agregado a cada tarea
```python

# Tarea 1
# Pseudocódigo con detalles CRÍTICOS no escribas todo el código
async def new_feature(param: str) -> Result:
    # PATRÓN: Siempre valida input primero (ver src/validators.py)
    validated = validate_input(param)  # lanza ValidationError

    # GOTCHA: Esta librería requiere connection pooling
    async with get_connection() as conn:  # ver src/db/pool.py
        # PATRÓN: Usa decorador retry existente
        @retry(attempts=3, backoff=exponential)
        async def _inner():
            # CRÍTICO: API retorna 429 si >10 req/sec
            await rate_limiter.acquire()
            return await external_api.call(validated)

        result = await _inner()

    # PATRÓN: Formato de respuesta estandarizado
    return format_response(result)  # ver src/utils/responses.py
```

### Puntos de Integración
```yaml
BASE DE DATOS:
  - migration: "Agregar columna 'feature_enabled' a tabla users"
  - index: "CREATE INDEX idx_feature_lookup ON users(feature_id)"

CONFIG:
  - agregar a: config/settings.py
  - patrón: "FEATURE_TIMEOUT = int(os.getenv('FEATURE_TIMEOUT', '30'))"

RUTAS:
  - agregar a: src/api/routes.py
  - patrón: "router.include_router(feature_router, prefix='/feature')"
```

## Bucle de Validación

### Nivel 1: Sintaxis & Estilo
```bash
# Ejecuta estos PRIMERO - corrige cualquier error antes de proceder
ruff check src/new_feature.py --fix  # Auto-corrige lo que sea posible
mypy src/new_feature.py              # Verificación de tipos

# Esperado: Sin errores. Si hay errores, LEE el error y corrige.
```

### Nivel 2: Tests Unitarios cada nueva feature/archivo/función usa patrones de test existentes
```python
# CREAR test_new_feature.py con estos casos de test:
def test_happy_path():
    """Funcionalidad básica funciona"""
    result = new_feature("valid_input")
    assert result.status == "success"

def test_validation_error():
    """Input inválido lanza ValidationError"""
    with pytest.raises(ValidationError):
        new_feature("")

def test_external_api_timeout():
    """Maneja timeouts gracefully"""
    with mock.patch('external_api.call', side_effect=TimeoutError):
        result = new_feature("valid")
        assert result.status == "error"
        assert "timeout" in result.message
```

```bash
# Ejecuta e itera hasta que pasen:
uv run pytest test_new_feature.py -v
# Si falla: Lee el error, entiende la causa raíz, corrige código, re-ejecuta (nunca mockees para pasar)
```

### Nivel 3: Test de Integración
```bash
# Inicia el servicio
uv run python -m src.main --dev

# Prueba el endpoint
curl -X POST http://localhost:8000/feature \
  -H "Content-Type: application/json" \
  -d '{"param": "test_value"}'

# Esperado: {"status": "success", "data": {...}}
# Si hay error: Revisa logs en logs/app.log para stack trace
```

## Checklist de Validación Final
- [ ] Todos los tests pasan: `uv run pytest tests/ -v`
- [ ] Sin errores de linting: `uv run ruff check src/`
- [ ] Sin errores de tipos: `uv run mypy src/`
- [ ] Test manual exitoso: [comando curl/comando específico]
- [ ] Casos de error manejados gracefully
- [ ] Logs son informativos pero no verbosos
- [ ] Documentación actualizada si es necesario

---

## Anti-Patrones a Evitar
- ❌ No crees nuevos patrones cuando los existentes funcionan
- ❌ No omitas validación porque "debería funcionar"
- ❌ No ignores tests fallidos - corrígelos
- ❌ No uses funciones sync en contexto async
- ❌ No hardcodees valores que deberían ser config
- ❌ No captures todas las excepciones - sé específico
