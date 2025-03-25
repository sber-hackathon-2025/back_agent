import argparse
import requests
from requests_pkcs12 import Pkcs12Adapter


# Функция для получения списка репозиториев
def get_repositories(base_url, workspace, session, headers):
    url = f"{base_url}/repositories/{workspace}"
    all_repositories = []

    while url:
        response = session.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            all_repositories.extend(data.get("values", []))
            url = data.get("next")  # Переход к следующей странице
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)
            break

    return all_repositories


# Основная функция
def main(base_url, username, password, p12_cert_path, p12_password, workspace):
    # Настройка сессии
    session = requests.Session()

    # Добавляем адаптер для работы с .p12 сертификатом
    session.mount(
        "https://",
        Pkcs12Adapter(
            pkcs12_filename=p12_cert_path,
            pkcs12_password=p12_password
        )
    )

    # Аутентификация Basic Auth
    session.auth = (username, password)

    # Заголовки запроса
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Получаем список репозиториев
    repositories = get_repositories(base_url, workspace, session, headers)
    for repo in repositories:
        repo_name = repo["name"]
        repo_slug = repo["slug"]
        clone_url = repo["links"]["clone"][0]["href"]  # URL для клонирования
        print(f"Репозиторий: {repo_name} (Slug: {repo_slug})")
        print(f"  URL для клонирования: {clone_url}")


# Обработка аргументов командной строки
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Скрипт для скачивания репозиториев из Bitbucket.")
    parser.add_argument("--url", required=True,
                        help="Базовый URL до Bitbucket API (например, https://api.bitbucket.org/2.0)")
    parser.add_argument("--username", required=True, help="Имя пользователя Bitbucket")
    parser.add_argument("--password", required=True, help="Пароль или App Password")
    parser.add_argument("--p12_cert_path", required=True, help="Путь к .p12 сертификату")
    parser.add_argument("--p12_password", required=True, help="Пароль от .p12 сертификата")
    parser.add_argument("--workspace", required=True, help="Имя рабочего пространства (workspace)")
    args = parser.parse_args()

    main(args.url, args.username, args.password, args.p12_cert_path, args.p12_password, args.workspace)
