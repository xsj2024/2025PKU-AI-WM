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
from manager import Manager
from shop import Shop
from move import Move
from rest import Rest

# File path constants
DATA_DIR = "D:\\conda\\camel\\game_data"
STATUS_FILE = f"{DATA_DIR}/status.json"
CARD_KB_FILE = f"./game_info/card_info.json"
SHOP_FILE = f"{DATA_DIR}/shop.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"
class SlaytheSpire:
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        self.manager=Manager()
        self.shop=Shop(self.manager)
        self.move=Move(self.manager)
        self.rest=Rest(self.manager)
        self.command_map = {
            # Existing manual commands
            "node": self.manager.set_current,
            "health": self.manager.set_hp,
            "maxhp": self.manager.set_maxhp,
            "gold": self.manager.set_gold,
            "card": self.manager.handle_deck,
            "relic": self.manager.handle_relics,
            "potion": self.manager.handle_potions,
            # New AI commands
            "move": self.move.handle,
            "shop": self.shop.handle,
            "rest": self.rest.handle,
            #"chat": self.chat.handle,
           # "exit": self.exit_game
        }        
        

    def exit_game(self, args: List[str]) -> None:
        """Exit game"""
        self.manager.save_data()
        print("Game data saved, goodbye!")
        sys.exit(0)

    def show_help(self) -> None:
        """Show help information"""
        help_text = """
        █ Command Manual █████████████████████████████
        
        [Basic commands]
          node <id>        - Set current node
          health <value>   - Set health value (0-MAX)
          maxhp <value>    - Set maximum health value
          gold <value>     - Set gold amount
        
        [Card management]
          card ins <name> <true/false> - Add card
          card del <name>             - Delete card
          card upgrade <name>         - Upgrade card
        
        [Relic/Potion]
          relic add <name> - Add relic
          relic del <name> - Delete relic
          potion add <name> - Add potion
          potion del <name> - Delete potion
        
        [AI Decisions]
          move  - Recommended movement path
          shop  - Shop purchase suggestions
          rest  - Rest strategy  
          chat  - 与AI进行策略对话
        
        exit   - Save and exit game
        ████████████████████████████████████
        """
        print(help_text)
    def handle(self,cmd_input: List[str]):
        cmd = cmd_input[0].lower()
        args = cmd_input[1:]
        print(cmd)
        print(args)
        return self.command_map[cmd](args)
    #def main(self) -> None:
        # """Main loop"""
        # print("=== Spire Climb Decision System ===")
        
        # while True:
        #     try:
        #         # Show current status
        #         status = self.manager.data
        #         print(f"\nCurrent position: Node {status['current_node']} | Health: {status['health']}/{status['max_health']} | Gold: {status['gold']}")
        #         print(f"Relics: {', '.join(status['relics']) or 'None'}")
        #         print(f"Potions: {', '.join(status['potions']) or 'None'}")
        #         print(f"Deck: {', '.join(c[0] + ('+' if c[1] else '') for c in status['deck']) or 'None'}")
                
        #         # Get input
        #         cmd_input = input("\n▶ Enter command (help for manual): ").strip().split()
        #         if not cmd_input:
        #             continue
                    
        #         cmd = cmd_input[0].lower()
        #         args = cmd_input[1:]
                
        #         if cmd == "help":
        #             self.show_help()
        #         elif cmd in self.command_map:
        #             self.command_map[cmd](args)
        #         else:
        #             print("Invalid command! Enter 'help' for manual")
                    
        #     except KeyboardInterrupt:
        #         self.exit_game([])
        #     except Exception as e:
               

                # print(f"错误: {str(e)}")


#if __name__ == "__main__":
   # SlaytheSpire().main()
