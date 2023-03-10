# -*- coding: utf-8 -*-
import re
import logging
import requests
from time import sleep
from httplib2 import Http
from bs4 import BeautifulSoup
from apiclient.discovery import build
from Const import obj_type_url_mapping
from oauth2client import file, client, tools
from SourceGameDataParcers import get_bonus_data_from_engine, get_task_data_from_engine, get_help_data_from_engine, \
    get_penalty_help_data_from_engine, get_lvl_name_comment_data_from_engine, get_lvl_timeout_data_from_engine, \
    get_sector_data_from_engine, check_empty_first_sector, get_lvl_ans_block_data_from_engine, \
    get_lvl_sectors_required_data_from_engine


class GoogleDocConnection(object):
    def __init__(self, spreadsheet_id):
        self.SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
        self.service = build('sheets', 'v4', http=self.get_creds().authorize(Http()))
        self.SPREADSHEET_ID = spreadsheet_id

    def get_creds(self):
        store = file.Storage('credentials.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('client_secret.json', self.SCOPES)
            creds = tools.run_flow(flow, store)
        return creds

    def get_levels_details(self, RANGE_NAME='LevelDetails'):
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=RANGE_NAME).execute()
        except Exception as e:
            if e.resp.status == 403:
                raise Exception('Нет доступа на просмотр гуглдока для jekafst@gmail.com')
            raise IndexError('%s sheet is not found in google doc' % RANGE_NAME)
        values = result.get('values', [])[1:]
        return values

    def get_helps(self, RANGE_NAME='Helps'):
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=RANGE_NAME).execute()
        except Exception as e:
            if e.resp.status == 403:
                raise Exception('Нет доступа на просмотр гуглдока для jekafst@gmail.com')
            raise IndexError('%s sheet is not found in google doc' % RANGE_NAME)
        values = result.get('values', [])[1:]
        return values

    def get_bonuses(self, RANGE_NAME='Bonuses'):
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=RANGE_NAME).execute()
        except Exception as e:
            if e.resp.status == 403:
                raise Exception('Нет доступа на просмотр гуглдока для jekafst@gmail.com')
            raise IndexError('%s sheet is not found in google doc' % RANGE_NAME)
        values = result.get('values', [])[1:]
        return values

    def get_sectors(self, RANGE_NAME='Sectors'):
        level_sectors_dict = dict()
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=RANGE_NAME).execute()
        except Exception as e:
            if e.resp.status == 403:
                raise Exception('Нет доступа на просмотр гуглдока для jekafst@gmail.com')
            raise IndexError('%s sheet is not found in google doc' % RANGE_NAME)
        values = result.get('values', [])[1:]
        for row in values:
            if row[2] not in level_sectors_dict.keys():
                level_sectors_dict[row[2]] = list()
            level_sectors_dict[row[2]].append(row)
        return level_sectors_dict

    def get_penalty_helps(self, RANGE_NAME='PenaltyHelps'):
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=RANGE_NAME).execute()
        except Exception as e:
            if e.resp.status == 403:
                raise Exception('Нет доступа на просмотр гуглдока для jekafst@gmail.com')
            raise IndexError('%s sheet is not found in google doc' % RANGE_NAME)
        values = result.get('values', [])[1:]
        return values

    def get_tasks(self, RANGE_NAME='Tasks'):
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=RANGE_NAME).execute()
        except Exception as e:
            if e.resp.status == 403:
                raise Exception('Нет доступа на просмотр гуглдока для jekafst@gmail.com')
            raise IndexError('%s sheet is not found in google doc' % RANGE_NAME)
        values = result.get('values', [])[1:]
        return values


