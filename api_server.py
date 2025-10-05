# API REST pentru gestionarea serviciilor educationale AI (Pro si Free tiers)
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api_server.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DEFAULT_LIMITS: Tuple[str, str] = ("50 per day", "10 per hour")
DATE_FORMAT = "%Y-%m-%d"


@dataclass
class DependencyContainer:
    """Abstrage dependintele externe folosite de API."""

    main_system_available: bool = False
    free_system_available: bool = False
    limiter_factory: Optional[Callable[..., Any]] = None
    get_remote_address: Optional[Callable[..., str]] = None
    default_limits: Tuple[str, str] = DEFAULT_LIMITS
    scoala_normala: Optional[Any] = None
    scoala_muzica: Optional[Any] = None
    sistem_gratuit: Optional[Any] = None
    token_monitor: Optional[Any] = None
    ai_client_manager: Optional[Any] = None
    Config: Optional[Any] = None
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def limiter_available(self) -> bool:
        return self.limiter_factory is not None and self.get_remote_address is not None


def load_dependencies() -> DependencyContainer:
    deps = DependencyContainer()

    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        deps.limiter_factory = Limiter
        deps.get_remote_address = get_remote_address
    except ImportError as exc:
        logger.warning("Flask-Limiter nu este disponibil: %s", exc)
        deps.errors["limiter"] = str(exc)

    try:
        from main import creeaza_structura_educationala

        scoala_normala_obj, scoala_muzica_obj = creeaza_structura_educationala()
        deps.scoala_normala = scoala_normala_obj
        deps.scoala_muzica = scoala_muzica_obj
        deps.main_system_available = True
    except ImportError as exc:
        logger.error("Modulele principale nu pot fi importate: %s", exc)
        deps.errors["main"] = str(exc)
    except Exception as exc:
        logger.critical("Initializarea sistemului principal a esuat: %s", exc, exc_info=True)
        deps.errors["main_init"] = str(exc)

    try:
        from main_free import SistemEducationalFree
        from config import Config, token_monitor
        from ai_clients import ai_client_manager

        deps.sistem_gratuit = SistemEducationalFree()
        deps.free_system_available = True
        deps.token_monitor = token_monitor
        deps.ai_client_manager = ai_client_manager
        deps.Config = Config
    except ImportError as exc:
        logger.warning("Modulele pentru varianta gratuita nu sunt disponibile: %s", exc)
        deps.errors["free"] = str(exc)
    except Exception as exc:
        logger.error("Initializarea sistemului gratuit a esuat: %s", exc, exc_info=True)
        deps.errors["free_init"] = str(exc)

    return deps


def verify_api_keys(env: Mapping[str, str] = os.environ) -> None:
    missing = [key for key in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "CLAUDE_API_KEY") if not env.get(key)]
    if missing:
        logger.warning("Chei API lipsa: %s", ", ".join(missing))
        logger.warning("Unele functionalitati pot fi indisponibile.")
    else:
        logger.info("Toate cheile API sunt configurate.")


def create_rate_limiter(app: Flask, deps: DependencyContainer) -> Optional[Any]:
    if not deps.limiter_available:
        class MockLimiter:
            def limit(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
                def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                    return func

                return decorator

        return MockLimiter()

    limiter = deps.limiter_factory(  # type: ignore[arg-type]
        app=app,
        key_func=deps.get_remote_address,
        default_limits=list(deps.default_limits),
    )
    return limiter


def create_pro_blueprint(deps: DependencyContainer, limiter: Any) -> Blueprint:
    bp = Blueprint("pro_api", __name__)
    limit = limiter.limit if hasattr(limiter, "limit") else (lambda *a, **k: (lambda f: f))

    @bp.route("/intreaba", methods=["POST"])
    @limit("50/day")
    def intreaba_profesor() -> Any:
        if not deps.main_system_available or not deps.scoala_normala:
            return jsonify({"success": False, "error": "Sistemul principal nu este disponibil"}), 503

        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"success": False, "error": "Nu s-a putut interpreta payload-ul JSON"}), 400

        intrebare = data.get("intrebare") if isinstance(data, dict) else None
        scoala_nume = data.get("scoala") if isinstance(data, dict) else None
        clasa = data.get("clasa") if isinstance(data, dict) else None

        if intrebare is None or scoala_nume is None or clasa is None:
            logger.warning("Date incomplete pentru /api/intreaba: intrebare=%s, scoala=%s, clasa=%s", intrebare, scoala_nume, clasa)
            return jsonify({"success": False, "error": "Intrebare, scoala si clasa sunt obligatorii."}), 400

        try:
            clasa_int = int(clasa)
        except ValueError:
            return jsonify({"success": False, "error": "Clasa trebuie sa fie un numar intreg."}), 400

        logger.info("[PRO] Question received: '%s' for school '%s', class '%s'", intrebare, scoala_nume, clasa_int)

        school_map = {
            "Scoala_Normala": deps.scoala_normala,
            "Scoala_de_Muzica_George_Enescu": deps.scoala_muzica,
        }
        scoala = school_map.get(scoala_nume)
        if scoala is None:
            logger.warning("Numele scolii este invalid: %s", scoala_nume)
            return jsonify({"success": False, "error": f"Scoala '{scoala_nume}' nu exista."}), 400

        try:
            director = scoala.directori[0]
            profesor_ales = director.alege_profesor_pentru_intrebare(intrebare, clasa_int)
        except Exception as exc:
            logger.error("Eroare la selectarea profesorului: %s", exc, exc_info=True)
            return jsonify({"success": False, "error": "Nu s-a putut selecta un profesor."}), 500

        if not profesor_ales:
            logger.warning("[PRO] Nu exista profesor potrivit pentru intrebarea: '%s'", intrebare)
            return jsonify({"success": False, "error": "Nu s-a gasit un profesor potrivit pentru clasa specificata."}), 404

        logger.info("[PRO] Intrebarea a fost asignata profesorului %s (%s)", profesor_ales.nume, profesor_ales.materie)

        try:
            raspuns = profesor_ales.raspunde_intrebare(intrebare, user_id="pro_user", is_free_tier=False)
        except Exception as exc:
            logger.error("Eroare la generarea raspunsului profesorului: %s", exc, exc_info=True)
            return jsonify({"success": False, "error": "Nu s-a putut genera raspunsul."}), 500

        return jsonify(
            {
                "success": True,
                "raspuns": raspuns,
                "profesor_nume": profesor_ales.nume,
                "profesor_materie": profesor_ales.materie,
                "profesor_personalitate": getattr(profesor_ales.configurari, "personalitate", "necunoscut"),
                "profesor_model_ai": getattr(profesor_ales.configurari, "model", "necunoscut"),
                "tier": "pro",
            }
        )

    return bp


