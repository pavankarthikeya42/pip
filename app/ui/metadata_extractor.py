def normalize_metadata_keys(data: dict) -> dict:
    aliases = {
      "generic":"generic_name", "generic name":"generic_name",
      "brand":"brand_name", "brand name":"brand_name",
      "sponsor":"sponsor", "pip number":"pip_number",
      "decision number":"decision_number", "decision date":"decision_date",
      "decision type":"decision_type", "status":"status",
      "therapeutic areas":"therapeutic_area", "therapeutic area":"therapeutic_area",
      "condition / indication":"condition_indication", "condition/indication":"condition_indication"
    }
    return {aliases.get(k.strip().casefold(), k.strip().casefold()):v for k,v in data.items()}
