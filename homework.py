import requests
import telegram
from exceptions import ExceptionErrors

import time
from http import HTTPStatus

import logging

import os
import sys

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=[
        logging.FileHandler('botlog.log', mode='w', encoding='UTF-8'),
        logging.StreamHandler(sys.stdout)])

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

message_list = []


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """
    Проверка наличия необходимых токенов при запуске
    остановка выполнения программы при отсутствии
    """

    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        logging.critical('Отсутствует обязательный токен/токены. '
                         'Бот остановлен!')
        sys.exit()


def send_message(bot, message):
    """Отправка сообщений"""

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Успешно отправил сообщение - {message}')

    except Exception as error:
        logging.error(error)
        raise ExceptionErrors(f'Бот не смог отправить сообщение '
                              f'- {message}! из-за ошибки {error}')


def get_api_answer(timestamp):
    """Запрос результатов проверки ДЗ"""

    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise ExceptionErrors(f'Сервер не отвечает {response.status_code}')

        response = response.json()
        return response

    except Exception as error:
        raise ExceptionErrors(f'Другие ошибки с доступом {error}')


def check_response(response):
    """
    Проверка, что полученный ответ, обладает
    надлежащей структурой и содержанием
    """

    if type(response) != dict:
        raise TypeError('Полученный ответ не является словарём!')
    elif 'homeworks' not in response:
        raise TypeError('В полученном словаре нет ключа [homeworks]!')
    elif type(response['homeworks']) != list:
        raise TypeError('В элементе [homeworks] не содержится списка!')
    elif not response['homeworks']:
        raise TypeError('В элементе homeworks пустой список!')
    else:
        homework = response['homeworks'][0]
        return homework


def parse_status(homework):
    """
    Формирование строки ответа для Телеграм,
    используя проверенный ответ API
    """

    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ExceptionErrors(f'Неизвестный статус проверки '
                              f'домашнего задани {homework["status"]}')

    if 'homework_name' not in homework:
        raise ExceptionErrors('Отсутствует название ДЗ!')

    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """"Этапы работы ПО телеграм-бота."""

    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message not in message_list:
                send_message(bot, message)
                message_list.append(message)
            else:
                logging.debug('Нет обновлений по ДЗ!')

        except (ExceptionErrors, TypeError) as error:
            message = f'{error}'
            logging.error(message)
            if message not in message_list:
                send_message(bot, message)
                message_list.append(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
