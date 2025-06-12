import os
import re
import json
import sys
import math
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType


# File path constants
DATA_DIR = "D:\\conda\\camel\\game_data"
STATUS_FILE = f"{DATA_DIR}/status.json"
CARD_KB_FILE = f"./game_info/card_info.json"
SHOP_FILE = f"{DATA_DIR}/shop.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"
class Move:
    def __init__(self,manager):
        self.manager=manager
    # === AI decision methods ===
    def handle(self, args: List[str]) -> None:
        """CAMEL-AI based movement decision"""
        current_node = self.manager.data["current_node"]
        available_nodes = self.manager.data["map"][current_node]["next"]  # Use next field
        # ===== Build CAMEL-AI specific Prompt =====

        player_status = {
            "health": f"{self.manager.data['health']}/{self.manager.data['max_health']}",
            "gold": self.manager.data["gold"],
            "relics": self.manager.data["relics"],
            "potions": self.manager.data["potions"]
        }
        
        # Dynamically build path options description
        path_options = []
        for node_id in available_nodes:
            node_data = self.manager.data["map"][node_id]
            path_options.append({
                "node": node_id,
                "type": node_data["type"],
                "data": node_data.get("data", {})
            })
        
        prompt = {
            "task": "Choose optimal movement path",
            "input": {
                "current_node": current_node,
                "player_status": player_status,
                "path_options": path_options
            },
            "output_requirements": {
                "format": """{
                    "target": "node ID", 
                    "reasons": ["strategy reason 1", "strategy reason 2"],
                    "risk_assessment": "potential risk explanation"
                }""",
                "rules": [
                    "Prioritize rest nodes when health below 50%",
                    "Favor combat when having 'Burning Blood' relic",
                    "Prioritize shop when gold exceeds 200"
                ]
            }
        }

            # ===== Call CAMEL-AI model =====
        response = self.manager.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
        raw_text = response.msg.content
        json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]  # Extract possible JSON portion
        decision = json.loads(json_str)
        print(response.msg.content)
        # ===== Visual output =====
        self._print_decision_panel(
            title="Path Decision",
            target=decision["target"],
            reasons=decision["reasons"],
            warning=decision.get("risk_assessment", "No significant risk")
        )
        
        # Automatically execute movement
        self.self.manager.set_current([decision["target"]])

    def _print_decision_panel(self, title: str, target: str, reasons: list, warning: str):
        """Professional decision panel output"""
        border = "╔" + "═"*(len(title)+6) + "╗"
        print(f"\n{border}")
        print(f"║  {title.upper():^{len(title)+2}}  ║")
        print("╠" + "═"*(len(title)+6) + "╣")
        
        max_len = max(len(border), 40)  # Minimum width 40
        print(f"║ Target node: {target.ljust(max_len-15)} ║")
        print("╠" + "─"*(max_len-2) + "╣")
        
        for i, reason in enumerate(reasons[:3], 1):
            print(f"║ {i}. {reason.ljust(max_len-6)} ║")
        
        print("╠" + "─"*(max_len-2) + "╣")
        print(f"║ ! Risk warning: {warning.ljust(max_len-13)} ║")
        print("╚" + "═"*(max_len-2) + "╝")

