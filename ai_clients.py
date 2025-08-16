import openai
import anthropic
import requests
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from config import Config, token_monitor
import logging

logger = logging.getLogger(__name__)

class ResponseCache:
    """Cache pentru răspunsuri AI"""
    
    def __init__(self):
        self.cache_file = Config.CACHE_FILE
        self.load_cache()
    
    def load_cache(self):
        """Încarcă cache-ul din fișier"""
        try:
            if Path(self.cache_file).exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            logger.error(f"Eroare la încărcarea cache-ului: {e}")
            self.cache = {}
    
    def save_cache(self):
        """Salvează cache-ul în fișier"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Eroare la salvarea cache-ului: {e}")
    
    def get_cache_key(self, prompt, model, temperature):
        """Generează cheie unică pentru cache"""
        content = f"{prompt}_{model}_{temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt, model, temperature):
        """Obține răspuns din cache"""
        key = self.get_cache_key(prompt, model, temperature)
        
        if key in self.cache:
            cached_item = self.cache[key]
            # Verifică dacă cache-ul nu a expirat
            cached_time = datetime.fromisoformat(cached_item['timestamp'])
            if datetime.now() - cached_time < timedelta(seconds=Config.CACHE_DURATION):
                logger.info("Răspuns găsit în cache")
                return cached_item['response']
        
        return None
    
    def set(self, prompt, model, temperature, response):
        """Salvează răspuns în cache"""
        key = self.get_cache_key(prompt, model, temperature)
        self.cache[key] = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        self.save_cache()

class AIClientManager:
    """Manager pentru clienții AI"""
    
    def __init__(self):
        self.cache = ResponseCache()
        self.setup_clients()
    
    def setup_clients(self):
        """Configurează clienții AI"""
        # OpenAI (pentru varianta Pro)
        if Config.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Claude (pentru STEM)
        if Config.CLAUDE_API_KEY:
            self.claude_client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)
    
    def estimate_tokens(self, text):
        """Estimează numărul de tokeni"""
        # Estimare aproximativă: 1 token ≈ 4 caractere pentru română
        return len(text) // 3
    
    def choose_model(self, subject, is_free_tier=True):
        """Alege modelul potrivit în funcție de materie și tier"""
        if not is_free_tier:
            # Pentru varianta Pro, folosește OpenAI
            return "openai", "gpt-4o"
        
        # Pentru varianta gratuită
        if subject in Config.STEM_SUBJECTS:
            return "claude", "claude-3-5-haiku-latest"
        else:
            return "deepseek", "deepseek-chat"
    
    def call_deepseek(self, messages, max_tokens=1000, temperature=0.7):
        """Apel către DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            response = requests.post(Config.DEEPSEEK_ENDPOINT, 
                                   headers=headers, 
                                   json=data, 
                                   timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"],
                "tokens_used": result.get("usage", {}).get("total_tokens", max_tokens)
            }
        
        except Exception as e:
            logger.error(f"Eroare DeepSeek API: {e}")
            raise
    
    def call_claude(self, messages, max_tokens=1000, temperature=0.7):
        """Apel către Claude API"""
        try:
            # Convertește mesajele pentru Claude
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = self.claude_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=user_messages
            )
            
            return {
                "content": response.content[0].text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens
            }
        
        except Exception as e:
            logger.error(f"Eroare Claude API: {e}")
            raise
    
    def call_openai(self, messages, model="gpt-4o", max_tokens=1000, temperature=0.7):
        """Apel către OpenAI API (pentru varianta Pro)"""
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "content": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens
            }
        
        except Exception as e:
            logger.error(f"Eroare OpenAI API: {e}")
            raise
       
    def get_free_tier_response(prompt, max_tokens=400):
        """Funcție optimizată pentru free tier"""
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=10  # Timeout mai mic pentru free
            )
            
            return {
                "content": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "provider": "openai-free",
                "from_cache": False
            }
        except Exception as e:
            logger.error(f"Eroare free tier: {e}")
            return {
                "content": "Îmi pare rău, am întâmpinat o problemă tehnică. Te rog încearcă din nou.",
                "tokens_used": 0,
                "provider": "error",
                "from_cache": False
            }

    def get_ai_response(self, prompt, subject, user_id="default", 
                       is_free_tier=True, max_tokens=1000, temperature=0.7):
        """Obține răspuns de la AI cu toate optimizările"""
        
        # Verifică cache-ul mai întâi
        provider, model = self.choose_model(subject, is_free_tier)
        cached_response = self.cache.get(prompt, model, temperature)
        
        if cached_response:
            return {
                "content": cached_response,
                "tokens_used": 0,  # Nu consumă tokeni din cache
                "provider": f"{provider} (cached)",
                "from_cache": True
            }
        
        # Estimează tokenii necesari
        estimated_tokens = self.estimate_tokens(prompt) + max_tokens
        
        # Verifică limitele pentru varianta gratuită
        if is_free_tier:
            can_use, message = token_monitor.can_use_tokens(user_id, estimated_tokens)
            if not can_use:
                raise Exception(f"Limită depășită: {message}")
        
        # Pregătește mesajele
        messages = [
            {"role": "system", "content": "Ești un profesor prietenos și empatic care ajută elevii să învețe."},
            {"role": "user", "content": prompt}
        ]
        
        # Apelează API-ul potrivit
        try:
            if provider == "deepseek":
                result = self.call_deepseek(messages, max_tokens, temperature)
            elif provider == "claude":
                result = self.call_claude(messages, max_tokens, temperature)
            elif provider == "openai":
                result = self.call_openai(messages, model, max_tokens, temperature)
            else:
                raise Exception(f"Provider necunoscut: {provider}")
            
            # Adaugă tokenii folosiți
            if is_free_tier:
                token_monitor.add_tokens(user_id, result["tokens_used"])
            
            # Salvează în cache
            self.cache.set(prompt, model, temperature, result["content"])
            
            result["provider"] = provider
            result["from_cache"] = False
            
            return result
        
        except Exception as e:
            logger.error(f"Eroare la obținerea răspunsului AI: {e}")
            raise

# Instanță globală
ai_client_manager = AIClientManager()