def create_free_blueprint(deps: DependencyContainer, limiter: Any) -> Blueprint:
    bp = Blueprint("free_api", __name__)

    @bp.route("/ask", methods=["POST"])
    def ask_free() -> Any:
        if not deps.sistem_gratuit:
            return jsonify({"error": "Sistemul gratuit nu este disponibil"}), 503

        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "Nu s-a putut interpreta payload-ul JSON"}), 400

        required = ["user_id", "intrebare", "scoala", "clasa"]
        missing = [field for field in required if field not in data]
        if missing:
            return jsonify({"error": f"Campurile {missing} sunt obligatorii"}), 400

        logger.info("[FREE] Question from user %s: '%s'", data["user_id"], data["intrebare"])

        try:
            rezultat = deps.sistem_gratuit.pune_intrebare(
                user_id=data["user_id"],
                intrebare=data["intrebare"],
                scoala_nume=data["scoala"],
                clasa=int(data["clasa"]),
            )
        except Exception as exc:
            logger.error("[FREE] Eroare la procesarea intrebarii: %s", exc, exc_info=True)
            return jsonify({"error": "Nu s-a putut procesa intrebarea in varianta gratuita"}), 500

        return jsonify({"success": True, "rezultat": rezultat})

    @bp.route("/stats", methods=["GET"])
    def get_free_stats() -> Any:
        if not deps.free_system_available or not deps.token_monitor:
            return jsonify({"error": "Monitorizarea pentru varianta gratuita nu este disponibila"}), 503

        try:
            stats = deps.token_monitor.get_stats()
        except Exception as exc:
            logger.error("Nu s-au putut obtine statisticile free tier: %s", exc, exc_info=True)
            return jsonify({"error": "Nu s-au putut obtine statisticile"}), 500

        return jsonify({"success": True, "stats": stats})

    @bp.route("/health", methods=["GET"])
    def free_health() -> Any:
        status = {
            "available": bool(deps.sistem_gratuit),
            "initialized": deps.free_system_available,
        }
        return jsonify({"success": True, "status": status})

    @bp.route("/user/<user_id>/stats", methods=["GET"])
    def free_user_stats(user_id: str) -> Any:
        if not deps.sistem_gratuit:
            return jsonify({"error": "Sistemul gratuit nu este disponibil"}), 503

        utilizatori = getattr(deps.sistem_gratuit, "utilizatori_activi", {})
        info = utilizatori.get(user_id, {})
        return jsonify({"success": True, "user_id": user_id, "info": info})

    return bp


