async def extract_comparison(client, row):
    return await client.compare(row)
