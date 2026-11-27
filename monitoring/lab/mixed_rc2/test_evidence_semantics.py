"""Synthetic evidence semantics. No network connections, live configuration or credentials."""
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch
from monitoring import rc2_probe
from mixed_rc2_candidate import rows, generation

NOW=1000
KINDS=('internet','openai','exit_ip','geo')
RESPONSES={'internet':b'204','openai':b'401','exit_ip':b'{"ip":"8.8.8.8"}','geo':b'{"success":true,"ip":"8.8.8.8","country_code":"LT"}'}
RECORD={'id':'synthetic','tag':'synthetic','protocol':'hysteria2','host':'synthetic.invalid','port':443,'support':'ready','outbound':{'tag':'synthetic'}}
RECORD['generation']=generation(RECORD['outbound'])

def observations(faults=None):
    faults=faults or {}
    result={}
    for k in KINDS:
        rc,body,owned=faults.get(k,(0,RESPONSES[k],True))
        # Existing classification code; simulated ownership, not actual packet evidence.
        with patch.object(rc2_probe,'live_owner',return_value=owned), patch.object(rc2_probe,'request',return_value=CompletedProcess([],rc,body)), patch.object(rc2_probe.time,'time',return_value=NOW):
            result[k]=rc2_probe.observe(object(),0,k)
    return result

def render(obs):
    return rows([RECORD],{'synthetic':{'generation':RECORD['generation'],'observations':obs}}, {}, NOW)[0]

class EvidenceTests(unittest.TestCase):
    def test_all_positive_control(self):
        r=render(observations())
        self.assertEqual(r['vpn']['status'],'ok')
        self.assertTrue(r['eligible'])
    def test_http204_timeout_does_not_prove_tunnel_failure(self):
        r=render(observations({'internet':(28,b'',True)}))
        self.assertEqual(r['internet']['status'],'timeout')
        self.assertEqual(r['vpn']['status'],'ok')
        self.assertEqual(r['geo_policy'],'ALLOWED')
        self.assertFalse(r['eligible'])
        self.assertEqual(r['exit_ip'],'8.8.8.8')
    def test_http403_is_not_a_transport_failure(self):
        r=render(observations({'internet':(0,b'403',True)}))
        self.assertEqual(r['internet']['status'],'http_error')
        self.assertEqual(r['vpn']['status'],'ok')
        self.assertFalse(r['eligible'])
    def test_exit_ip_alone_does_not_admit(self):
        r=render(observations({k:(28,b'',True) for k in ('internet','openai','geo')}))
        self.assertEqual(r['vpn']['status'],'ok')
        self.assertEqual(r['geo_policy'],'UNVERIFIED')
        self.assertFalse(r['eligible'])
    def test_no_positive_observation(self):
        r=render(observations({k:(28,b'',True) for k in KINDS}))
        self.assertEqual(r['vpn']['status'],'not_confirmed')
        self.assertFalse(r['eligible'])
        self.assertIsNone(r['exit_ip'])
    def test_success_without_ownership_is_rejected(self):
        r=render(observations({k:(0,RESPONSES[k],False) for k in KINDS}))
        self.assertEqual(r['vpn']['status'],'not_confirmed')
        self.assertFalse(r['eligible'])
    def test_ip_disagreement_fails_closed(self):
        r=render(observations({'geo':(0,b'{"success":true,"ip":"1.1.1.1","country_code":"LT"}',True)}))
        self.assertEqual(r['geo_policy'],'UNVERIFIED')
        self.assertEqual(r['geo']['status'],'ip_mismatch')
        self.assertFalse(r['eligible'])
    def test_ru_by_excluded_even_with_positive_http(self):
        for c in ('RU','BY'):
            with self.subTest(country=c):
                body=('{"success":true,"ip":"8.8.8.8","country_code":"%s"}'%c).encode()
                r=render(observations({'geo':(0,body,True)}))
                self.assertEqual(r['geo_policy'],'EXCLUDED_'+c)
                self.assertFalse(r['eligible'])

if __name__=='__main__': unittest.main(verbosity=2)
