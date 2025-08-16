# api_server.py - Versiunea actualizată cu suport pentru varianta gratuită

# Importăm librăriile necesare
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import time

# Importuri pentru sistemul gratuit
try:
    from main_free import SistemEducationalFree
    from config import Config, token_monitor
    from ai_clients import ai_client_manager
except ImportError as e:
    print(f"ATENȚIE: Nu s-au putut importa modulele pentru varianta gratuită: {e}")
    print("Sistemul va rula doar cu funcționalitățile Pro.")

# Importăm logica existentă din main.py
from main import (
    creeaza_structura_educationala,
    Director,
    Profesor
)

# Configurarea logging-ului pentru API
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Încarcă variabilele din fișierul .env
load_dotenv()

# Verificăm cheile API la pornire
def verify_api_keys():
    """Verifică configurarea API keys"""
    missing_keys = []
    
    if not os.getenv('OPENAI_API_KEY'):
        missing_keys.append('OPENAI_API_KEY')
    
    if not os.getenv('DEEPSEEK_API_KEY'):
        missing_keys.append('DEEPSEEK_API_KEY')
    
    if not os.getenv('CLAUDE_API_KEY'):
        missing_keys.append('CLAUDE_API_KEY')
    
    if missing_keys:
        logger.warning(f"Chei API lipsă: {', '.join(missing_keys)}")
        logger.warning("Unele funcționalități vor fi limitate.")
    else:
        logger.info("✅ Toate cheile API sunt configurate")

verify_api_keys()

# Inițializează aplicația Flask
app = Flask(__name__)
CORS(app)

# Inițializarea sistemului educațional la pornirea serverului
logger.info("Initializing educational system...")

try:
    # Sistemul Pro (existent)
    scoala_normala_obj, scoala_muzica_obj = creeaza_structura_educationala()
    SCOALA_NORMALA_GLOBAL = scoala_normala_obj
    SCOALA_MUZICA_GLOBAL = scoala_muzica_obj
    
    # Sistemul gratuit (nou)
    try:
        sistem_gratuit = SistemEducationalFree()
        logger.info("✅ Sistem gratuit inițializat cu succes")
    except Exception as e:
        logger.error(f"❌ Eroare la inițializarea sistemului gratuit: {e}")
        sistem_gratuit = None
    
    logger.info("✅ Educational system initialized successfully.")
    
except Exception as e:
    logger.critical(f"❌ Failed to initialize educational system: {e}")
    exit(1)

# ==================== ENDPOINT-URI EXISTENTE (PRO) ====================

limiter = Limiter(app)

