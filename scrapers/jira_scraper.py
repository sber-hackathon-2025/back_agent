import argparse
import requests
from requests_pkcs12 import Pkcs12Adapter
from urllib.parse import urljoin
import os
import json


def main(url, username, password, p12_cert_path, p12_password, workspace):
    """
    Основная функция для выполнения скрапинга Jira и сохранения результатов в файлы.

    :param url: Базовый URL Jira
    :param username: Имя пользователя для аутентификации
    :param password: Пароль пользователя
    :param p12_cert_path: Путь к файлу сертификата P12
    :param p12_password: Пароль для сертификата P12
    :param workspace: Рабочее пространство (например, проект или доска)
    """
    # Создаем сессию для выполнения запросов
    session = requests.Session()

    # Добавляем адаптер для работы с сертификатом P12
    session.mount('https://', Pkcs12Adapter(pkcs12_filename=p12_cert_path, pkcs12_password=p12_password))

    # Аутентификация через Basic Auth
    session.auth = (username, password)

    # Формируем URL для API Jira
    api_url = urljoin(url, f"/rest/api/3/search")

    # Параметры запроса (фильтр по рабочему пространству)
    params = {
        "jql": f"project={workspace}",
        "maxResults": 50,  # Количество результатов на странице
        "startAt": 0,  # Начало пагинации
    }

    try:
        # Выполняем GET-запрос к API Jira
        response = session.get(api_url, params=params)

        # Проверяем статус ответа
        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])

            # Создаем директорию для сохранения файлов, если она не существует
            output_dir = "jira_issues"
            os.makedirs(output_dir, exist_ok=True)

            print(f"Сохранение данных в директорию: {output_dir}")

            for issue in issues:
                key = issue.get("key")
                summary = issue.get("fields", {}).get("summary")

                # Формируем имя файла
                file_name = f"{key}.json"
                file_path = os.path.join(output_dir, file_name)

                # Сохраняем данные в файл
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(issue, f, ensure_ascii=False, indent=4)

                print(f"Сохранен файл: {file_path}, Summary: {summary}")

        else:
            print(f"Ошибка при выполнении запроса: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(description="Скрипт для скрапинга данных из Jira и сохранения их в файлы.")
    parser.add_argument("--url", required=True, help="Базовый URL Jira (например, https://your-domain.atlassian.net)")
    parser.add_argument("--username", required=True, help="Имя пользователя Jira")
    parser.add_argument("--password", required=True, help="Пароль пользователя Jira")
    parser.add_argument("--p12-cert-path", required=True, help="Путь к файлу сертификата P12")
    parser.add_argument("--p12-password", required=True, help="Пароль для сертификата P12")
    parser.add_argument("--workspace", required=True, help="Рабочее пространство (например, проект)")

    # Парсинг аргументов
    args = parser.parse_args()

    # Вызов основной функции
    main(args.url, args.username, args.password, args.p12_cert_path, args.p12_password, args.workspace)