from app.validation.table_validator import compare_tables

def test_reordered_rows():
    p={'rows':[{'Area':'Quality','Description':'A'},{'Area':'Clinical','Description':'B'}]}
    u={'rows':[{'Area':'Clinical','Description':'B'},{'Area':'Quality','Description':'A'}]}
    r=compare_tables(p,u)
    assert not r['missing_rows'] and not r['mismatches']
