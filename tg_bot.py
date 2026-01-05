import asyncio
from aiogram import Dispatcher

from app.heandlers import router, bot


async def main():
    dp = Dispatcher()
    dp.include_router(router)

    await asyncio.gather()
    await asyncio.gather(dp.start_polling(bot))


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
