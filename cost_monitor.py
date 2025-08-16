import json
import time
from datetime import datetime, timedelta
import logging

class CostMonitor:
    """Monitorizează costurile pentru free tier"""
    
    def __init__(self):
        self.cost_file = "daily_costs.json"
        self.daily_limit_usd = 5.0  # Limită zilnică de $5
        
    def log_usage(self, tokens_used, model="gpt-3.5-turbo"):
        """Înregistrează utilizarea"""
        cost = self.calculate_cost(tokens_used, model)
        
        data = self.load_daily_data()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in data:
            data[today] = {"tokens": 0, "cost": 0, "requests": 0}
        
        data[today]["tokens"] += tokens_used
        data[today]["cost"] += cost
        data[today]["requests"] += 1
        
        self.save_daily_data(data)
        
        # Verifică limita
        if data[today]["cost"] > self.daily_limit_usd:
            logging.warning(f"Limita zilnică de cost depășită: ${data[today]['cost']:.4f}")
            return False
        
        return True
    
    def calculate_cost(self, tokens, model="gpt-3.5-turbo"):
        """Calculează costul pentru tokens"""
        if model == "gpt-3.5-turbo":
            return (tokens / 1000) * 0.002  # $0.002 per 1K tokens
        return 0
    
    def load_daily_data(self):
        """Încarcă datele zilnice"""
        try:
            with open(self.cost_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_daily_data(self, data):
        """Salvează datele zilnice"""
        with open(self.cost_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_daily_stats(self):
        """Returnează statisticile zilei"""
        data = self.load_daily_data()
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get(today, {"tokens": 0, "cost": 0, "requests": 0})

# Instanță globală
cost_monitor = CostMonitor()