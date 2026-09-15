# Gestión de Servicios (portfolio)

Sistema de gestión de clientes + servicios programados + personal +
facturación. Arquitectura extraída y generalizada a partir de un proyecto real
en producción (ver `PLAN_GENERALIZACION_PORTFOLIO.md` para el detalle de qué
se generalizó y por qué).

**Estado actual: en construcción, Fase 0 completa.** Todavía no hay modelos de
negocio ni pantallas reales — ver el plan para las fases siguientes. Este
README se reescribe por completo en la fase final (documentación tipo
case-study).

**Alcance: solo local.** No hay despliegue (sin Railway/Vercel/S3): el
proyecto corre en tu máquina con Postgres local.

## Requisitos

- Python 3.11+
- Node 20+
- PostgreSQL corriendo en local

## Backend

```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows (PowerShell: venv\Scripts\Activate.ps1)
pip install -r requirements.txt

cp .env.example .env
# completar SECRET_KEY, FIELD_ENCRYPTION_KEY y credenciales de Postgres en .env
# (instrucciones para generar cada valor dentro del propio .env.example)

# crear la base de datos vacía en Postgres (nombre según DB_NAME en .env), luego:
python manage.py migrate
python manage.py runserver
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Por defecto el frontend corre en `http://localhost:5173` y espera el backend
en `http://localhost:8000` (se configura la URL base en una fase posterior,
cuando exista llamada real a la API).

## Estructura

```
backend/    Django + DRF (API)
frontend/   React + Vite + Tailwind (SPA)
docs/       Documentación de diseño (dataset ficticio, decisiones, etc.)
```

Ver `PLAN_GENERALIZACION_PORTFOLIO.md` para el glosario de nombres y el
detalle de cada fase.
