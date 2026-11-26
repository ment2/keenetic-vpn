"""Pure scheduling core; persist returned state atomically in caller."""
def observe(state, digest, now, delay=3600):
    s = dict(state)
    if digest == s.get('committed'):
        s.pop('since', None)
        return s, False
    s.setdefault('since', now)
    return s, now - s['since'] >= delay

def acknowledge(state, digest):
    return {'committed': digest}
