# Configuratii pentru sistem si monitorizarea consumului AI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from pathlib import Path

load_dotenv()


class Config:
    """Configuratii pentru sistemul educational"""

    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

    # Limitari pentru varianta gratuita
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
    CACHE_DURATION = 3600  # 1 ora in secunde
    CACHE_FILE = "cache_responses.json"


class ConfigFree:
    """Configuratii pentru versiunea gratuita"""

    FREE_TIER_ENABLED = True
    MAX_FREE_USERS = 10
    MAX_QUESTIONS_PER_DAY_FREE = 5
    MAX_TOKENS_FREE = 400

    DEFAULT_MODEL = "gpt-5-nano"
    MODEL_WEIGHTS = {
        "gpt-5-nano": 0.50,
        "gpt-4.1-nano": 0.25,
        "deepseek-chat": 0.25,
    }

    MODELS = {
        "gpt-5-nano": {
            "input_per_1k": 0.05,
            "cached_input_per_1k": 0.005,
            "output_per_1k": 0.40,
        },
        "gpt-4.1-nano": {
            "input_per_1k": 0.10,
            "cached_input_per_1k": 0.025,
            "output_per_1k": 0.40,
        },
        "deepseek-chat": {
            "input_per_1k": 0.28,
            "cached_input_per_1k": 0.028,
            "output_per_1k": 0.42,
        },
    }

    FREE_MODEL = DEFAULT_MODEL
    COST_PER_1K_TOKENS_INPUT = MODELS[DEFAULT_MODEL]["input_per_1k"]
    COST_PER_1K_TOKENS_OUTPUT = MODELS[DEFAULT_MODEL]["output_per_1k"]

    @classmethod
    def get_daily_cost_estimate(cls, cache_hit_rate=0.0):
        """Calculeaza costul zilnic estimat pentru free tier"""
        avg_tokens_per_question = 600
        input_tokens = avg_tokens_per_question / 2
        output_tokens = avg_tokens_per_question - input_tokens
        cached_tokens = input_tokens * cache_hit_rate
        uncached_tokens = input_tokens - cached_tokens
        questions_per_day = cls.MAX_FREE_USERS * cls.MAX_QUESTIONS_PER_DAY_FREE

        def cost_for_model(model_name):
            pricing = cls.MODELS[model_name]
            input_cost = (uncached_tokens / 1000) * pricing["input_per_1k"]
            cached_input_cost = (cached_tokens / 1000) * pricing["cached_input_per_1k"]
            output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
            return input_cost + cached_input_cost + output_cost

        expected_cost_per_question = sum(
            cls.MODEL_WEIGHTS.get(model, 0) * cost_for_model(model)
            for model in cls.MODELS
        )

        return expected_cost_per_question * questions_per_day


class TokenMonitor:
    """Monitorizare tokeni in timp real"""

    def __init__(self):
        self.usage_file = "token_usage.json"
        self.load_usage()

    def load_usage(self):
        """Incarca utilizarea tokenilor din fisier"""
        try:
            if Path(self.usage_file).exists():
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    self.usage_data = json.load(f)
            else:
                self.usage_data = {
                    "daily_tokens": 0,
                    "last_reset": datetime.now().isoformat(),
                    "users": {},
                    "total_requests": 0
                }
        except Exception as exc:
            print(f"Eroare la incarcarea datelor de utilizare: {exc}")
            self.usage_data = {
                "daily_tokens": 0,
                "last_reset": datetime.now().isoformat(),
                "users": {},
                "total_requests": 0
            }

    def save_usage(self):
        """Salveaza utilizarea tokenilor in fisier"""
        try:
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(self.usage_data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"Eroare la salvarea datelor de utilizare: {exc}")

    def reset_daily_if_needed(self):
        """Reseteaza contorul zilnic daca este nevoie"""
        last_reset = datetime.fromisoformat(self.usage_data["last_reset"])
        if datetime.now().date() > last_reset.date():
            self.usage_data["daily_tokens"] = 0
            self.usage_data["last_reset"] = datetime.now().isoformat()
            self.save_usage()

    def can_use_tokens(self, user_id, tokens_needed):
        """Verifica daca utilizatorul poate folosi tokenii ceruti"""
        self.reset_daily_if_needed()

        if self.usage_data["daily_tokens"] + tokens_needed > Config.MAX_DAILY_TOKENS:
            return False, "Limita zilnica de tokeni a fost depasita"

        user_tokens = self.usage_data["users"].get(user_id, 0)
        if user_tokens + tokens_needed > Config.MAX_TOKENS_PER_USER:
            return False, f"Limita personala de tokeni depasita ({user_tokens}/{Config.MAX_TOKENS_PER_USER})"

        return True, "OK"

    def add_tokens(self, user_id, tokens_used):
        """Adauga tokenii folositi in contor"""
        self.reset_daily_if_needed()

        self.usage_data["daily_tokens"] += tokens_used
        self.usage_data["total_requests"] += 1

        if user_id not in self.usage_data["users"]:
            self.usage_data["users"][user_id] = 0

        self.usage_data["users"][user_id] += tokens_used

        usage_percentage = self.usage_data["daily_tokens"] / Config.MAX_DAILY_TOKENS
        if usage_percentage >= Config.ALERT_THRESHOLD:
            print(f"ALERTA! Utilizare tokeni: {usage_percentage:.1%} din limita zilnica!")

        self.save_usage()

    def get_stats(self):
        """Returneaza statistici de utilizare"""
        self.reset_daily_if_needed()
        return {
            "daily_tokens": self.usage_data["daily_tokens"],
            "max_daily": Config.MAX_DAILY_TOKENS,
            "usage_percentage": (self.usage_data["daily_tokens"] / Config.MAX_DAILY_TOKENS) * 100,
            "active_users": len(self.usage_data["users"]),
            "total_requests": self.usage_data["total_requests"]
        }


# Instanta globala pentru monitorizare
token_monitor = TokenMonitor()
