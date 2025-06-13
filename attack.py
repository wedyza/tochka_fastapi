import asyncio
import aiohttp

async def fetch(session, url):
    async with session.post(url=url, json={
        'ticker': 'RAND',
        'qty': 5,
        'direction': 'BUY'
    }, headers={
        'Authorization': 'TOKEN eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYzNjZTkxYzQtZjhiZS00NTFmLTg3MTktNGI1YTkwYmIyOGMwIn0.SsfZK8rLIBMr14RsHuNXwOAmqDQwGIS3SdZJNPwxq_M'
    }) as response:
        pass

async def main():
    url = 'http://localhost:8000/api/v1/order'
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for _ in range(15)]
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())