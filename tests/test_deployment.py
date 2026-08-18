import os
import unittest
from unittest.mock import patch

from studyforge.config import Settings


class DeploymentConfigTests(unittest.TestCase):
    def test_local_profile(self):
        with patch.dict(os.environ, {'DEPLOY_MODE': 'local', 'INFERENCE_PROVIDER': 'ollama'}, clear=False):
            cfg = Settings()
            cfg.validate()
            self.assertEqual(cfg.deploy_mode, 'local')
            self.assertEqual(cfg.inference_provider, 'ollama')

    def test_server_profile(self):
        with patch.dict(os.environ, {'DEPLOY_MODE': 'server', 'INFERENCE_PROVIDER': 'ollama'}, clear=False):
            cfg = Settings()
            cfg.validate()
            self.assertEqual(cfg.deploy_mode, 'server')

    def test_unknown_profile_is_rejected(self):
        with patch.dict(os.environ, {'DEPLOY_MODE': 'public-cloud'}, clear=False):
            cfg = Settings()
            with self.assertRaises(ValueError):
                cfg.validate()


if __name__ == '__main__':
    unittest.main()
