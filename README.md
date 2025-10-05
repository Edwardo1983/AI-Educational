# AI Educational Assistant

## Overview
AI Educational Assistant is a hybrid platform that simulates a personalised teaching staff for elementary students. It combines deterministic lesson planning (folders, materials, structured teaching roles) with dynamic AI generated answers, allowing both a Pro tier and a Free tier experience.

## Key Capabilities
- Multi school orchestration (regular school and George Enescu music school) with tailored subjects per class.
- AI powered staff: directors select the most suitable AI teacher, and each teacher uses a fine tuned prompt with subject specific models (GPT-5 and Claude Sonnet 4.5).
- Material manager that builds and reads a full folder hierarchy for every class, subject, and teacher and caches parsed PDF content.
- AI client manager with response caching, provider selection (OpenAI, Claude, DeepSeek), token monitoring, and configurable tiers.
- Cost monitor using Decimal based accounting, retention policies, and daily clean up hooks.
- REST API built with Flask, blueprints, rate limiting, free tier endpoints, and status reports.
- CLI workflows for demos, interactive sessions, statistics, and advanced configuration tests.

## Architecture at a Glance
- `education/gestor_materiale.py`: builds and maintains the teaching material tree, caches PDF excerpts, generates inventory reports.
- `education/profesor.py`: defines teacher configuration profiles and the AI response flow that talks to `ai_client_manager`.
- `education/director.py`: encapsulates director level decision logic and uses OpenAI to assign the best teacher.
- `main.py`: constructs the full school ecosystem, provides CLI menus, demos, and stats.
- `main_free.py`: lightweight free tier implementation with per user limits and simplified prompts.
- `ai_clients.py`: provider management (OpenAI GPT-5, Claude Sonnet 4.5, DeepSeek), caching, token estimates, monitoring hooks.
- `config.py`: environment configuration, free tier pricing maps, token monitor implementation.
- `cost_monitor.py`: Decimal-safe tracking of daily AI spend, retention clean-up, pricing injection from `ConfigFree`.
- `api_server.py`: Flask application factory, Pro/Free blueprints, common routes, health/status endpoints, dependency container.

## Requirements
- Python 3.9+
- Dependencies listed in `requirements.txt`
- Valid API keys for OpenAI, Anthropic (Claude), and DeepSeek as needed