@app.route('/api/intreaba', methods=['POST'])
@limiter.limit("50/day")
def intreaba_profesor():
    """
    Endpoint pentru varianta Pro - folosește OpenAI
    """
    try:
        data = request.json
        intrebare = data.get('intrebare')
        scoala_nume = data.get('scoala')
        clasa = int(data.get('clasa'))
        
        if not all([intrebare, scoala_nume is not None, clasa is not None]):
            logger.warning(f"Missing data for /api/intreaba: intrebare={intrebare}, scoala={scoala_nume}, clasa={clasa}")
            return jsonify({'success': False, 'error': 'Date incomplete: intrebare, scoala și clasa sunt obligatorii.'}), 400
        
        logger.info(f"[PRO] Received question: '{intrebare}' for school '{scoala_nume}', class '{clasa}'")
        
        # Selectează școala corectă
        if scoala_nume == "Scoala_Normală":
            scoala = SCOALA_NORMALA_GLOBAL
        elif scoala_nume == "Scoala_de_Muzica_George_Enescu":
            scoala = SCOALA_MUZICA_GLOBAL
        else:
            logger.warning(f"Invalid school name: {scoala_nume}")
            return jsonify({'success': False, 'error': f'Școala "{scoala_nume}" nu există.'}), 400
        
        # Directorul alege profesorul
        director = scoala.directori[0]
        profesor_ales = director.alege_profesor_pentru_intrebare(intrebare, clasa)
        
        if profesor_ales:
            logger.info(f"[PRO] Question assigned to: {profesor_ales.nume} ({profesor_ales.materie})")
            
            # Folosește varianta Pro (is_free_tier=False)
            raspuns = profesor_ales.raspunde_intrebare(
                intrebare, 
                user_id="pro_user", 
                is_free_tier=False
            )
            
            logger.info(f"[PRO] Response generated for {profesor_ales.nume}.")
            
            return jsonify({
                'success': True,
                'raspuns': raspuns,
                'profesor_nume': profesor_ales.nume,
                'profesor_materie': profesor_ales.materie,
                'profesor_personalitate': profesor_ales.configurari.personalitate,
                'profesor_model_ai': profesor_ales.configurari.model,
                'tier': 'pro'
            })
        else:
            logger.warning(f"[PRO] No suitable teacher found for question: '{intrebare}'")
            return jsonify({'success': False, 'error': 'Nu s-a găsit un profesor potrivit pentru această întrebare în clasa specificată.'}), 404
    
    except Exception as e:
        logger.error(f"Error in /api/intreaba: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'A apărut o eroare internă: {str(e)}'}), 500

# Metrics pentru monitorizare
#def log_metrics(response_time, tokens_used, user_id):
#    metrics = {
#        'timestamp': time.time(),
#        'response_time': response_time,
#       'tokens': tokens_used,
#        'user_id': user_id
#    }
#    save_metrics(metrics)

# ==================== ENDPOINT-URI NOI (GRATUIT) ====================

@app.route('/api/free/ask', methods=['POST'])
def ask_free():
    """
    Endpoint pentru întrebări în varianta gratuită
    Folosește DeepSeek și Claude cu limitări
    """
    if not sistem_gratuit:
        return jsonify({"error": "Sistemul gratuit nu este disponibil"}), 503
    
    try:
        data = request.json
        
        # Validare câmpuri obligatorii
        required_fields = ['user_id', 'intrebare', 'scoala', 'clasa']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Câmpul '{field}' este obligatoriu"}), 400
        
        logger.info(f"[FREE] Received question from user {data['user_id']}: '{data['intrebare']}'")
        
        # Procesează întrebarea prin sistemul gratuit
        rezultat = sistem_gratuit.pune_intrebare(
            user_id=data['user_id'],
            intrebare=data['intrebare'],
            scoala_nume=data['scoala'],
            clasa=int(data['clasa'])
        )
        
        if "error" in rezultat:
            logger.warning(f"[FREE] Error for user {data['user_id']}: {rezultat['error']}")
            return jsonify(rezultat), 400
        
        logger.info(f"[FREE] Success for user {data['user_id']}, professor: {rezultat['profesor']['nume']}")
        
        # Adaugă informații despre tier
        rezultat['tier'] = 'free'
        rezultat['timestamp'] = datetime.now().isoformat()
        
        return jsonify(rezultat)
    
    except Exception as e:
        logger.error(f"Error in /api/free/ask: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/free/stats', methods=['GET'])
def get_free_stats():
    """
    Statistici pentru varianta gratuită
    """
    if not sistem_gratuit:
        return jsonify({"error": "Sistemul gratuit nu este disponibil"}), 503
    
    try:
        stats = token_monitor.get_stats()
        
        return jsonify({
            "success": True,
            "data": {
                "utilizatori_activi": len(sistem_gratuit.utilizatori_activi),
                "max_utilizatori": sistem_gratuit.max_utilizatori,
                "tokeni_zilnici": stats["daily_tokens"],
                "limita_zilnica": stats["max_daily"],
                "procent_utilizare": round(stats["usage_percentage"], 2),
                "total_cereri": stats["total_requests"],
                "alerta_activa": stats["usage_percentage"] > 80,
                "status": "healthy" if stats["usage_percentage"] < 90 else "warning"
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in /api/free/stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/free/health', methods=['GET'])
def health_check_free():
    """
    Verificare sănătate sistem gratuit
    """
    try:
        stats = token_monitor.get_stats() if sistem_gratuit else {}
        
        health_status = {
            "status": "healthy",
            "free_tier_enabled": Config.FREE_TIER_ENABLED if 'Config' in globals() else False,
            "deepseek_configured": bool(os.getenv('DEEPSEEK_API_KEY')),
            "claude_configured": bool(os.getenv('CLAUDE_API_KEY')),
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "sistem_gratuit_available": sistem_gratuit is not None,
            "usage_ok": stats.get("usage_percentage", 0) < 90,
            "timestamp": datetime.now().isoformat()
        }
        
        # Determină statusul general
        if not health_status["sistem_gratuit_available"]:
            health_status["status"] = "degraded"
        elif not health_status["usage_ok"]:
            health_status["status"] = "warning"
        
        return jsonify(health_status)
    
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/free/user/<user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    """
    Statistici pentru un utilizator specific
    """
    if not sistem_gratuit:
        return jsonify({"error": "Sistemul gratuit nu este disponibil"}), 503
    
    try:
        # Încarcă datele de utilizare
        token_monitor.load_usage()
        user_tokens = token_monitor.usage_data["users"].get(user_id, 0)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "data": {
                "tokeni_folositi": user_tokens,
                "limita_personala": Config.MAX_TOKENS_PER_USER,
                "procent_utilizare": round((user_tokens / Config.MAX_TOKENS_PER_USER) * 100, 2),
                "tokeni_ramasi": max(0, Config.MAX_TOKENS_PER_USER - user_tokens),
                "este_utilizator_activ": user_id in sistem_gratuit.utilizatori_activi,
                "poate_pune_intrebari": user_tokens < Config.MAX_TOKENS_PER_USER
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting user stats for {user_id}: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== ENDPOINT-URI COMUNE ====================

@app.route('/api/scoli', methods=['GET'])
def get_scoli():
    """
    Endpoint pentru a returna lista de școli disponibile
    """
    scoli_disponibile = [
        {'nume': SCOALA_NORMALA_GLOBAL.nume, 'tip': SCOALA_NORMALA_GLOBAL.tip},
        {'nume': SCOALA_MUZICA_GLOBAL.nume, 'tip': SCOALA_MUZICA_GLOBAL.tip}
    ]
    
    logger.info("Providing list of schools.")
    return jsonify({'success': True, 'scoli': scoli_disponibile})

@app.route('/api/clase', methods=['GET'])
def get_clase():
    """
    Endpoint pentru a returna lista de clase disponibile (0-4)
    """
    clase_disponibile = list(range(5))
    logger.info("Providing list of classes.")
    return jsonify({'success': True, 'clase': clase_disponibile})

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """
    Status general al sistemului
    """
    try:
        free_stats = token_monitor.get_stats() if sistem_gratuit else {}
        
        status = {
            "system": "AI Educational System",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "pro_tier": {
                    "available": bool(os.getenv('OPENAI_API_KEY')),
                    "status": "active"
                },
                "free_tier": {
                    "available": sistem_gratuit is not None,
                    "status": "active" if sistem_gratuit else "unavailable",
                    "users": len(sistem_gratuit.utilizatori_activi) if sistem_gratuit else 0,
                    "max_users": Config.MAX_FREE_USERS if 'Config' in globals() else 10,
                    "token_usage": free_stats.get("usage_percentage", 0)
                }
            },
            "api_keys": {
                "openai": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
                "deepseek": "configured" if os.getenv('DEEPSEEK_API_KEY') else "missing",
                "claude": "configured" if os.getenv('CLAUDE_API_KEY') else "missing"
            }
        }
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== ENDPOINT PENTRU TESTARE ====================

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """
    Endpoint simplu pentru testarea conectivității
    """
    return jsonify({
        "message": "API funcționează corect!",
        "timestamp": datetime.now().isoformat(),
        "endpoints_available": [
            "/api/intreaba (PRO)",
            "/api/free/ask (FREE)",
            "/api/free/stats (FREE)",
            "/api/free/health (FREE)",
            "/api/scoli",
            "/api/clase",
            "/api/status"
        ]
    })

# ==================== GESTIONAREA ERORILOR ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint nu a fost găsit",
        "message": "Verifică documentația API pentru endpoint-urile disponibile",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Eroare internă de server",
        "message": "Te rugăm să încerci din nou mai târziu",
        "timestamp": datetime.now().isoformat()
    }), 500

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "AI Educational API"}, 200

# ==================== PORNIREA SERVERULUI ====================

if __name__ == '__main__':
    logger.info("🚀 Starting Flask API server...")
    logger.info("📊 Available endpoints:")
    logger.info("   PRO: /api/intreaba")
    logger.info("   FREE: /api/free/ask")
    logger.info("   STATS: /api/free/stats")
    logger.info("   HEALTH: /api/free/health")
    logger.info("   COMMON: /api/scoli, /api/clase, /api/status")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
    
    logger.info("🛑 Flask API server stopped.")