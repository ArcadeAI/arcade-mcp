import asyncio

from arcade.core.config import Config
from arcade.core.config_model import ApiConfig, UserConfig

from evals.eval_search_recent_tweets_by_keywords import x_eval_suite


async def iteration():
    # run 3 times
    results = []
    tasks = []
    for _ in range(3):
        task = asyncio.create_task(
            x_eval_suite(
                config=Config(
                    api=ApiConfig(key="arc_o1RFXRqfSkCqFD8PYv9ANJHjTMqBcS52HcFus5jBe5oC2Y4GATAq"),
                    user=UserConfig(email="eric@arcade.dev"),
                ),
                base_url="http://localhost:9099",
                model="gpt-4o",
                max_concurrency=1,
            )
        )
        tasks.append(task)

    for f in asyncio.as_completed(tasks):
        results.append(await f)

    return results


async def optimize():
    # run 100 times
    for _ in range(2):
        results = await iteration()
        print(results)
        print("-\n" * 10)


if __name__ == "__main__":
    asyncio.run(optimize())
