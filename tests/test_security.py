import unittest
from types import SimpleNamespace
import studyforge.security as security


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.old=security.settings

    def tearDown(self):
        security.settings=self.old

    def test_server_requires_token(self):
        security.settings=SimpleNamespace(deploy_mode='server',api_token='')
        with self.assertRaises(RuntimeError):
            security.validate_server_security()

    def test_local_does_not_require_token(self):
        security.settings=SimpleNamespace(deploy_mode='local',api_token='')
        security.validate_server_security()
        self.assertFalse(security.auth_required())

if __name__=='__main__': unittest.main()
