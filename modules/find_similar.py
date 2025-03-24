import json
import os
import requests
from typing import Dict, Any, Optional
from pathlib import Path

class FindSimilarAgent:
    def __init__(self):
        self.config = self._load_config()
        self.headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации LLM"""
        config_path = Path(__file__).parent.parent / "config" / "llm_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def process_query(self, user_text: str) -> Dict[str, Any]:
        """
        Обработка запроса пользователя и генерация function call
        
        Args:
            user_text: Текст запроса от пользователя
            
        Returns:
            Dict с результатами function call и slot filling
        """
        try:
            url = f"{self.config['base_url']}/chat/completions"
            
            payload = {
                "model": self.config["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "Вы - AI агент, который анализирует запросы пользователя и определяет параметры для поиска информации."
                    },
                    {
                        "role": "user",
                        "content": user_text
                    }
                ],
                "functions": self.config["functions"],
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_tokens"]
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Получаем function call из ответа
            function_call = result.get("choices", [{}])[0].get("message", {}).get("function_call")
            
            if function_call:
                return {
                    "function_name": function_call.get("name"),
                    "parameters": json.loads(function_call.get("arguments", "{}")),
                    "raw_response": result.get("choices", [{}])[0].get("message", {}).get("content")
                }
            else:
                return {
                    "error": "Не удалось определить параметры для поиска",
                    "raw_response": result.get("choices", [{}])[0].get("message", {}).get("content")
                }
                
        except Exception as e:
            return {
                "error": f"Ошибка при обработке запроса: {str(e)}",
                "raw_response": None
            }
    
    def fill_slots(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Заполнение слотов на основе function call
        
        Args:
            function_call: Результат function call
            
        Returns:
            Dict с заполненными слотами
        """
        if "error" in function_call:
            return function_call
            
        try:
            parameters = function_call["parameters"]
            return {
                "query": parameters.get("query", ""),
                "query_type": parameters.get("query_type", "all"),
                "target_type": parameters.get("target_type", "all")
            }
        except Exception as e:
            return {
                "error": f"Ошибка при заполнении слотов: {str(e)}",
                "raw_response": function_call
            }
