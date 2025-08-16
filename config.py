import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from pathlib import Path

load_dotenv()

class Config:
    """Configurări pentru sistemul educational"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
    
    # Limitări pentru varianta gratuită
    MAX_DAILY_TOKENS = int(os.getenv('MAX_DAILY_TOKENS', 50000))
    MAX_TOKENS_PER_USER = int(os.getenv('MAX_TOKENS_PER_USER', 5000))
    ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', 0.8))
    FREE_TIER_ENABLED = os.getenv('FREE_TIER_ENABLED', 'true').lower() == 'true'
    MAX_FREE_USERS = int(os.getenv('MAX_FREE_USERS', 10))
    
    # Endpoint-uri API
    DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
    CLAUDE_ENDPOINT = "https://api.anthropic.com/v1/messages"
    
    # Materii STEM pentru Claude
    STEM_SUBJECTS = [
        "Matematica", "Matematica_si_Explorarea_mediului", 
        "Stiinte_ale_naturii", "Educatie_civica"
    ]
    
    # Cache settings
    CACHE_DURATION = 3600  # 1 oră în secunde
    CACHE_FILE = "cache_responses.json"

# Adaugă aceste configurări în config.py

class ConfigFree:
    """Configurări pentru versiunea gratuită"""
    FREE_TIER_ENABLED = True
    MAX_FREE_USERS = 10
    MAX_QUESTIONS_PER_DAY_FREE = 5
    MAX_TOKENS_FREE = 400
    FREE_MODEL = "gpt-3.5-turbo"
    
    # Costuri estimate
    COST_PER_1K_TOKENS_INPUT = 0.0015  # USD pentru GPT-3.5-turbo
    COST_PER_1K_TOKENS_OUTPUT = 0.002  # USD pentru GPT-3.5-turbo
    
    @classmethod
    def get_daily_cost_estimate(cls):
        """Calculează costul zilnic estimat pentru free tier"""
        avg_tokens_per_question = 600  # input + output
        questions_per_day = cls.MAX_FREE_USERS * cls.MAX_QUESTIONS_PER_DAY_FREE
        total_tokens = questions_per_day * avg_tokens_per_question
        cost_usd = (total_tokens / 1000) * cls.COST_PER_1K_TOKENS_OUTPUT
        return cost_usd

class TokenMonitor:
    """Monitorizare tokeni în timp real"""
    
    def __init__(self):
        self.usage_file = "token_usage.json"
        self.load_usage()
    
    def load_usage(self):
        """Încarcă utilizarea tokenilor din fișier"""
        try:
            if Path(self.usage_file).exists():
                with open(self.usage_file, 'r') as f:
                    self.usage_data = json.load(f)
            else:
                self.usage_data = {
                    "daily_tokens": 0,
                    "last_reset": datetime.now().isoformat(),
                    "users": {},
                    "total_requests": 0
                }
        except Exception as e:
            print(f"Eroare la încărcarea datelor de utilizare: {e}")
            self.usage_data = {
                "daily_tokens": 0,
                "last_reset": datetime.now().isoformat(),
                "users": {},
                "total_requests": 0
            }
    
    def save_usage(self):
        """Salvează utilizarea tokenilor în fișier"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            print(f"Eroare la salvarea datelor de utilizare: {e}")
    
    def reset_daily_if_needed(self):
        """Resetează contorul zilnic dacă e nevoie"""
        last_reset = datetime.fromisoformat(self.usage_data["last_reset"])
        if datetime.now().date() > last_reset.date():
            self.usage_data["daily_tokens"] = 0
            self.usage_data["last_reset"] = datetime.now().isoformat()
            self.save_usage()
    
    def can_use_tokens(self, user_id, tokens_needed):
        """Verifică dacă utilizatorul poate folosi tokenii"""
        self.reset_daily_if_needed()
        
        # Verifică limita zilnică globală
        if self.usage_data["daily_tokens"] + tokens_needed > Config.MAX_DAILY_TOKENS:
            return False, "Limita zilnică de tokeni a fost depășită"
        
        # Verifică limita per utilizator
        user_tokens = self.usage_data["users"].get(user_id, 0)
        if user_tokens + tokens_needed > Config.MAX_TOKENS_PER_USER:
            return False, f"Limita personală de tokeni depășită ({user_tokens}/{Config.MAX_TOKENS_PER_USER})"
        
        return True, "OK"
    
    def add_tokens(self, user_id, tokens_used):
        """Adaugă tokenii folosiți"""
        self.reset_daily_if_needed()
        
        self.usage_data["daily_tokens"] += tokens_used
        self.usage_data["total_requests"] += 1
        
        if user_id not in self.usage_data["users"]:
            self.usage_data["users"][user_id] = 0
        
        self.usage_data["users"][user_id] += tokens_used
        
        # Verifică alertele
        usage_percentage = self.usage_data["daily_tokens"] / Config.MAX_DAILY_TOKENS
        if usage_percentage >= Config.ALERT_THRESHOLD:
            print(f"🚨 ALERTĂ! Utilizare tokeni: {usage_percentage:.1%} din limita zilnică!")
        
        self.save_usage()
    
    def get_stats(self):
        """Returnează statistici de utilizare"""
        self.reset_daily_if_needed()
        return {
            "daily_tokens": self.usage_data["daily_tokens"],
            "max_daily": Config.MAX_DAILY_TOKENS,
            "usage_percentage": (self.usage_data["daily_tokens"] / Config.MAX_DAILY_TOKENS) * 100,
            "active_users": len(self.usage_data["users"]),
            "total_requests": self.usage_data["total_requests"]
        }

# Instanță globală pentru monitorizare
token_monitor = TokenMonitor()