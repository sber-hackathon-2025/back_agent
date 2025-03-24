import requests, json
from requests_pkcs12 import get

# Базовые параметры
base_url = "https://sberworks.ru/wiki/rest/api/"
<<<<<<< HEAD
username = "tuz_sbt_ci_hack"  # Ваш email в Atlassian
password = "0EfW8PSD&vhzF1"  # Ваш PAT
=======
username = ""
password = ""
>>>>>>> 17781b1b4f47da9787af068ed39ecf9a9f245e72

# Настройки Confluence
space_key = "ABRAU"  # Ключ пространства Confluence


# Путь к .p12 сертификату и пароль от него
p12_cert_path = "/Users/16690145/work/hahaton/hakaton2025.p12"
p12_password = "hakaton2025"

# Функция для загрузки страниц из пространства
def download_space_content(base_url, space_key, username, password, p12_cert_path, p12_password):

    # Заголовки запроса
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # URL для получения содержимого пространства
    url = f"{base_url}content?spaceKey={space_key}&expand=body.storage"

    try:
        # Выполняем GET-запрос

        print(url)
        response = get(url, auth=(username, password), pkcs12_filename=p12_cert_path,
                pkcs12_password=p12_password, headers=headers, verify=False)

        if response.status_code == 200:
            print("Содержимое успешно получено:")
            data = response.json()

            # Сохраняем содержимое в файл
            with open("confluence_space_content.json", "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            print("Содержимое сохранено в файл confluence_space_content.json")
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Произошла ошибка: {e}")

# Вызов функции
download_space_content(base_url, space_key, username, password, p12_cert_path, p12_password)