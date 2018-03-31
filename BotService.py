# -*- coding: utf-8 -*-
import flask
import re
import telebot
from flask import Flask
from Const import helptext
from DBMethods import DB
from MainClasses import Task, Validations
from TextConvertingMethods import find_coords


def run_app(bot, main_vars):
    app = Flask(__name__)

    #Process webhook calls
    @app.route('/webhook', methods=['GET', 'POST'])
    def webhook():
        if flask.request.headers.get('content-type') == 'application/json':
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            flask.abort(403)

    @bot.message_handler(commands=['ask_for_permission'])
    def ask_for_permission(message):
        main_chat_ids, _ = DB.get_allowed_chat_ids()
        if message.chat.id in main_chat_ids:
            bot.send_message(message.chat.id, 'Данный чат уже разрешен для работы с ботом')
            return
        text = '<b>%s</b> запрашивает разрешение на работу с ботом из чата "%s"\r\nchat_id: %s' % \
               (str(message.from_user.username.encode('utf-8')), str(message.chat.title.encode('utf-8')),
                str(message.chat.id))
        bot.send_message(45839899, text, parse_mode='HTML')

    @bot.message_handler(commands=['join'])
    def join_session(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed \
                and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_join_possible(message.chat.id, bot, message.from_user.id, message.message_id, add_chat_ids):
            join_task = Task(message.chat.id, 'join', message_id=message.message_id, user_id=message.from_user.id)
            main_vars.task_queue.append(join_task)

    @bot.message_handler(commands=['reset_join'])
    def reset_join(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed \
                and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_reset_join_possible(message.chat.id, bot, message.from_user.id, message.message_id, add_chat_ids):
            reset_join_task = Task(message.chat.id, 'reset_join', message_id=message.message_id, user_id=message.from_user.id)
            main_vars.task_queue.append(reset_join_task)

    @bot.message_handler(commands=['add'])
    def add_chat_to_allowed(message):
        if message.chat.id != 45839899:
            bot.send_message(message.chat.id, 'Данная команда не доступна из этого чата')
            return
        chat_id = int(re.search(r'[-\d]+', str(message.text.encode('utf-8'))).group(0))
        DB.insert_main_chat_id(chat_id)
        main_chat_ids, _ = DB.get_allowed_chat_ids()
        if chat_id in main_chat_ids:
            bot.send_message(chat_id, 'Этот чат добавлен в список разрешенных для работы с ботом')
        else:
            bot.send_message(chat_id, 'Этот чат не добавлен в список разрешенных для работы с ботом'
                                      '\r\nДля повторного запроса введите /ask_for_permission')

    @bot.message_handler(commands=['start'])
    def start(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and not Validations.check_from_add_chat(message.chat.id, add_chat_ids):
            start_task = Task(message.chat.id, 'start')
            main_vars.task_queue.append(start_task)

    @bot.message_handler(commands=['help'])
    def help(message):
        allowed, _, _ = Validations.check_permission(message.chat.id, bot)
        if allowed:
            bot.send_message(message.chat.id, helptext)

    @bot.message_handler(commands=['start_session'])
    def start_session(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            start_session_task = Task(message.chat.id, 'start_session', session_id=message.chat.id)
            main_vars.task_queue.append(start_session_task)

    @bot.message_handler(commands=['stop_session'])
    def stop_session(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            stop_session_task = Task(message.chat.id, 'stop_session', session_id=message.chat.id)
            main_vars.task_queue.append(stop_session_task)

    @bot.message_handler(commands=['config'])
    def config(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            config_task = Task(message.chat.id, 'config', session_id=message.chat.id)
            main_vars.task_queue.append(config_task)

    @bot.message_handler(commands=['login'])
    def save_login(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            new_login = re.findall(r'/login\s*(.+)', str(message.text.encode('utf-8')))[0]
            set_login_task = Task(message.chat.id, 'login', session_id=message.chat.id, new_login=new_login)
            main_vars.task_queue.append(set_login_task)

    @bot.message_handler(commands=['password'])
    def save_password(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            new_password = re.findall(r'/password\s*(.+)', str(message.text.encode('utf-8')))[0]
            set_password_task = Task(message.chat.id, 'password', session_id=message.chat.id, new_password=new_password)
            main_vars.task_queue.append(set_password_task)

    @bot.message_handler(commands=['domain'])
    def save_en_domain(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            new_domain = re.findall(r'/domain\s*(.+)', str(message.text.encode('utf-8')))[0]
            set_domain_task = Task(message.chat.id, 'domain', session_id=message.chat.id, new_domain=new_domain)
            main_vars.task_queue.append(set_domain_task)

    @bot.message_handler(commands=['gameid'])
    def save_game_id(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            new_game_id = re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)
            set_game_id_task = Task(message.chat.id, 'game_id', session_id=message.chat.id, new_game_id=new_game_id)
            main_vars.task_queue.append(set_game_id_task)

    @bot.message_handler(commands=['login_to_en'])
    def login_to_en(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            login_to_en_task = Task(message.chat.id, 'login_to_en', session_id=message.chat.id)
            main_vars.task_queue.append(login_to_en_task)

    @bot.message_handler(commands=['task'])
    def send_task(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_task_task = Task(message.chat.id, 'send_task', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_task_task)

    @bot.message_handler(commands=['task_images'])
    def send_task_images(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            send_task_images_task = Task(message.chat.id, 'task_images', session=session)
            main_vars.task_queue.append(send_task_images_task)

    @bot.message_handler(commands=['sectors'])
    def send_all_sectors(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_all_sectors_task = Task(message.chat.id, 'send_sectors', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_all_sectors_task)

    @bot.message_handler(commands=['hints'])
    def send_all_helps(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_all_helps_task = Task(message.chat.id, 'send_helps', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_all_helps_task)

    @bot.message_handler(commands=['last_hint'])
    def send_last_help(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_last_help_task = Task(message.chat.id, 'send_last_help', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_last_help_task)

    @bot.message_handler(commands=['bonuses'])
    def send_all_bonuses(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_all_bonuses_task = Task(message.chat.id, 'send_bonuses', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_all_bonuses_task)

    @bot.message_handler(commands=['unclosed_bonuses'])
    def send_unclosed_bonuses(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_unclosed_bonuses_task = Task(message.chat.id, 'unclosed_bonuses', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_unclosed_bonuses_task)

    @bot.message_handler(commands=['messages'])
    def send_auth_messages(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            storm_level = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0)) if \
                re.findall(r'[\d]+', str(message.text.encode('utf-8'))) else None
            send_auth_messages_task = Task(message.chat.id, 'send_messages', session=session, storm_level_number=storm_level)
            main_vars.task_queue.append(send_auth_messages_task)

    @bot.message_handler(commands=['start_updater'])
    def start_updater(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            start_updater_task = Task(message.chat.id, 'start_updater', main_vars=main_vars)
            main_vars.task_queue.append(start_updater_task)

    @bot.message_handler(commands=['delay'])
    def set_updater_delay(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            new_delay = int(re.search(r'[\d]+', str(message.text.encode('utf-8'))).group(0))
            set_delay_task = Task(message.chat.id, 'delay', session=session, new_delay=new_delay)
            main_vars.task_queue.append(set_delay_task)

    @bot.message_handler(commands=['stop_updater'])
    def stop_updater(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            stop_updater_task = Task(message.chat.id, 'stop_updater', session=session)
            main_vars.task_queue.append(stop_updater_task)

    @bot.message_handler(commands=['set_channel_name'])
    def set_channel_name(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            new_channel_name = re.findall(r'/set_channel_name\s*(.+)', str(message.text.encode('utf-8')))[0]
            set_channel_name_task = Task(message.chat.id, 'channel_name', session=session, new_channel_name=new_channel_name)
            main_vars.task_queue.append(set_channel_name_task)

    @bot.message_handler(commands=['start_channel'])
    def start_channel(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            start_channel_task = Task(message.chat.id, 'start_channel', session=session)
            main_vars.task_queue.append(start_channel_task)

    @bot.message_handler(commands=['stop_channel'])
    def stop_channel(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            stop_channel_task = Task(message.chat.id, 'stop_channel', session=session)
            main_vars.task_queue.append(stop_channel_task)

    @bot.message_handler(commands=['codes_on'])
    def enable_codes(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            enable_codes_task = Task(message.chat.id, 'codes_on', session=session)
            main_vars.task_queue.append(enable_codes_task)

    @bot.message_handler(commands=['codes_off'])
    def disable_codes(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot) \
                and Validations.check_from_main_chat(message.chat.id, bot, main_chat_ids, message.message_id):

            session = Task.get_session(message.chat.id, main_chat_ids)
            disable_codes_task = Task(message.chat.id, 'codes_off', session=session)
            main_vars.task_queue.append(disable_codes_task)

    @bot.message_handler(commands=['add_tag'])
    def add_tag(message):
        if message.chat.id != 45839899:
            bot.send_message(message.chat.id, 'Данная команда не доступна из этого чата')
            return
        tag_to_add = re.findall(r'/add_tag\s*(.+)', str(message.text.encode('utf-8')))[0]
        DB.insert_tag_in_tags_list(tag_to_add)
        if tag_to_add in DB.get_tags_list():
            bot.send_message(message.chat.id, 'Тег успешно добавлен в обработчик')
        else:
            bot.send_message(message.chat.id, 'Тег не добавлен в обработчикб повторите попытку')

    @bot.message_handler(commands=['send_ll'])
    def send_live_location(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            coords = re.findall(r'\d\d\.\d{4,7},\s{0,3}\d\d\.\d{4,7}|'
                                r'\d\d\.\d{4,7}\s{0,3}\d\d\.\d{4,7}|'
                                r'\d\d\.\d{4,7}\r\n\d\d\.\d{4,7}|'
                                r'\d\d\.\d{4,7},\r\n\d\d\.\d{4,7}', message.text)
            seconds = re.findall(r'\ss(\d+)', str(message.text.encode('utf-8')))
            duration = int(seconds[0]) if seconds else None
            send_live_location_task = Task(message.chat.id, 'live_location', session=session, coords=coords, duration=duration)
            main_vars.task_queue.append(send_live_location_task)

    @bot.message_handler(commands=['stop_ll'])
    def stop_live_location(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            point_number = re.search(r'\s(\d{1,2})\s', str(message.text.encode('utf-8')))
            point = int(point_number.group(0)) if point_number else None
            stop_live_location_task = Task(message.chat.id, 'stop_live_location', session=session, point=point)
            main_vars.task_queue.append(stop_live_location_task)

    @bot.message_handler(commands=['edit_ll'])
    def edit_live_location(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            coords = re.findall(r'\d\d\.\d{4,7},\s{0,3}\d\d\.\d{4,7}|'
                                r'\d\d\.\d{4,7}\s{0,3}\d\d\.\d{4,7}|'
                                r'\d\d\.\d{4,7}\r\n\d\d\.\d{4,7}|'
                                r'\d\d\.\d{4,7},\r\n\d\d\.\d{4,7}', message.text)
            point_number = re.search(r'\s(\d{1,2})\s', str(message.text.encode('utf-8')))
            point = int(point_number.group(0)) if point_number else None
            edit_live_location_task = Task(message.chat.id, 'edit_live_location', session=session, point=point, coords=coords)
            main_vars.task_queue.append(edit_live_location_task)

    @bot.message_handler(commands=['add_points_ll'])
    def add_points_live_location(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            points_dict = dict()
            points = re.findall(r'\d{1,2}\s*-\s*\d\d\.\d{4,7},\s{,3}\d\d\.\d{4,7}|'
                                r'\d{1,2}\s*-\s*\d\d\.\d{4,7}\s{1,3}\d\d\.\d{4,7}', str(message.text.encode('utf-8')))
            for point in points:
                i = int(re.findall(r'(\d{1,2})\s*-', point)[0])
                points_dict[i] = re.findall(r'\d\d\.\d{4,7},\s{,3}\d\d\.\d{4,7}|'
                                            r'\d\d\.\d{4,7}\s{1,3}\d\d\.\d{4,7}', point)[0]
            if not points_dict:
                bot.send_message(message.chat.id, 'Нет точек, для отправки live_locations. Верный формат:\n'
                                                  '1 - корды\n2 - корды\n...\nn - корды')
            seconds = re.findall(r'\ss(\d+)', str(message.text.encode('utf-8')))
            duration = int(seconds[0]) if seconds else None
            add_points_ll_task = Task(message.chat.id, 'add_points_ll', session=session, points_dict=points_dict, duration=duration)
            main_vars.task_queue.append(add_points_ll_task)

    @bot.message_handler(regexp='!\s*(.+)')
    def main_code_processor(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            if message.text[0] == '!':
                code = re.findall(r'!\s*(.+)', str(message.text.lower().encode('utf-8')))[0]
                send_code_main_task = Task(message.chat.id, 'send_code_main', session=session, code=code, message_id=message.message_id)
                main_vars.task_queue.append(send_code_main_task)

    @bot.message_handler(regexp='\?\s*(.+)')
    def bonus_code_processor(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed and Validations.check_session_available(message.chat.id, bot):

            session = Task.get_session(message.chat.id, main_chat_ids)
            if message.text[0] == '?':
                code = re.findall(r'\?\s*(.+)', str(message.text.lower().encode('utf-8')))[0]
                send_code_bonus_task = Task(message.chat.id, 'send_code_bonus', session=session, code=code, message_id=message.message_id)
                main_vars.task_queue.append(send_code_bonus_task)

    @bot.message_handler(regexp='\d\d\.\d{4,7},\s{0,3}\d\d\.\d{4,7}|'
                                '\d\d\.\d{4,7}\s{0,3}\d\d\.\d{4,7}|'
                                '\d\d\.\d{4,7}\r\n\d\d\.\d{4,7}|'
                                '\d\d\.\d{4,7},\r\n\d\d\.\d{4,7}')
    def coords_processor(message):
        allowed, main_chat_ids, add_chat_ids = Validations.check_permission(message.chat.id, bot)
        if allowed:
            coords = find_coords(message.text)
            if coords:
                send_coords_task = Task(message.chat.id, 'send_code_bonus', coords=coords)
                main_vars.task_queue.append(send_coords_task)

    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot.remove_webhook()

    # Set webhook
    # bot.set_webhook(url='https://powerful-shelf-32284.herokuapp.com/webhook')
    bot.set_webhook(url='https://b96f5a9d.ngrok.io/webhook')

    @app.route("/", methods=['GET', 'POST'])
    def hello():
        return 'Hello world!'

    @app.route("/develop/DB/connectorcheck", methods=['GET', 'POST'])
    def db_conn_check():
        list_of_tags = 'List of tags:'
        for tag in DB.get_tags_list():
            list_of_tags += '<br>' + tag
        return list_of_tags

    return app
