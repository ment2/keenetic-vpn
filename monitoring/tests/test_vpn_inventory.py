import unittest
from monitoring.vpn_inventory import inventory

def node(tag='vpn01', host='host.example', userid='UUID-A', pubkey='PUBLICKEY'):
    return {
        'protocol':'vless','tag':tag,
        'settings':{'vnext':[{'address':host,'port':443,'users':[{'id':userid,'flow':'xtls-rprx-vision'}]}]},
        'streamSettings':{'network':'tcp','security':'reality','realitySettings':{'publicKey':pubkey}}
    }

class TestInventory(unittest.TestCase):
    def test_identity_stable_across_tag_and_user(self):
        a=inventory({'outbounds':[node()]})[0]
        b=inventory({'outbounds':[node(tag='vpn09',userid='UUID-CHANGED')]})[0]
        self.assertEqual(a['node_id'],b['node_id'])
        self.assertNotEqual(a['tag'],b['tag'])
    def test_identity_changes_with_endpoint(self):
        a=inventory({'outbounds':[node()]})[0]
        b=inventory({'outbounds':[node(host='another.example')]})[0]
        self.assertNotEqual(a['node_id'],b['node_id'])
    def test_no_secret_material_in_inventory(self):
        result=str(inventory({'outbounds':[node()]}))
        self.assertNotIn('UUID-A',result)
        self.assertNotIn('PUBLICKEY',result)
        self.assertNotIn('host.example',result)
    def test_nonvless_filtered(self):
        self.assertEqual(inventory({'outbounds':[{'tag':'blocked','protocol':'blackhole'}]}),[])
    def test_duplicate_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            inventory({'outbounds':[node('vpn01'),node('vpn02')]})
    def test_invalid_tag_rejected(self):
        with self.assertRaises(ValueError):
            inventory({'outbounds':[node('random')]})
if __name__=='__main__':unittest.main()
