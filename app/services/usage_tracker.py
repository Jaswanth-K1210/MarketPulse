"""
Gemini API Usage Tracker
Monitors and logs API calls to ensure efficient credit usage
"""
import json
import os
from datetime import datetime
from pathlib import Path

USAGE_LOG_PATH = Path(__file__).parent.parent / "data" / "gemini_usage.json"

class UsageTracker:
    def __init__(self):
        self.usage_data = self._load_usage()
    
    def _load_usage(self):
        """Load usage data from file"""
        if USAGE_LOG_PATH.exists():
            try:
                with open(USAGE_LOG_PATH, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"daily_requests": {}, "total_requests": 0}
    
    def _save_usage(self):
        """Save usage data to file"""
        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG_PATH, 'w') as f:
            json.dump(self.usage_data, f, indent=2)
    
    def log_request(self, model: str, input_chars: int, output_chars: int):
        """Log a Gemini API request"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.usage_data["daily_requests"]:
            self.usage_data["daily_requests"][today] = {
                "count": 0,
                "input_chars": 0,
                "output_chars": 0,
                "estimated_cost": 0.0
            }
        
        # Gemini 2.5 Flash pricing: $0.000075 per 1K chars (input), $0.0003 per 1K chars (output)
        input_cost = (input_chars / 1000) * 0.000075
        output_cost = (output_chars / 1000) * 0.0003
        total_cost = input_cost + output_cost
        
        self.usage_data["daily_requests"][today]["count"] += 1
        self.usage_data["daily_requests"][today]["input_chars"] += input_chars
        self.usage_data["daily_requests"][today]["output_chars"] += output_chars
        self.usage_data["daily_requests"][today]["estimated_cost"] += total_cost
        self.usage_data["total_requests"] += 1
        
        self._save_usage()
        
        print(f"📊 Gemini Usage: {self.usage_data['daily_requests'][today]['count']} requests today | "
              f"${self.usage_data['daily_requests'][today]['estimated_cost']:.4f} cost | "
              f"${10.00 - sum(day['estimated_cost'] for day in self.usage_data['daily_requests'].values()):.2f} credits remaining")
    
    def get_daily_stats(self):
        """Get today's usage stats"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.usage_data["daily_requests"].get(today, {
            "count": 0, "input_chars": 0, "output_chars": 0, "estimated_cost": 0.0
        })

# Singleton
usage_tracker = UsageTracker()