class ENConnection(object):
    def __init__(self, domain, login, password, gameid):
        self.login_url = domain + '/Login.aspx'
        self.login = login
        self.password = password
        self.cookie = self.update_cookies()
        self.domain = domain
        self.gameid = gameid
        self.level_ids_dict = self.get_level_ids()

    def update_cookies(self):
        try:
            response = requests.post(self.login_url, data={'Login': self.login, 'Password': self.password}, headers={'Cookie': 'lang=ru'})
            cookie = response.request.headers['Cookie']
            return cookie
        except Exception:
            logging.exception("Can't get cookies by login URL")
            raise Exception("Can't login to EN")

    def get_level_ids(self):
        level_ids_dict = dict()
        url = self.domain + '/Administration/Games/LevelManager.aspx'
        params = {'gid': self.gameid}
        response = requests.get(url, params=params, headers={'Cookie': self.cookie})
        soup = BeautifulSoup(response.text, 'html.parser')
        td = soup.find(id='ddlCopyFrom')
        if not td:
            raise IndexError('Levels for game %s are not found' % self.gameid)
        for option_tag in td.contents:
            level_ids_dict[option_tag.text] = option_tag.attrs['value']
        return level_ids_dict

    def get_level_page(self, level_number):
        url = self.domain + obj_type_url_mapping['level']
        params = {'gid': self.gameid, 'level': level_number, 'swanswers': '1'}
        try:
            for i in range(2):
                response = requests.get(url, params=params, headers={'Cookie': self.cookie})
                if response.status_code != 200:
                    logging.log(logging.WARNING, "Failed to get level page %s" % level_number)
                    return False
                elif "your requests have been classified as robot's requests." in response.text.lower() and i == 0:
                    sleep(5)
                    self.cookie = self.update_cookies()
                    continue
                elif "your requests have been classified as robot's requests." in response.text.lower() and i > 0:
                    logging.log(logging.WARNING, "Failed to get level page %s" % level_number)
                    return False
                else:
                    return response.text
        except Exception:
            logging.exception("Failed to get level page %s" % level_number)
            return False

    def create_en_object(self, url, data, type, params):
        try:
            for i in range(2):
                response = requests.post(url, data=data, headers={'Cookie': self.cookie}, allow_redirects=False, params=params)
                if response.status_code != 302:
                    logging.log(logging.WARNING, "Failed to create %s. Data: %s" % (type, str(data)))
                    return False
                elif 'NotHumanRequest' in response.next.url and i == 0:
                    sleep(5)
                    self.cookie = self.update_cookies()
                    continue
                elif 'NotHumanRequest' in response.next.url and i > 0:
                    logging.log(logging.WARNING, "Failed to create %s. Data: %s" % (type, str(data)))
                    return False
                else:
                    return True
        except Exception:
            logging.exception("Failed to create %s. Data: %s" % (type, str(data)))
            return False

    def delete_en_object(self, params, type):
        url = self.domain + obj_type_url_mapping[type]
        try:
            for i in range(2):
                response = requests.get(url, params=params, headers={'Cookie': self.cookie})
                if response.status_code != 200:
                    logging.log(logging.WARNING, "Failed to delete %s. Data: %s" % (type, str(params)))
                    return False
                elif "your requests have been classified as robot's requests." in response.text.lower() and i == 0:
                    sleep(5)
                    self.cookie = self.update_cookies()
                    continue
                elif "your requests have been classified as robot's requests." in response.text.lower() and i > 0:
                    logging.log(logging.WARNING, "Failed to delete %s. Data: %s" % (type, str(params)))
                    return False
                else:
                    return True
        except Exception:
            logging.exception("Failed to delete %s. Data: %s" % (type, str(params)))
            return False

    def read_en_object(self, params, type):
        url = self.domain + obj_type_url_mapping[type]
        try:
            for i in range(2):
                response = requests.get(url, params=params, headers={'Cookie': self.cookie})
                if response.status_code != 200:
                    logging.log(logging.WARNING, "Failed to read %s. Data: %s" % (type, str(params)))
                    return False
                elif "your requests have been classified as robot's requests." in response.text.lower() and i == 0:
                    sleep(5)
                    self.cookie = self.update_cookies()
                    continue
                elif "your requests have been classified as robot's requests." in response.text.lower() and i > 0:
                    logging.log(logging.WARNING, "Failed to read %s. Data: %s" % (type, str(params)))
                    return False
                else:
                    return response
        except Exception:
            logging.exception("Failed to read %s. Data: %s" % (type, str(params)))
            return False


def make_help_data_and_url(row, domain, gameid, source_task_text=None, target_level_number=None):
    help_data = help_data_from_gdoc(row) if row else get_help_data_from_engine(source_task_text)
    help_url = domain + obj_type_url_mapping['help']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[5])}
    return help_data, help_url, params


