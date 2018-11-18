# -*- coding: utf-8 -*-
import os
import threading
from Queue import PriorityQueue
import telebot
from Const import prod, num_worker_threads
from BotService import run_app
from DBMethods import DB
from MainMethods import reload_backup
from TaskMathodMap import TaskMethodMap


def worker():
    while True:
        if not queue.empty():
            TaskMethodMap.run_task(queue.get()[1], bot)
            queue.task_done()


port = int(os.environ.get('PORT', 5000)) if prod else 443
queue = PriorityQueue()

bot = telebot.TeleBot(DB.get_main_bot_token()) if prod else telebot.TeleBot("583637976:AAEFrQFiAaGuKwmoRV0N1MwU-ujRzmCxCAo")
bot.remove_webhook()
bot.set_webhook(url='https://jekafstbot.herokuapp.com/webhook') if prod \
    else bot.set_webhook(url='https://0c5dcaba.ngrok.io/webhook')

try:
    threading.Thread(name='th_flask', target=run_app(bot, queue).run, args=('0.0.0.0', port)).start()
except Exception:
    bot.send_message(45839899, 'Exception в main - не удалось запустить Flask')

reload_backup(bot, queue)
for i in range(num_worker_threads):
    threading.Thread(target=worker).start()
