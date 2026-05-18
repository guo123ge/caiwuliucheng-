import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.project_root = Path(__file__).parent.resolve()
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"

        load_dotenv(self.project_root / ".env")

        self._accounts: Dict = {}
        self._categories: Dict = {}
        self._subject_mapping: Dict = {}
        self._tax_rules: Dict = {}

        self._load_all()

    def _load_json(self, filename: str) -> Dict:
        path = self.config_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_all(self):
        self._accounts = self._load_json("accounts.json")
        self._categories = self._load_json("categories.json")
        self._subject_mapping = self._load_json("subject_mapping.json")
        self._tax_rules = self._load_json("tax_rules.json")

    def reload(self):
        self._load_all()

    @property
    def accounts(self) -> List[Dict]:
        return self._accounts.get("accounts", [])

    @property
    def file_patterns(self) -> Dict:
        return self._accounts.get("file_patterns", {})

    @property
    def data_dirs(self) -> Dict[str, str]:
        raw = self._accounts.get("data_dirs", {})
        resolved = {}
        for key, rel_path in raw.items():
            abs_path = (self.project_root / rel_path).resolve()
            resolved[key] = str(abs_path)
        return resolved

    @property
    def bank_categories(self) -> Dict:
        return self._categories.get("bank_transaction_categories", {})

    @property
    def invoice_categories(self) -> Dict:
        return self._categories.get("invoice_categories", {})

    @property
    def llm_threshold(self) -> Dict:
        return self._categories.get("llm_threshold", {})

    @property
    def category_subject_mapping(self) -> Dict:
        return self._subject_mapping.get("category_subject_mapping", {})

    @property
    def invoice_subject_mapping(self) -> Dict:
        return self._subject_mapping.get("invoice_subject_mapping", {})

    @property
    def tax_rules(self) -> Dict:
        return self._tax_rules

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "deepseek")

    @property
    def deepseek_api_key(self) -> str:
        return os.getenv("DEEPSEEK_API_KEY", "")

    @property
    def deepseek_base_url(self) -> str:
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    @property
    def deepseek_model(self) -> str:
        return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def ollama_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    def get_subject_for_category(self, category: str) -> Optional[Dict]:
        return self.category_subject_mapping.get(category)

    def get_invoice_subject(self, category: str) -> Optional[Dict]:
        return self.invoice_subject_mapping.get(category)

    def get_category_keywords(self, category: str) -> List[str]:
        cat_info = self.bank_categories.get(category, {})
        return cat_info.get("keywords", [])

    def get_invoice_keywords(self, category: str) -> List[str]:
        cat_info = self.invoice_categories.get(category, {})
        return cat_info.get("keywords", [])

    def get_all_bank_keywords_map(self) -> Dict[str, List[str]]:
        return {
            cat: info.get("keywords", [])
            for cat, info in self.bank_categories.items()
        }

    def get_all_invoice_keywords_map(self) -> Dict[str, List[str]]:
        return {
            cat: info.get("keywords", [])
            for cat, info in self.invoice_categories.items()
        }


config = Config()
