import json
import os
import logging
from typing import Dict, Any, List

TEMPLATE_PERFORMANCE_FILE = "data/template_performance.json"

class ContextAwareProcessor:
    def __init__(self):
        self.template_performance = self._load_performance_data()

    def _load_performance_data(self) -> Dict:
        if os.path.exists(TEMPLATE_PERFORMANCE_FILE):
            with open(TEMPLATE_PERFORMANCE_FILE, 'r') as f:
                return json.load(f)
        return {}

    def _save_performance_data(self):
        os.makedirs(os.path.dirname(TEMPLATE_PERFORMANCE_FILE), exist_ok=True)
        with open(TEMPLATE_PERFORMANCE_FILE, 'w') as f:
            json.dump(self.template_performance, f, indent=2)

    def update_template_performance(self, template_name: str, company_cluster: str, success: bool):
        # For simplicity, company_cluster can be company_name for now
        # In a more advanced system, you'd cluster companies based on industry, size, etc.
        key = f"{company_cluster}:{template_name}"
        if key not in self.template_performance:
            self.template_performance[key] = {"sent": 0, "replied": 0, "success_rate": 0.0}
        
        self.template_performance[key]["sent"] += 1
        if success:
            self.template_performance[key]["replied"] += 1
        
        self.template_performance[key]["success_rate"] = self.template_performance[key]["replied"] / self.template_performance[key]["sent"]
        self._save_performance_data()
        logging.info(f"Updated template performance for {key}: {self.template_performance[key]}")

    def select_optimal_template(self, available_templates: List[str], company_cluster: str) -> str:
        best_template = None
        highest_success_rate = -1.0

        for template in available_templates:
            key = f"{company_cluster}:{template}"
            if key in self.template_performance:
                rate = self.template_performance[key]["success_rate"]
                if rate > highest_success_rate:
                    highest_success_rate = rate
                    best_template = template
        
        if best_template:
            logging.info(f"Selected optimal template '{best_template}' for cluster '{company_cluster}' with success rate {highest_success_rate}")
            return best_template
        else:
            # Fallback to a default or random template if no performance data exists
            logging.info(f"No performance data for cluster '{company_cluster}'. Falling back to first available template.")
            return available_templates[0] if available_templates else "value_proposition"

context_aware_processor = ContextAwareProcessor()