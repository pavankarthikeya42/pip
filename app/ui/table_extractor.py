def canonical_table(table: dict):
    headers=[str(x).strip() for x in table.get("headers", [])]
    rows=[]
    for r in table.get("rows", []):
        rows.append({headers[i] if i < len(headers) else f"column_{i}": str(v).strip() for i,v in enumerate(r)})
    return {"headers":headers,"rows":rows}
