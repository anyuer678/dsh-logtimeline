"""config.py 基线测试：环境变量读取与校验矩阵。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from config import ConfigError, load_config_from_env

VALID = {"LLM_BASE_URL": "https://api.example.com/", "LLM_API_KEY": "sk-x", "LLM_MODEL": "m1"}


class TestLoadConfigFromEnv(unittest.TestCase):
    def test_valid_full(self):
        cfg = load_config_from_env(VALID)
        self.assertEqual(cfg.base_url, "https://api.example.com")  # 尾斜杠被剥
        self.assertEqual(cfg.api_key, "sk-x")
        self.assertEqual(cfg.model, "m1")
        self.assertEqual(cfg.timeout, 30)  # 缺省 30

    def test_missing_each_key(self):
        for key in VALID:
            env = {k: v for k, v in VALID.items() if k != key}
            with self.assertRaises(ConfigError) as ctx:
                load_config_from_env(env)
            self.assertIn(key, str(ctx.exception))

    def test_timeout_non_int(self):
        with self.assertRaises(ConfigError):
            load_config_from_env({**VALID, "LLM_TIMEOUT": "abc"})

    def test_timeout_non_positive(self):
        with self.assertRaises(ConfigError):
            load_config_from_env({**VALID, "LLM_TIMEOUT": "0"})
        with self.assertRaises(ConfigError):
            load_config_from_env({**VALID, "LLM_TIMEOUT": "-5"})

    def test_timeout_custom(self):
        cfg = load_config_from_env({**VALID, "LLM_TIMEOUT": "12"})
        self.assertEqual(cfg.timeout, 12)

    def test_empty_mapping_raises(self):
        with self.assertRaises(ConfigError):
            load_config_from_env({})


if __name__ == "__main__":
    unittest.main()