def help_data_from_gdoc(row):
    help_data = {
        'ForMemberID': 0,
        'NewPromptTimeoutDays': int(row[1]) if row[1] else 0,
        'NewPromptTimeoutHours': int(row[2]) if row[2] else 0,
        'NewPromptTimeoutMinutes': int(row[3]) if row[3] else 0,
        'NewPromptTimeoutSeconds': int(row[4]) if row[4] else 0,
        'NewPrompt': row[0] if row[0] else ''
    }
    return help_data


# txt - award
# txtDelay - delay
# txtValid - time to answer
def make_bonus_data_and_url(row, domain, gameid, level_ids_dict, source_bonus_text=None, target_level_number=None):
    bonus_data = bonus_data_from_gdoc(row, level_ids_dict) if row else get_bonus_data_from_engine(source_bonus_text, level_ids_dict, target_level_number)
    bonus_url = domain + obj_type_url_mapping['bonus']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[17]), 'bonus': '0', 'action': 'save'}
    return bonus_data, bonus_url, params


def bonus_data_from_gdoc(row, level_ids_dict):
    bonus_data = {
        "ddlBonusFor": 0,
        "txtBonusName": row[0] if row[0] else '',
        "txtTask": row[1] if row[1] else '',
        "rbAllLevels-1": 0 if row[3] and row[3].lower() in ['true', 'y', 'yes'] else 1,
        "txtHours": int(row[5]) if row[5] else 0,
        "txtMinutes": int(row[6]) if row[6] else 0,
        "txtSeconds": int(row[7]) if row[7] else 0,
        "txtHelp": row[8] if row[8] else ''
    }
    # answers = re.findall(r'.+', row[2])
    answers = re.findall(r'[^/]+', row[2])
    for i, answer in enumerate(answers):
        bonus_data['answer_-%s' % str(i+1)] = answer.strip()
    # level_numbers = re.findall(r'.+', row[4])
    if bonus_data['rbAllLevels-1'] == 1:
        level_numbers = re.findall(r'[^/]+', row[4])
        for level_number in level_numbers:
            bonus_data['level_%s' % level_ids_dict[level_number.strip()]] = 'on'
    if row[9] or row[10] or row[11]:
        bonus_data['chkDelay'] = 'on'
        bonus_data['txtDelayHours'] = int(row[9]) if row[9] else 0
        bonus_data['txtDelayMinutes'] = int(row[10]) if row[10] else 0
        bonus_data['txtDelaySeconds'] = int(row[11]) if row[11] else 0
    if row[12] or row[13] or row[14]:
        bonus_data['chkRelativeLimit'] = 'on'
        bonus_data['txtValidHours'] = int(row[12]) if row[12] else 0
        bonus_data['txtValidMinutes'] = int(row[13]) if row[13] else 0
        bonus_data['txtValidSeconds'] = int(row[14]) if row[14] else 0
    if row[15] and row[16]:
        bonus_data['chkAbsoluteLimit'] = 'on'
        bonus_data['txtValidFrom'] = row[15] if row[15] else ''
        bonus_data['txtValidTo'] = row[16] if row[16] else ''
    return bonus_data


def make_sector_data_and_url(row, domain, gameid, source_sector_text=None, target_level_number=None, sector_id=None, is_answer=False):
    sector_data = sector_data_from_gdoc(row, is_answer) if row else get_sector_data_from_engine(source_sector_text, sector_id)
    sector_url = domain + obj_type_url_mapping['sector']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[2])}
    return sector_data, sector_url, params


def sector_data_from_gdoc(row, is_answer):
    sector_data = dict()
    # answers = re.findall(r'.+', row[1])
    answers = re.findall(r'[^/]+', row[1])
    for i, answer in enumerate(answers):
        sector_data['txtAnswer_%s' % str(i)] = answer.strip()
        sector_data['ddlAnswerFor_%s' % str(i)] = 0
    if is_answer and not row[0]:
        sector_data['saveanswers'] = 1
    else:
        sector_data['txtSectorName'] = row[0] if row[0] else ''
        sector_data['savesector'] = ''
    return sector_data


def make_del_answer_data_and_url(domain, gameid, answers_data, target_level_number, answers_block_id):
    del_answer_data = {
        'updateanswers': int(answers_block_id),
        'btnDelete.x': 96,
        'btnDelete.y': 8,
    }
    for answer_data in answers_data:
        del_answer_data['chkDeleteAnswer_%s' % answer_data['answer_id']] = int(answer_data['answer_id'])
        del_answer_data['txtAnswer_%s' % answer_data['answer_id']] = answer_data['answer_code']
        del_answer_data['ddlAnswerFor_%s' % answer_data['answer_id']] = 0
    del_answer_url = domain + obj_type_url_mapping['sector']
    params = {'gid': gameid, 'level': target_level_number}
    return del_answer_data, del_answer_url, params


