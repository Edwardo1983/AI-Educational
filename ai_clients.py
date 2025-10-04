# Gestionare clienti AI pentru variantele free si pro
import openai
import anthropic
import requests
import json
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from config import Config, token_monitor
import logging

logger = logging.getLogger(__name__)

class ResponseCache:
    """Cache pentru raspunsuri AI"""
    
    def __init__(self):
        self.cache_file = Config.CACHE_FILE
        self.load_cache()
    
    def load_cache(self):
        """Incarca cache-ul din fisier"""
        try:
            if Path(self.cache_file).exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            logger.error(f"Eroare la incarcarea cache-ului: {e}")
            self.cache = {}
    
    def save_cache(self):
        """Salveaza cache-ul in fisier"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Eroare la salvarea cache-ului: {e}")
    
    def get_cache_key(self, prompt, model, temperature):
        """Genereaza cheie unica pentru cache"""
        content = f"{prompt}_{model}_{temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt, model, temperature):
        """Obtine raspuns din cache"""
        key = self.get_cache_key(prompt, model, temperature)
        
        if key in self.cache:
            cached_item = self.cache[key]
            # Verifica daca cache-ul nu a expirat
            cached_time = datetime.fromisoformat(cached_item['timestamp'])
            if datetime.now() - cached_time < timedelta(seconds=Config.CACHE_DURATION):
                logger.info("Raspuns gasit in cache")
                return cached_item['response']
        
        return None
    
    def set(self, prompt, model, temperature, response):
        """Salveaza raspuns in cache"""
        key = self.get_cache_key(prompt, model, temperature)
        self.cache[key] = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        self.save_cache()

class AIClientManager:
    """Manager pentru clientii AI"""
    
    def __init__(self):
        self.cache = ResponseCache()
        self.setup_clients()
    
    def setup_clients(self):
        """Configureaza clientii AI"""
        # OpenAI (pentru varianta Pro)
        if Config.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Claude (pentru STEM)
        if Config.CLAUDE_API_KEY:
            self.claude_client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)
    
    def estimate_tokens(self, text):
        """Estimeaza numarul de tokeni"""
        # Estimare aproximativa: 1 token corespunde la aproximativ 4 caractere
        return len(text) // 3
    
    def choose_model(self, subject, is_free_tier=True):
        """Alege modelul potrivit in functie de materie si tier"""
        if not is_free_tier:
            if subject in Config.STEM_SUBJECTS:
                return "claude", "claude-4.5-sonnet"
            return "openai", "gpt-5"

        if subject in Config.STEM_SUBJECTS:
            return "deepseek", "deepseek-chat"

        model = random.choices(
            ["gpt-5-nano", "gpt-4.1-nano"],
            weights=[0.75, 0.25],
            k=1
        )[0]
        return "openai", model

    def call_deepseek(self, messages, model="deepseek-chat", max_tokens=1000, temperature=0.7):
        """Apel catre DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
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
    
    def call_claude(self, messages, model="claude-4.5-sonnet", max_tokens=1000, temperature=0.7):
        """Apel catre Claude API"""
        try:
            # Converteste mesajele pentru Claude
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = self.claude_client.messages.create(
                model=model,
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
    
    @staticmethod
    def _openai_messages_payload(messages):
        """Normalizeaza mesajele pentru endpoint-ul Responses"""
        payload = []
        for message in messages:
            payload.append({
                "role": message.get("role", "user"),
                "content": [
                    {"type": "text", "text": message.get("content", "")}
                ]
            })
        return payload

    @staticmethod
    def _openai_output_text(response):
        """Extrage continutul text din raspunsul Responses"""
        content = getattr(response, "output_text", None)
        if content:
            return content
        parts = []
        for item in getattr(response, "output", []):
            item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
            if item_type == "message":
                content_items = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else [])
                for sub in content_items:
                    text_value = getattr(sub, "text", None) or (sub.get("text") if isinstance(sub, dict) else None)
                    if text_value:
                        parts.append(text_value)
            elif item_type in {"output_text", "text"}:
                text_value = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                if text_value:
                    parts.append(text_value)
        return "".join(parts)

    @staticmethod
    def _openai_total_tokens(response, fallback):
        """Obtine totalul de tokeni folositi din raspuns"""
        usage = getattr(response, "usage", None)
        if usage is None:
            return fallback
        total = getattr(usage, "total_tokens", None)
        if total:
            return total
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        if input_tokens is None and isinstance(usage, dict):
            total = usage.get("total_tokens")
            if total:
                return total
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
        total = (input_tokens or 0) + (output_tokens or 0)
        return total if total else fallback

    def call_openai(self, messages, model="gpt-5", max_tokens=1000, temperature=0.7):
        """Apel catre OpenAI API (pentru varianta Pro) folosind Responses"""
        if not hasattr(self, "openai_client"):
            raise ValueError("OpenAI client nu este configurat")

        try:
            response = self.openai_client.responses.create(
                model=model,
                input=self._openai_messages_payload(messages),
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            content = self._openai_output_text(response)
            if not content:
                raise ValueError("OpenAI nu a returnat continut")

            tokens_used = self._openai_total_tokens(response, fallback=max_tokens)
            return {
                "content": content,
                "tokens_used": tokens_used
            }

        except Exception as e:
            logger.error(f"Eroare OpenAI API: {e}")
            raise

    def get_free_tier_response(self, prompt, subject, user_id="default", max_tokens=400, temperature=0.7):
        """Ruleaza fluxul free tier reutilizand mecanismul standard"""
        return self.get_ai_response(
            prompt=prompt,
            subject=subject,
            user_id=user_id,
            is_free_tier=True,
            max_tokens=max_tokens,
            temperature=temperature
        )

    def get_ai_response(self, prompt, subject, user_id="default", 
                       is_free_tier=True, max_tokens=1000, temperature=0.7):
        """Obtine raspuns de la AI cu toate optimizarile"""
        
        # Verifica cache-ul mai intai
        provider, model = self.choose_model(subject, is_free_tier)
        cached_response = self.cache.get(prompt, model, temperature)
        
        if cached_response:
            return {
                "content": cached_response,
                "tokens_used": 0,  # Nu consuma tokeni din cache
                "provider": f"{provider} (cached)",
                "from_cache": True
            }
        
        # Estimeaza tokenii necesari
        estimated_tokens = self.estimate_tokens(prompt) + max_tokens
        
        # Verifica limitele pentru varianta gratuita
        if is_free_tier:
            can_use, message = token_monitor.can_use_tokens(user_id, estimated_tokens)
            if not can_use:
                raise Exception(f"Limita depasita: {message}")
        
        # Pregateste mesajele
        messages = [
            {"role": "system", "content": "Esti un profesor prietenos si empatic care ajuta elevii sa invete."},
            {"role": "user", "content": prompt}
        ]
        
        # Apeleaza API-ul potrivit
        handlers = {
            "deepseek": lambda: self.call_deepseek(messages, model=model, max_tokens=max_tokens, temperature=temperature),
            "claude": lambda: self.call_claude(messages, model=model, max_tokens=max_tokens, temperature=temperature),
            "openai": lambda: self.call_openai(messages, model=model, max_tokens=max_tokens, temperature=temperature)
        }

        try:
            if provider not in handlers:
                raise ValueError(f"Provider necunoscut: {provider}")

            result = handlers[provider]()

            # Adauga tokenii folositi
            if is_free_tier:
                token_monitor.add_tokens(user_id, result["tokens_used"])
            
            # Salveaza in cache
            self.cache.set(prompt, model, temperature, result["content"])
            
            result["provider"] = provider
            result["from_cache"] = False
            
            return result
        
        except Exception as e:
            logger.error(f"Eroare la obtinerea raspunsului AI: {e}")
            raise

# Instanta globala
ai_client_manager = AIClientManager()

