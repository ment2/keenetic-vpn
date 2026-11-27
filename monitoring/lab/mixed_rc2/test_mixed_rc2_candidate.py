import base64, json, unittest
from mixed_rc2_candidate import build, decode, hy2, rows, collect, Unsupported, payload

def converter(uri, i):
    from urllib.parse import urlsplit
    u=urlsplit(uri)
    return {'tag':'vpn%02d'%i,'protocol':'vless','settings':{'vnext':[{'address':u.hostname,'port':u.port,'users':[{'id':'TEST_SECRET'}]}]}},None

def inventory(cfg):
    return [{'node_id':'node_'+o['settings']['vnext'][0]['address']} for o in cfg['outbounds']]

V=['vless://test@v%d.example:443'%i for i in range(10)]
H=['hysteria2://secret@hy.example:443?sni=hy.example','hy2://s%3Apass@lt.example:443?obfs=salamander&obfs-password=masksecret']

def records(lines=V+H):
    return build(base64.b64encode('\n'.join(lines).encode()),converter,inventory)

def observations(country='LT', ip='8.8.8.8', geo_ip=None, verified=True, at=1000):
    o={k:{'status':'ok','route_verified':verified,'checked_at':at,'duration_ms':42} for k in ('internet','openai','exit_ip','geo')}
    o['exit_ip']['ip']=ip; o['geo'].update(ip=geo_ip or ip,country=country)
    return o

def render(r, obs, now=1000):
    return rows([r],{r['id']:{'generation':r['generation'],'observations':obs}}, {},now)[0]

