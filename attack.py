import asyncio
import aiohttp

async def fetch(session, url):
    async with session.post(url=url, json={
        'ticker': 'RAND',
        'qty': 5,
        'direction': 'SELL'
    }, headers={
        'Authorization': 'TOKEN eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiY2Y4OWQxYTEtOWQzZC00OTFhLWIwZjgtNjhkZGVmYjMxZmY0In0.CI44lu3QsiAKEVut2vt1U7rpXQBeRozqF0ks2rIdR5A'
    }) as response:
        pass

async def main():
    url = 'http://158.160.136.82/api/v1/order'
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for _ in range(15)]
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())