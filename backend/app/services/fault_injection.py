import asyncio
async def delay(mode):
    if mode == "SLOW_RESPONSE": await asyncio.sleep(1)
