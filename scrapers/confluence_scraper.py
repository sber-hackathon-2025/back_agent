import argparse
import os
from requests_pkcs12 import get

# Путь для сохранения результатов
output_dir = "confluence_pages"
os.makedirs(output_dir, exist_ok=True)

# Функция для получения всех страниц в пространстве
def get_pages_in_space(space_key, base_url, username, password):
    url = f"{base_url}content"
    params = {
        "spaceKey": space_key,
        "type": "page",  # Только страницы
        "start": 0,
        "limit": 100,  # Максимальное количество страниц за один запрос
        "expand": "body.storage"  # Получаем содержимое страницы в формате HTML
    }

    all_pages = []

    while True:
        response = get(url, params=params, auth=(username, password), pkcs12_filename=p12_cert_path,
                       pkcs12_password=p12_password, verify=False)

        if response.status_code == 200:
            data = response.json()
            pages = data.get("results", [])
            all_pages.extend(pages)

            # Проверяем, есть ли еще страницы (пагинация)
            if len(pages) < params["limit"]:
                break

            # Переходим к следующей странице
            params["start"] += params["limit"]
        else:
            print(f"Ошибка при получении страниц для пространства {space_key}: {response.status_code}")
            print(response.text)
            break

    return all_pages


# Функция для сохранения страниц в структурированном виде
def save_page_to_file(page, space_key):
    page_id = page["id"]
    page_title = page["title"].replace("/", "_").replace("\\", "_")  # Заменяем недопустимые символы
    page_content = page["body"]["storage"]["value"]

    # Создаем поддиректорию для пространства
    space_dir = os.path.join(output_dir, space_key)
    os.makedirs(space_dir, exist_ok=True)

    # Сохраняем страницу в файл
    file_name = f"{page_title}_{page_id}.html"
    file_path = os.path.join(space_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(page_content)

    print(f"Страница '{page_title}' сохранена в файл {file_path}")


# Основная функция
def download_confluence_pages(base_url, username, password, p12_cert_path, p12_password):
    # Получаем список пространств
    spaces_url = f"{base_url}space"

    params = {
        "limit": 10,  # Максимальное количество пространств за один запрос
        "start": 0
    }

    all_spaces = []

    while True:
        response = get(spaces_url, params=params, auth=(username, password), pkcs12_filename=p12_cert_path,
                       pkcs12_password=p12_password, verify=False)

        if response.status_code == 200:
            data = response.json()
            spaces = data.get("results", [])
            all_spaces.extend(spaces)

            # Проверяем, есть ли еще пространства (пагинация)
            if len(spaces) < params["limit"]:
                break

            # Переходим к следующей странице
            params["start"] += params["limit"]
        else:
            print(f"Ошибка при получении пространств: {response.status_code}")
            print(response.text)
            break

    # Для каждого пространства получаем страницы
    for space in all_spaces:
        space_key = space["key"]
        space_name = space["name"]
        print(f"Обработка пространства: {space_name} ({space_key})")

        pages = get_pages_in_space(space_key, base_url, username, password)
        for page in pages:
            save_page_to_file(page, space_key)


# Вызов основной функции
if __name__ == '__main__':
    # Базовые параметры
    base_url = "https://sberworks.ru/wiki/rest/api/"

    # Настройки Confluence
    space_key = "ABRAU"  # Ключ пространства Confluence

    # Путь к .p12 сертификату и пароль от него
    p12_cert_path = ""
    p12_password = ""

    parser = argparse.ArgumentParser(description="Скрипт для скачивания Confluence.")
    parser.add_argument("--url", required=True,
                        help="Базовый URL до Confluence API (например, https://api.bitbucket.org/2.0)")
    parser.add_argument("--username", required=True, help="Имя пользователя ")
    parser.add_argument("--password", required=True, help="Пароль ")
    parser.add_argument("--p12_cert_path", required=True, help="Путь к .p12 сертификату")
    parser.add_argument("--p12_password", required=True, help="Пароль от .p12 сертификата")
    parser.add_argument("--workspace", required=True, help="Имя рабочего пространства (workspace)")
    args = parser.parse_args()

    download_confluence_pages(base_url, args.username, args.password, args.p12_cert_path, args.p12_password)