def register_common_routes(app: Flask, deps: DependencyContainer, limiter: Any) -> None:
    limit = limiter.limit if hasattr(limiter, "limit") else (lambda *a, **k: (lambda f: f))

    @app.route("/api/scoli", methods=["GET"])
    def get_scoli() -> Any:
        scoli = []
        if deps.scoala_normala:
            scoli.append({"nume": deps.scoala_normala.nume, "tip": "pro"})
        if deps.scoala_muzica:
            scoli.append({"nume": deps.scoala_muzica.nume, "tip": "pro"})
        if deps.sistem_gratuit:
            scoli.append({"nume": "Free Tier", "tip": "free"})
        logger.info("Returned list of schools (%s entries).", len(scoli))
        return jsonify({"success": True, "scoli": scoli})

    @app.route("/api/clase", methods=["GET"])
    def get_clase() -> Any:
        clase = list(range(5))
        logger.info("Returned list of classes.")
        return jsonify({"success": True, "clase": clase})

    @app.route("/api/status", methods=["GET"])
    def get_system_status() -> Any:
        free_stats: Dict[str, Any] = {}
        if deps.token_monitor:
            try:
                free_stats = deps.token_monitor.get_stats()
            except Exception as exc:
                logger.error("Nu s-au putut obtine statisticile de tokeni: %s", exc, exc_info=True)

        status = {
            "system": "AI Educational System",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "pro_tier": {
                    "available": deps.main_system_available and bool(os.getenv("OPENAI_API_KEY")),
                    "status": "active" if deps.main_system_available else "unavailable",
                },
                "free_tier": {
                    "available": deps.free_system_available and deps.sistem_gratuit is not None,
                    "status": "active" if deps.free_system_available and deps.sistem_gratuit else "unavailable",
                    "users": len(getattr(deps.sistem_gratuit, "utilizatori_activi", {})) if deps.sistem_gratuit else 0,
                    "max_users": getattr(deps.Config, "MAX_FREE_USERS", 10) if deps.Config else 10,
                    "token_usage": free_stats.get("usage_percentage", 0),
                },
            },
            "api_keys": {
                "openai": "configured" if os.getenv("OPENAI_API_KEY") else "missing",
                "deepseek": "configured" if os.getenv("DEEPSEEK_API_KEY") else "missing",
                "claude": "configured" if os.getenv("CLAUDE_API_KEY") else "missing",
            },
            "errors": deps.errors,
        }
        return jsonify(status)

    @app.route("/api/test", methods=["GET"])
    @limit("100/hour")
    def test_endpoint() -> Any:
        endpoints = [
            "/api/intreaba" if deps.main_system_available else "/api/intreaba (unavailable)",
            "/api/free/ask" if deps.free_system_available else "/api/free/ask (unavailable)",
            "/api/scoli",
            "/api/clase",
            "/api/status",
            "/api/test",
            "/health",
        ]
        return jsonify(
            {
                "message": "API functioneaza corect",
                "timestamp": datetime.now().isoformat(),
                "system_status": {
                    "main_system": deps.main_system_available,
                    "free_system": deps.free_system_available,
                    "limiter": deps.limiter_available,
                },
                "endpoints_available": endpoints,
            }
        )

    @app.route("/health", methods=["GET"])
    def health_check() -> Any:
        return {"status": "healthy", "service": "AI Educational API"}, 200

    @app.route("/", methods=["GET"])
    def home() -> Any:
        return jsonify(
            {
                "message": "AI Educational System API",
                "version": "1.0",
                "documentation": "/api/test",
                "status": "running",
            }
        )


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error: Exception) -> Any:
        return (
            jsonify(
                {
                    "error": "Endpoint inexistent",
                    "message": "Verifica documentatia API pentru rutele disponibile",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error: Exception) -> Any:
        logger.error("Eroare interna a serverului: %s", error)
        return (
            jsonify(
                {
                    "error": "Eroare interna",
                    "message": "Incearca din nou mai tarziu",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


def create_app(dependencies: Optional[DependencyContainer] = None) -> Flask:
    deps = dependencies or load_dependencies()
    app = Flask(__name__)
    CORS(app)

    limiter = create_rate_limiter(app, deps)
    pro_bp = create_pro_blueprint(deps, limiter)
    free_bp = create_free_blueprint(deps, limiter)

    app.register_blueprint(pro_bp, url_prefix="/api")
    app.register_blueprint(free_bp, url_prefix="/api/free")

    register_common_routes(app, deps, limiter)
    register_error_handlers(app)
    verify_api_keys()

    # Stocam containerul pe app pentru acces in teste/diagnostic
    app.dependency_container = deps  # type: ignore[attr-defined]
    return app


def perform_daily_cleanup(app: Flask) -> None:
    deps: DependencyContainer = getattr(app, "dependency_container", None)
    if not deps or not deps.sistem_gratuit:
        return
    try:
        history = getattr(deps.sistem_gratuit, "istoric_utilizare", {})
        threshold = datetime.now().date() - timedelta(days=30)
        for key in list(history.keys()):
            try:
                day = datetime.strptime(key, DATE_FORMAT).date()
            except ValueError:
                continue
            if day < threshold:
                history.pop(key, None)
    except Exception as exc:
        logger.error("Curatarea zilnica a istoricului gratuit a esuat: %s", exc, exc_info=True)


def _bootstrap_app() -> Flask:
    deps = load_dependencies()
    return create_app(deps)


app = _bootstrap_app()


if __name__ == "__main__":
    logger.info("Pornire server Flask API...")
    logger.info("Rute disponibile: /api/intreaba, /api/free/ask, /api/status, /api/test, /health")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
    logger.info("Server Flask API oprit.")