## Installation
```bash
# Clone the repository
git clone https://github.com/Edwardo1983/AI-Educational.git
cd AI-Educational

# (Optional) create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration
1. Copy `.env` (see `.env.example` if provided) and add the keys:
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `CLAUDE_API_KEY`
2. Adjust `config.py` for cache paths, free tier limits, and token thresholds if required.
3. Review `ai_clients.py` for provider defaults and `ConfigFree.MODELS` for pricing updates.

## Running the Platform
### CLI Demo / Interactive Mode (Pro tier)
```
python main.py
```
Choose between the automated demo, interactive Q&A, or exit from the menu. Stop with `Ctrl+C`.

### Free Tier CLI
```
python main_free.py
```
Designed for constrained usage: limited questions per user, slim prompts, and budget friendly models.

### REST API Server
```
python api_server.py
```
The server exposes:
- `/api/intreaba` – Pro tier question endpoint.
- `/api/free/ask`, `/api/free/stats`, `/api/free/health`, `/api/free/user/<id>/stats` – Free tier utilities.
- `/api/scoli`, `/api/clase`, `/api/status`, `/api/test`, `/health`, `/` – Common metadata endpoints.
Stop the API with `Ctrl+C`.

## Logs and Monitoring
- Pro system logs: `sistem_educational.log`
- Free system logs: `sistem_educational_free.log`
- API logs: `api_server.log`
- Material manager reports saved under `materiale_didactice/`
- `cost_monitor.py` persists usage in `daily_costs.json` and can be triggered via `perform_daily_maintenance` or the API cleanup hooks.

## Testing
Unit tests live in the `tests/` directory.
```
python -m unittest discover
```
You can also run individual suites, e.g. `python -m unittest tests.test_cost_monitor`.

## Project Structure (excerpt)
```
AI-Educational/
├─ education/
│  ├─ gestor_materiale.py
│  ├─ profesor.py
│  └─ director.py
├─ main.py
├─ main_free.py
├─ ai_clients.py
├─ api_server.py
├─ config.py
├─ cost_monitor.py
├─ tests/
│  ├─ test_ai_clients.py
│  └─ test_cost_monitor.py
└─ README.md
```

## Deployment
The repository ships with `Procfile` and `railway.json` for Railway deployment. Configure environment variables on the platform; each push triggers deployment when linked to Railway.

## License & Contact
- License: specify the correct license text in this section if available.
- Contact: extasssy@gmail.com (Ordean Eduard Gabi)

## Project Status
Active development. Contributions welcome via pull requests.

---

# Asistent Educational AI (RO)

## Prezentare Generala
Asistentul Educational AI este o platforma hibrida care simuleaza un corp profesoral personalizat pentru elevii din ciclul primar. Combinam planificarea determinista (materiale pe foldere, roluri clare) cu raspunsuri dinamice generate de AI, atat pentru abonamentul Pro, cat si pentru versiunea Free.

## Functionalitati Cheie
- Orchestrare multi-scoala (scoala normala si scoala de muzica George Enescu) cu materii adaptate pe clase.
- Personal AI: directorii aleg profesorul optim, iar profesorii folosesc prompturi dedicate cu modele GPT-5 si Claude Sonnet 4.5.
- Gestor de materiale care construieste arborele de foldere, incarca PDF-uri si pastreaza cache cu fragmente relevante.
- Manager AI cu cache de raspunsuri, selectie intre OpenAI, Claude, DeepSeek, monitorizare tokeni si configuratii pe tier.
- Monitor de costuri bazat pe Decimal, politici de retentie si rutina zilnica de curatare.
- API REST in Flask cu blueprints, rate limiting, endpoints pentru free tier si rapoarte de stare.
- Fluxuri CLI pentru demo, meniu interactiv, statistici si teste avansate de configurare.

## Cerinte
- Python 3.9+
- Dependente: `requirements.txt`
- Chei API valide: OpenAI, Anthropic (Claude), DeepSeek

## Instalare
```bash
# Cloneaza repository-ul
git clone https://github.com/Edwardo1983/AI-Educational.git
cd AI-Educational

# (Optional) activeaza un mediu virtual
python -m venv .venv
.\.venv\Scripts\activate   # Windows

# Instaleaza dependentele
pip install -r requirements.txt
```

## Configurare
1. Completeaza `.env` cu `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `CLAUDE_API_KEY`.
2. Ajusteaza `config.py` pentru limite, cache si tokeni.
3. Revizuieste `ai_clients.py` si `ConfigFree.MODELS` pentru modele si costuri.

## Rulare
### CLI Pro
```
python main.py
```
Alege demo-ul automat sau meniul interactiv. Se opreste cu `Ctrl+C`.

### CLI Free
```
python main_free.py
```
Versiune limitata pentru 10 utilizatori, intrebari reduse si cost minim.

### Server REST
```
python api_server.py
```
Expune rutele `/api/intreaba`, `/api/free/*`, `/api/scoli`, `/api/status`, `/health`. Oprire cu `Ctrl+C`.

## Monitorizare si Loguri
- `sistem_educational.log`, `sistem_educational_free.log`, `api_server.log`
- Rapoarte materiale: `materiale_didactice/`
- `cost_monitor.py` salveaza `daily_costs.json` si curata automat istoricul vechi.

## Teste
```
python -m unittest discover
```
Sau ruleaza teste punctuale din `tests/`.

## Structura
Vezi diagrama de mai sus pentru directoare principale (`education/`, `main.py`, `api_server.py`, etc.).

## Deployment
Configurarea Railway este pregatita (`Procfile`, `railway.json`). Conecteaza repository-ul, seteaza variabilele de mediu si fiecare push declanseaza deploy-ul.

## Licenta si Contact
- Licenta: adauga tipul corect daca este disponibil.
- Contact: extasssy@gmail.com (Ordean Eduard Gabi)

## Status Proiect
Proiect in dezvoltare activa. Contributiile sunt binevenite prin pull request-uri.
