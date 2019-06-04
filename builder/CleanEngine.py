# -*- coding: utf-8 -*-
import re
import logging
from time import sleep
from DBMethods import DB
from SourceGameDataParcers import get_answers_data
from GameDetailsBuilderMethods import GoogleDocConnection, ENConnection, parse_level_page, make_del_answer_data_and_url


class Buttons:
    BUTTON_CLEAN_ENGINE = "Очистить движок"


class CleanEngine(object):
    def get_applications(self):
        return [
            {"name": Buttons.BUTTON_CLEAN_ENGINE, "fn": self.clean_engine},
        ]

    def __get_clean_engine_data(self, request):
        login = request.get('login').strip()
        password = request.get('password').strip()
        domain = request.get('domain').strip()
        if 'http://' not in domain:
            domain = 'http://' + domain
        game_id = request.get('game_id').strip()
        levels = request.get('levels')
        return login, password, domain, game_id, levels

    def __get_cleanup_level_rows(self, en_connection, levels):
        if len(levels) == 1 and levels[0]['level_number'] == 'all':
            level_rows = [[levels[0]['sectors'], levels[0]['helps'], levels[0]['bonuses'], levels[0]['pen_helps'], level_number] for level_number in en_connection.level_ids_dict.keys()]
        else:
            level_rows = [[level['sectors'], level['helps'], level['bonuses'], level['pen_helps'], level['level_number']] for level in levels]
        return level_rows

    def clean_engine(self, request):
        login, password, domain, game_id, levels = self.__get_clean_engine_data(request.json)
        yield 'Очистка движка запущена'
        if 'demo' in domain or game_id in DB.get_gameids_for_builder_list():
            en_connection = ENConnection(domain, login, password, game_id)

            level_rows = self.__get_cleanup_level_rows(en_connection, levels)
            for i, level_row in level_rows:
                logging.log(logging.INFO, "Cleanup of level %s started" % level_row[4])
                yield 'Очистка данных из уровня %s запущена' % level_row[4]

                level_page = en_connection.get_level_page(level_row[4])
                sectors_to_del, helps_to_del, bonuses_to_del, pen_helps_to_del, _ = parse_level_page(level_row, level_page)

                if helps_to_del:
                    logging.log(logging.INFO, "Cleanup of helps for level %s started" % level_row[4])
                    for help_to_del in helps_to_del:
                        params = {
                            'gid': game_id,
                            'action': 'PromptDelete',
                            'prid': help_to_del,
                            'level': level_row[4]
                        }
                        en_connection.delete_en_object(params, 'help')
                    logging.log(logging.INFO, "Cleanup of helps for level %s finished" % level_row[4])

                if bonuses_to_del:
                    logging.log(logging.INFO, "Cleanup of bonuses for level %s started" % level_row[4])
                    for bonus_to_del in bonuses_to_del:
                        params = {
                            'gid': game_id,
                            'action': 'delete',
                            'bonus': bonus_to_del,
                            'level': level_row[4]
                        }
                        en_connection.delete_en_object(params, 'bonus')
                    logging.log(logging.INFO, "Cleanup of bonuses for level %s finished" % level_row[4])

                if pen_helps_to_del:
                    logging.log(logging.INFO, "Cleanup of penalty helps for level %s started" % level_row[4])
                    for pen_help_to_del in pen_helps_to_del:
                        params = {
                            'gid': game_id,
                            'action': 'PromptDelete',
                            'prid': pen_help_to_del,
                            'level': level_row[4],
                            'penalty': '1'
                        }
                        en_connection.delete_en_object(params, 'pen_help')
                    logging.log(logging.INFO, "Cleanup of penalty helps for level %s finished" % level_row[4])

                if level_row[0].lower() in ['y', 'yes', 'true']:
                    logging.log(logging.INFO, "Cleanup of sectors for level %s started" % level_row[4])
                    if sectors_to_del:
                        for i, sector_to_del in enumerate(sectors_to_del):
                            if i % 30 == 0:
                                sleep(5)
                            params = {
                                'gid': en_connection.gameid,
                                'level': level_row[4],
                                'delsector': sector_to_del,
                                'swanswers': 1
                            }
                            en_connection.delete_en_object(params, 'sector')
                        logging.log(logging.INFO, "Cleanup of sectors for level %s finished" % level_row[4])
                    else:
                        answers = re.findall('divAnswersView_(\d+)', level_page)
                        if answers:
                            read_params = {
                                'gid': en_connection.gameid,
                                'level': level_row[4],
                                'editanswers': answers[0],
                                'swanswers': '1'
                            }
                            response = en_connection.read_en_object(read_params, 'sector')
                            if response:
                                answers_data = get_answers_data(response.text, answers[0])
                                del_answer_data, del_answer_url, params = make_del_answer_data_and_url(en_connection.domain, en_connection.gameid, answers_data, level_row[4], answers[0])
                                en_connection.create_en_object(del_answer_url, del_answer_data, 'sector', params)
                        logging.log(logging.INFO, "Cleanup of sectors for level %s finished" % level_row[4])

                yield 'Очистка данных из уровня %s выполнена' % level_row[4]
                logging.log(logging.INFO, "Cleanup of level %s finished" % level_row[4])
            yield 'Проверьте правильность удаления данных из движка.'
        else:
            yield 'Очистка данных для данной игры не разрешено. Напишите @JekaFST в телеграмме для получения разрешения'