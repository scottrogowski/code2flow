import asyncio

class A:
    def __init__(self):
        pass
    async def test(self):
        print("hello world")

async def main():
    a = A()
    await a.test()

asyncio.run(main())
