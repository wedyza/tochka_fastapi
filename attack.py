import asyncio
import aiohttp

async def fetch(session, url):
    async with session.post(url) as response:
        pass

async def main():
    url = 'http://http://158.160.136.82/api/v1/order'
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for _ in range(5)]
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())