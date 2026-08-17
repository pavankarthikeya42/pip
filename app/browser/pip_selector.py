async def choose_pip(client, medicine):
    return await client.select_pip(medicine.get('pip_number',''), medicine.get('generic_name',''), medicine.get('brand_name',''))
