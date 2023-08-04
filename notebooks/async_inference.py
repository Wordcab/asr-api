import json
import aiohttp

headers = {"accept": "application/json", "Content-Type": "application/json"}
params = {"url": "https://youtu.be/JZ696sbfPHs"}
# params = {"url": "https://youtu.be/CNzSJ5SGhqU"}
# params = {"url": "https://youtu.be/pmjrj_TrOEI"}
# params = {"url": "https://youtu.be/SVwLEocqK0E"}

data = {
    "alignment": False,  # Longer processing time but better timestamps
    "diarization": False,  # Longer processing time but speaker segment attribution
    "source_lang": "en",  # optional, default is "en"
    "timestamps": "s",  # optional, default is "s". Can be "s", "ms" or "hms".
    "use_batch": False,  # optional, default is False
    "internal_vad": False,  # optional, default is False
    "word_timestamps": True,  # optional, default is False
}


async def fetch(session, params):
    async with session.post(
        "http://localhost:5001/api/v1/youtube",
        headers=headers,
        params=params,
        data=json.dumps(data),
    ) as response:
        return await response.json()


async def main():
    async with aiohttp.ClientSession() as session:
        responses = await asyncio.gather(*[fetch(session, params) for _ in range(15)])
        for response in responses:
            print(response["audio_duration"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