class Tests(unittest.TestCase):
    def test_twelve(self):
        r=records(); self.assertEqual(len(r),12); self.assertEqual([x['tag'] for x in r[-2:]],['hy01','hy02']); self.assertEqual(r[9]['tag'],'vpn10')
    def test_plain(self): self.assertEqual(len(decode('\n'.join(V+H).encode())),12)
    def test_vless_order(self): self.assertEqual([x['id'] for x in records(V+H)[:10]],[x['id'] for x in records(H+V)[2:]])
    def test_auth_mask(self):
        o=records()[-1]['outbound']; self.assertEqual(o['streamSettings']['hysteriaSettings']['auth'],'s:pass'); self.assertEqual(o['streamSettings']['finalmask']['udp'][0]['settings']['password'],'masksecret')
    def test_unsupported_kept(self):
        r=records(V+['hy2://pw@hy.example?insecure=1']); self.assertEqual(len(r),11); self.assertEqual(r[-1]['support'],'unsupported'); self.assertIsNone(r[-1]['outbound'])
    def test_unknown_option(self):
        for q in ['x=1','insecure=1','sni=a&sni=b','obfs=gecko','pinSHA256=aa']:
            with self.subTest(q=q),self.assertRaises(Unsupported): hy2('hy2://pw@x.example?'+q,'hy01')
    def test_option_reasons_fail_closed(self):
        for query,reason in [('ech=FAKE_ECH_SECRET','ech_unverified'),('custom=FAKE_UNKNOWN_SECRET','unsupported_option'),('sni=a&sni=b','duplicate_option'),('insecure=1&ech=FAKE_ECH_SECRET','tls_policy')]:
            with self.subTest(query=query):
                r=records(V+H[:1]+['hy2://pw@lt.example?'+query]); self.assertEqual(len(r),12)
                self.assertIsNone(r[-1]['outbound']); self.assertEqual(r[-1]['support_reason'],reason)
                x=render(r[-1],observations()); self.assertEqual(x['support_reason'],reason); self.assertFalse(x['eligible']); self.assertEqual(x['geo_policy'],'UNVERIFIED')
                self.assertNotIn('FAKE_',json.dumps(x))
    def test_tls_aliases_never_admitted(self):
        for alias in ('noverify', 'skipcertverify', 'allow_insecure', 'Insecure', 'tls-skip-verify', 'verify'):
            for value in ('0','1','false','true','FAKE_SECRET'):
                with self.subTest(alias=alias, value=value):
                    r=records(V+H[:1]+['hy2://pw@lt.example?'+alias+'='+value])[-1]
                    self.assertEqual(r['support_reason'],'tls_policy'); self.assertIsNone(r['outbound'])
                    x=render(r,observations()); self.assertFalse(x['eligible']);self.assertNotIn('FAKE_SECRET',json.dumps(x))
    def test_tls_alias_with_canonical_is_not_dropped(self):
        with self.assertRaises(Unsupported) as err: hy2('hy2://pw@x.example?insecure=0&noverify=0','hy01')
        self.assertEqual(err.exception.reason,'tls_policy')
    def test_strict_tls_unchanged(self):
        o=hy2('hy2://pw@x.example?insecure=0&sni=x.example','hy01')
        self.assertNotIn('allowInsecure',o['streamSettings']['tlsSettings'])
    def test_fm_legacy_bbr_and_timers(self):
        from urllib.parse import quote
        mask={'udp':[{'type':'salamander','settings':{'password':'masksecret'}}]}
        for v in ({'congestion':'bbr'}, {'congestion':'bbr','keepAlivePeriod':15,'maxIdleTimeout':60}, {}):
            fm=dict(mask,quicParams=v)
            u=H[1]+'&fm='+quote(json.dumps(fm),safe='')
            o=hy2(u,'hy02')['streamSettings']
            self.assertEqual(o['hysteriaSettings'],dict(v,version=2,auth='s:pass'))
            self.assertEqual(o['finalmask'],mask)
            self.assertNotIn('allowInsecure',o['tlsSettings'])
            self.assertNotIn('masksecret',json.dumps(rows(records(V+H[:1]+[u]),{}, {},1000)))
    def test_fm_rejects_unreviewed_settings(self):
        from urllib.parse import quote
        mask={'udp':[{'type':'salamander','settings':{'password':'masksecret'}}]}
        invalid=[dict(mask,quicParams={'udpHop':{}}),dict(mask,quicParams={'congestion':'brutal'}),
                 dict(mask,quicParams={'maxIdleTimeout':121}),dict(mask,quicParams={'keepAlivePeriod':True}),
                 dict(mask,quicParams={'keepAlivePeriod':1}),dict(mask,quicParams={'debug':False}),
                 dict(mask,tcp=[]),{'udp':[{'type':'salamander','settings':{'password':'different'}}]},
                 dict(mask,quicParams=[])]
        for fm in invalid:
            with self.subTest(fm=fm),self.assertRaises(Unsupported):
                hy2(H[1]+'&fm='+quote(json.dumps(fm),safe=''),'hy02')
        for raw in ('not-json','{"udp":[],"udp":[]}', '[]'):
            with self.assertRaises(Unsupported):
                hy2(H[1]+'&fm='+quote(raw,safe=''),'hy02')
    def test_fm_cannot_override_auth_or_tls(self):
        from urllib.parse import quote
        fm={'udp':[{'type':'salamander','settings':{'password':'masksecret'}}],'quicParams':{'auth':'other'}}
        with self.assertRaises(Unsupported):
            hy2(H[1]+'&fm='+quote(json.dumps(fm),safe=''),'hy02')
        fm['quicParams']={'congestion':'bbr'}
        with self.assertRaises(Unsupported):
            hy2(H[1]+'&insecure=1&fm='+quote(json.dumps(fm),safe=''),'hy02')
    def test_untrusted_reason_not_published(self):
        r=records(V+['hy2://pw@lt.example?other=FAKE_UNKNOWN_SECRET'])[-1]; r['support_reason']='FAKE_UNKNOWN_SECRET'
        self.assertEqual(render(r,observations())['support_reason'],'invalid_uri')
    def test_other_scheme(self):
        with self.assertRaises(ValueError): records(V+['trojan://pw@x.example'])
    def test_duplicate(self):
        with self.assertRaises(ValueError): records(V+H+[H[0]])
    def test_geo(self):
        for c,expected in [('LT','ALLOWED'),('RU','EXCLUDED_RU'),('BY','EXCLUDED_BY'),('ZZ','UNVERIFIED')]:
            with self.subTest(c=c):
                x=render(records()[-1],observations(c)); self.assertEqual(x['geo_policy'],expected); self.assertEqual(x['eligible'],c=='LT')
    def test_mismatch(self): self.assertEqual(render(records()[-1],observations(geo_ip='1.1.1.1'))['geo_policy'],'UNVERIFIED')
    def test_unowned(self): self.assertFalse(render(records()[-1],observations(verified=False))['eligible'])
    def test_stale(self): self.assertFalse(render(records()[-1],observations(at=1),now=2000)['eligible'])
    def test_private_ip(self): self.assertFalse(render(records()[-1],observations(ip='192.168.0.1'))['eligible'])
    def test_openai_failure(self):
        o=observations(); o['openai']['status']='http_error'; self.assertFalse(render(records()[-1],o)['eligible'])
    def test_generation(self):
        r=records()[-1]; self.assertFalse(rows([r],{r['id']:{'generation':'old','observations':observations()}},{},1000)[0]['eligible'])
    def test_no_secrets(self):
        s=json.dumps(rows(records(),{}, {},1000)); self.assertNotIn('secret',s); self.assertNotIn('TEST_SECRET',s); self.assertNotIn('generation',s)
    def test_active(self):
        r=records(); a={x['id']:x['generation'] for x in r[:4]}; v=rows(r,{},a,1000); self.assertEqual(sum(x['active'] for x in v),4); self.assertFalse(v[-1]['active'])
    def test_port_zero(self):
        r=records(V+['hy2://pw@hy.example:0']); self.assertEqual(r[-1]['support'],'unsupported'); self.assertIsNone(r[-1]['port'])
    def test_bad_percent(self):
        r=records(V+['hy2://p%ZZ@hy.example']); self.assertEqual(r[-1]['support'],'unsupported')
    def test_incoherent(self):
        o=observations(); o['geo']['checked_at']=900; self.assertEqual(render(records()[-1],o)['geo_policy'],'UNVERIFIED')
    def test_payload(self):
        r=records(); c={x['id']:{'generation':x['generation'],'observations':observations()} for x in r}; p=payload(r,c,{},1000,995,{}); self.assertEqual(p['protocol_counts'],{'vless':10,'hysteria2':2}); self.assertEqual(p['probe_complete'],12); self.assertEqual(payload(r,c,{},3000,995)['inventory_status'],'unavailable')
    def test_failed_probe_complete(self):
        r=records(); o=observations(); o['exit_ip']['status']='timeout'; c={x['id']:{'generation':x['generation'],'observations':o} for x in r}; p=payload(r,c,{},1000,995); self.assertEqual(p['probe_complete'],12); self.assertFalse(p['rows'][0]['eligible']); self.assertEqual(p['rows'][0]['exit_ip_probe']['ms'],42)
    def test_collect(self):
        class Cleanup(Exception): pass
        r=records(); c=collect(r,lambda o: observations(),100,lambda:0,Cleanup); self.assertEqual(len(c),12); self.assertEqual(len(collect(r,lambda o:observations(),54,lambda:0,Cleanup)),0)
        def fail(o): raise Cleanup()
        with self.assertRaises(Cleanup): collect(r,fail,100,lambda:0,Cleanup)

if __name__=='__main__': unittest.main()
