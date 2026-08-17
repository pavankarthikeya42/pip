import asyncio
async def retry_async(fn, retries=2):
    last=None
    for i in range(retries+1):
        try:return await fn()
        except Exception as e:
            last=e
            if i<retries: await asyncio.sleep(1+i)
    raise last