# PenaltyComment - help description
# NewPrompt - penalty help text
# PromptTimeout - delay
# PenaltyPrompt - penalty time
def make_penalty_help_data_and_url(row, domain, gameid, source_task_text=None, target_level_number=None):
    pen_help_data = pen_help_data_from_gdoc(row) if row else get_penalty_help_data_from_engine(source_task_text)
    pen_help_url = domain + obj_type_url_mapping['pen_help']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[10]), 'penalty': '1'}
    return pen_help_data, pen_help_url, params


def pen_help_data_from_gdoc(row):
    pen_help_data = {
        'ForMemberID': 0,
        'txtPenaltyComment': row[0] if row[0] else '',
        'NewPrompt': row[1] if row[1] else '',
        'NewPromptTimeoutDays': int(row[2]) if row[2] else 0,
        'NewPromptTimeoutHours': int(row[3]) if row[3] else 0,
        'NewPromptTimeoutMinutes': int(row[4]) if row[4] else 0,
        'NewPromptTimeoutSeconds': int(row[5]) if row[5] else 0,
        'PenaltyPromptHours': int(row[7]) if row[7] else 0,
        'PenaltyPromptMinutes': int(row[8]) if row[8] else 0,
        'PenaltyPromptSeconds': int(row[9]) if row[9] else 0,

    }
    if 'false' not in row[6].lower():
        pen_help_data['chkRequestPenaltyConfirm'] = 'on'
    return pen_help_data


def make_task_data_and_url(row, domain, gameid, source_task_text=None, target_level_number=None):
    task_data = task_data_from_gdoc(row) if row else get_task_data_from_engine(source_task_text)
    task_url = domain + obj_type_url_mapping['task']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[2])}
    return task_data, task_url, params


def task_data_from_gdoc(row):
    task_data = {
        'forMemberID': 0,
        'inputTask': row[0] if row[0] else ''
    }
    # if 'false' not in row[1].lower():
    if row[1] and row[1].lower() in ['y', 'yes', 'true']:
        task_data['chkReplaceNlToBr'] = 'on'
    return task_data


def make_lvl_ans_block_data_and_url(row, domain, gameid, source_ans_block=None, target_level_number=None):
    lvl_ans_block_data = lvl_ans_block_data_from_gdoc(row) if row else get_lvl_ans_block_data_from_engine(source_ans_block)
    level_url = domain + obj_type_url_mapping['level']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[14])}
    return lvl_ans_block_data, level_url, params


def lvl_ans_block_data_from_gdoc(row):
    level_ans_block_data = {
        'txtAttemptsNumber': int(row[8]),
        'txtAttemptsPeriodHours': int(row[10]) if row[10] else 0,
        'txtAttemptsPeriodMinutes': int(row[11]) if row[11] else 0,
        'txtAttemptsPeriodSeconds': int(row[12]) if row[12] else 0,
        'action': 'upansblock',
        }
    if row[9]:
        if row[9] == 'player':
            level_ans_block_data['rbApplyForPlayer'] = 1
        if row[9] == 'team':
            level_ans_block_data['rbApplyForPlayer'] = 2
    return level_ans_block_data


def make_lvl_name_comment_data_and_url(row, domain, gameid, source_level_name_comment=None, target_level_number=None):
    lvl_name_comment_data = lvl_name_comment_data_from_gdoc(row) if row else get_lvl_name_comment_data_from_engine(source_level_name_comment)
    level_url = domain + obj_type_url_mapping['level_name']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[14])}
    return lvl_name_comment_data, level_url, params


def lvl_name_comment_data_from_gdoc(row):
    level_name_comment_data = {
        'txtLevelName': row[0] if row[0] else '',
        'txtLevelComment': row[1] if row[1] else '',
    }
    return level_name_comment_data


