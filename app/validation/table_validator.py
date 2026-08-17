from .normalizer import norm

def row_key(row):
    vals=list(row.values())
    return norm(vals[0]) if vals else ""

def compare_tables(pdf_table, ui_table):
    p_rows={row_key(r):r for r in pdf_table.get("rows",[])}
    u_rows={row_key(r):r for r in ui_table.get("rows",[])}
    missing=[p_rows[k] for k in p_rows.keys()-u_rows.keys()]
    extra=[u_rows[k] for k in u_rows.keys()-p_rows.keys()]
    mismatches=[]
    for k in p_rows.keys() & u_rows.keys():
        if {norm(a):norm(v) for a,v in p_rows[k].items()} != {norm(a):norm(v) for a,v in u_rows[k].items()}:
            mismatches.append({"key":k,"pdf":p_rows[k],"ui":u_rows[k]})
    return {"missing_rows":missing,"extra_rows":extra,"mismatches":mismatches}
