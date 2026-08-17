from app.validation.normalizer import norm,norm_id

def test_norm(): assert norm('  Hello\n World ')=='hello world'
def test_id(): assert norm_id(' EMEA-001 ')=='emea-001'
