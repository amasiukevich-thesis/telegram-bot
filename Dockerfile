FROM python:3.8

COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip && pip install -r requirements.txt
WORKDIR /app

COPY tg_bot.py tg_bot.py
COPY db_stuff.py db_stuff.py

ENTRYPOINT ["python3", "tg_bot.py"]
