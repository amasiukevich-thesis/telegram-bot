import os
from datetime import datetime, time, timedelta
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from typing import List, Tuple

from db_stuff import Subscription, Base


# TODO: How do I add those to the container?
APP_TOKEN = os.environ.get("APP_TOKEN")


storage = MemoryStorage()
bot = Bot(token=APP_TOKEN)
dp = Dispatcher(bot, storage=storage)


# database_session
HOST = os.environ.get("POSTGRES_HOST")
PORT = os.environ.get("POSTGRES_PORT")
USER = os.environ.get("POSTGRES_USER")
PASSWORD = os.environ.get("POSTGRES_PASSWORD")
DATABASE_NAME = os.environ.get("POSTGRES_DB")

connection_string = f'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE_NAME}'
engine = create_engine(connection_string, pool_size=10, max_overflow=20)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


message = "This is a daily message"

sending_time = time(hour=23, minute=10)

@dp.message_handler(commands="start")
async def start(payload: types.Message):
    await payload.reply(
        """
        Welcome to Crypto Predictor bot.
        Please type the command /help to get to know how to use it.
    """
    )


@dp.message_handler(commands="help")
async def help(payload: types.Message):
    # TODO: Fetch it later from the DB
    cryptos_to_subscribe = ["ETH"]
    await payload.reply(f"""Current available cryptos to subscribe : {','.join(cryptos_to_subscribe)}""")


@dp.message_handler(commands="subscribe")
@dp.message_handler(lambda message: message.text.startswith("subscribe "))
async def subscribe(message: types.Message):

    user_id = message.from_user.id

    crypto_candidate = message.text.split(' ')
    if len(crypto_candidate) > 1:

        # TODO: validate the crypto candidate over the database
        crypto_candidate = crypto_candidate[1].upper()

        distinct_values = [
            symbol.split('/')[0].upper() for symbol in
            session.execute(text('SELECT DISTINCT symbol FROM rates')).fetchall()[-1]
        ]

        if crypto_candidate in distinct_values:
            reply_message = f"""Successfully subscribed to {crypto_candidate}"""
            subscription = Subscription(user_id=user_id, crypto=crypto_candidate)
            session.add(subscription)
            session.commit()
        else:
            reply_message = f"Not supported subscription for {crypto_candidate}"
    else:
        reply_message = f"""Invalid argument"""

    await message.reply(reply_message)


def get_time_difference(sending_time) -> int:

    """
    Calculates the time difference to find the next desired sending time
    :return: number of seconds until next desired sending time
    """

    now = datetime.now().time()

    next_sending_time = datetime.combine(datetime.today(), sending_time).time()

    if now < next_sending_time:
        return (datetime.combine(datetime.today(), next_sending_time) - datetime.combine(datetime.today(), now)).seconds
    else:
        next_sending_time = (datetime.combine(datetime.today(), sending_time) + timedelta(days=1)).time()
        return (datetime.combine(datetime.today(), next_sending_time) - datetime.combine(datetime.today(), now)).seconds


def generate_prediction(crypto: str) -> str:

    """
    Sends the request to a model service and generates the message for prediction
    :return:
    """

    price = "Hey there" # TODO: Call the model here

    return f"Price for the ETH for the next date is {price}."

async def send_predictions(user_id: str, message_text: str):
    await bot.send_message(chat_id=user_id, text=message_text)

def get_users_subscriptions() -> List[Tuple[str]]:

    users_subscriptions = session.execute(
        text("SELECT user_id, crypto FROM subscriptions")
    ).fetchall()

    return users_subscriptions

@dp.message_handler(commands=["predict"])
async def get_on_demand_predicton(message: types.Message):

    users_subscriptions = get_users_subscriptions()
    for user_id, crypto in users_subscriptions:
        prediction_msg = generate_prediction(crypto)

        await send_predictions(user_id, prediction_msg)

async def schedule_task():

    while True:
        time_difference = get_time_difference(sending_time)
        print(f"time difference: {time_difference}")
        await asyncio.sleep(time_difference)

        user_subscriptions = get_users_subscriptions()
        for user_id, crypto in user_subscriptions:

            message = generate_prediction(crypto)
            await send_predictions(user_id, message)


@dp.message_handler(commands=['list'])
async def retrieve_subscriptions(message: types.Message):

    user_id = message.from_user.id

    subscriptions = [
        result_tpl[0]
        for result_tpl in session.query(Subscription.crypto).filter(
                    Subscription.user_id == str(user_id)).all()
    ]

    newline = "\n"
    reply_text = f"Your subscrptions: {newline.join([sub_crypt for sub_crypt in subscriptions])}" \
        if len(subscriptions) > 0 \
        else "You don't have any subscriptions"

    await message.reply(reply_text)


@dp.message_handler(commands=["unsubscribe"])
@dp.message_handler(lambda message: message.text.startswith("unsubscribe "))
async def unsubscribe(message: types.Message):

    # TODO: Create a mechanism later to unsubscribe from all of the subscriptions
    user_id = message.from_user.id

    crypto = message.text.split(' ')
    if len(crypto) > 1:
        crypto = crypto[1].upper()

        # No validation here needed
        subscription = session.query(Subscription).filter(
            Subscription.user_id == str(user_id),
            Subscription.crypto == str(crypto)
        ).first()

        session.delete(subscription)
        session.commit()

        await message.reply(f'Successfully unsubscribed from crypto {crypto}')


async def main():
    asyncio.create_task(schedule_task())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