def make_lvl_timeout_data_and_url(row, domain, gameid, source_level_timeout=None, target_level_number=None):
    lvl_timeout_data = lvl_timeout_data_from_gdoc(row) if row else get_lvl_timeout_data_from_engine(source_level_timeout)
    level_url = domain + obj_type_url_mapping['level']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[14])}
    return lvl_timeout_data, level_url, params


def lvl_timeout_data_from_gdoc(row):
    level_timeout_data = {
        'txtApHours': int(row[2]) if row[2] else 0,
        'txtApMinutes': int(row[3]) if row[3] else 0,
        'txtApSeconds': int(row[4]) if row[4] else 0,
        'updateautopass': '',
    }
    if row[5] or row[6] or row[7]:
        level_timeout_data['chkTimeoutPenalty'] = 'on'
        level_timeout_data['txtApPenaltyHours'] = int(row[5]) if row[5] else 0
        level_timeout_data['txtApPenaltyMinutes'] = int(row[6]) if row[6] else 0
        level_timeout_data['txtApPenaltySeconds'] = int(row[7]) if row[7] else 0

    return level_timeout_data


def make_lvl_sectors_required_data_and_url(row, domain, gameid, source_level_sectors_required=None, target_level_number=None):
    lvl_sectors_required_data = lvl_sectors_required_data_from_gdoc(row) if row else get_lvl_sectors_required_data_from_engine(source_level_sectors_required)
    level_sectors_required_url = domain + obj_type_url_mapping['level']
    params = {'gid': gameid, 'level': target_level_number if target_level_number else str(row[14]), 'sw': 'edlvlsectsett'}
    return lvl_sectors_required_data, level_sectors_required_url, params


def lvl_sectors_required_data_from_gdoc(row):
    lvl_sectors_required_data = {
        'rbSectorCompleteType': 2,
        'txtRequiredSectorsCount': int(row[13]),
        'action': 'upsecsett',
    }
    return lvl_sectors_required_data


def parse_level_page(level_page, level=None, transfer=False):
    sectors, helps, bonuses, pen_helps, task_ids = __parse_level_page_transfer(level_page) if transfer else __parse_level_page_cleanup(level, level_page)
    return sectors, helps, bonuses, pen_helps, task_ids


def __parse_level_page_cleanup(level, level_page, sectors=list(), helps=list(), bonuses=list(), pen_helps=list(), task_ids=None):
    if level['sectors'] and level['sectors'].lower() == 'да':
        sectors = re.findall(r'divSectorManage_(\d+)\'', level_page)
    if level['helps']:
        help_ids = re.findall(r'prid=(\d+)\'', level_page)
        helps = help_ids if level['helps'] == 'все' else get_exact_ids(re.findall(r'[^/]+', level['helps']), help_ids)
    if level['bonuses']:
        bonus_ids = re.findall(r'bonus=(\d+)', level_page)
        bonuses = bonus_ids if level['bonuses'] == 'все' else get_exact_ids(re.findall(r'[^/]+', level['bonuses']), bonus_ids)
    if level['pen_helps']:
        pen_helps_ids = re.findall(r'prid=(\d+)&penalty', level_page)
        pen_helps = pen_helps_ids if level['pen_helps'] == 'все' else get_exact_ids(re.findall(r'[^/]+', level['pen_helps']), pen_helps_ids)
    return sectors, helps, bonuses, pen_helps, task_ids


def __parse_level_page_transfer(level_page):
    sectors = re.findall(r'divSectorManage_(\d+)\'', level_page)
    helps = re.findall(r'prid=(\d+)\'', level_page)
    bonuses = re.findall(r'bonus=(\d+)', level_page)
    pen_helps = re.findall(r'prid=(\d+)&penalty', level_page)
    task_ids = re.findall(r'tid=(\d+)', level_page)
    return sectors, helps, bonuses, pen_helps, task_ids


def clean_empty_first_sector(en_connection, level):
    level_page = en_connection.get_level_page(level)
    if not level_page:
        return False
    sector_id_to_clean = check_empty_first_sector(level_page)
    if sector_id_to_clean:
        params = {
            'gid': en_connection.gameid,
            'level': level,
            'delsector': sector_id_to_clean,
            'swanswers': 1
        }
        result = en_connection.delete_en_object(params, 'sector')
    else:
        result = True
    return result


def get_exact_ids(exact_ids, all_ids):
    ids = list()
    for id in exact_ids:
        ids.append(all_ids[int(id.strip())-1])
    return ids
