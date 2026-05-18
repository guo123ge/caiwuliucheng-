import json
import time
from typing import Any, Dict, List, Optional

from config import config


class LLMClient:
    def __init__(self):
        self.provider = config.llm_provider

    def _call_deepseek(self, messages: List[Dict], temperature: float = 0.1,
                       max_tokens: int = 4096) -> Dict:
        import requests

        headers = {
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.deepseek_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{config.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _call_openai(self, messages: List[Dict], temperature: float = 0.1,
                     max_tokens: int = 4096) -> Dict:
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key)

        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=config.openai_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.model_dump()
            except Exception:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _call_ollama(self, messages: List[Dict], temperature: float = 0.1,
                     max_tokens: int = 4096) -> Dict:
        import requests

        payload = {
            "model": config.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{config.ollama_base_url}/api/chat",
                    json=payload,
                    timeout=180,
                )
                resp.raise_for_status()
                result = resp.json()
                return {
                    "choices": [{
                        "message": {
                            "content": result.get("message", {}).get("content", "")
                        }
                    }]
                }
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except requests.exceptions.RequestException:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def chat(self, messages: List[Dict], temperature: float = 0.1,
             max_tokens: int = 4096) -> str:
        if self.provider == "openai":
            resp = self._call_openai(messages, temperature, max_tokens)
        elif self.provider == "ollama":
            resp = self._call_ollama(messages, temperature, max_tokens)
        else:
            resp = self._call_deepseek(messages, temperature, max_tokens)

        choices = resp.get("choices", [])
        if not choices:
            raise RuntimeError(f"LLM 返回空结果: {resp}")

        content = choices[0].get("message", {}).get("content", "")
        return content

    def classify_batch(
        self,
        items: List[Dict[str, str]],
        categories: List[str],
        category_descriptions: Dict[str, str],
    ) -> List[Dict]:
        if not items:
            return []

        cat_list = "\n".join(
            f"{i+1}. {cat} — {category_descriptions.get(cat, '')}"
            for i, cat in enumerate(categories)
        )

        items_text = ""
        for i, item in enumerate(items):
            items_text += f"[{i}]\n"
            for k, v in item.items():
                items_text += f"  {k}: {v}\n"
            items_text += "\n"

        prompt = f"""你是一位专业的财务会计，请为以下 {len(items)} 条交易记录批量分类。

【可选分类】
{cat_list}

【交易记录】
{items_text}

【输出格式】
请严格按照以下JSON数组格式输出，每个元素对应一条记录：
[
  {{
    "index": 0,
    "category": "分类名称",
    "confidence": 0.95,
    "reason": "判断依据"
  }},
  ...
]

请只输出JSON数组，不要额外内容。"""

        messages = [
            {"role": "system", "content": "你是一位专业的财务会计，擅长银行流水和发票分类。请严格按JSON格式输出。"},
            {"role": "user", "content": prompt},
        ]

        response = self.chat(messages, temperature=0.1, max_tokens=4096)

        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])
            results = json.loads(json_str)
            if not isinstance(results, list):
                results = [results]
            return results
        except json.JSONDecodeError:
            if config.debug:
                print(f"[DEBUG] LLM返回解析失败，原始响应: {response[:500]}")
            return [
                {"index": i, "category": "其他", "confidence": 0.0, "reason": "解析失败"}
                for i in range(len(items))
            ]


llm_client = LLMClient()
