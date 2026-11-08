"""Security regression tests for public-URL/SSRF restrictions."""
import socket
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cite-check-tr/scripts'))
from network_safety import validate_url


def dns_for(ip='8.8.8.8'):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]


class NetworkSafetyTests(unittest.TestCase):
    def test_local_and_private_ip_literals_blocked(self):
        urls = ['http://127.0.0.1:80', 'http://10.0.0.5', 'http://169.254.169.254/',
                'http://[::1]/', 'http://localhost/', 'https://service.local/',
                'http://user:password@mevzuat.gov.tr/', 'file:///etc/passwd',
                'http://mevzuat.gov.tr:9000/']
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_unlisted_public_domain_blocked(self):
        with patch('network_safety.socket.getaddrinfo', return_value=dns_for()):
            with self.assertRaises(ValueError):
                validate_url('https://example.org/doc')
            self.assertEqual(validate_url('https://example.org/doc', ['example.org']), 'https://example.org/doc')
            self.assertEqual(validate_url('https://cdn.tbmm.gov.tr/doc'), 'https://cdn.tbmm.gov.tr/doc')

    def test_sneaky_official_lookalike_blocked(self):
        with self.assertRaises(ValueError):
            validate_url('https://mevzuat.gov.tr.evil.example.org/a')

    def test_private_dns_resolution_blocked_even_on_official_host(self):
        for ip in ['127.0.0.1', '10.0.5.9', '192.168.1.6', '169.254.169.254', '0.0.0.0']:
            with self.subTest(ip=ip), patch('network_safety.socket.getaddrinfo', return_value=dns_for(ip)):
                with self.assertRaises(ValueError):
                    validate_url('https://karararama.yargitay.gov.tr/')

    def test_mixed_dns_resolution_fail_closed(self):
        with patch('network_safety.socket.getaddrinfo', return_value=dns_for('8.8.8.8') + dns_for('192.168.0.2')):
            with self.assertRaises(ValueError):
                validate_url('https://www.kvkk.gov.tr/')

    def test_dns_failure_rejected(self):
        with patch('network_safety.socket.getaddrinfo', side_effect=socket.gaierror('unavailable')):
            with self.assertRaises(ValueError):
                validate_url('https://www.mevzuat.gov.tr/')


if __name__ == '__main__':
    unittest.main()
