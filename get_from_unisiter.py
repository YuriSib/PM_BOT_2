import requests
import re
import time
from random import randint, choice
from bs4 import BeautifulSoup


def get_rand_proxy_list():
    token = 'd294971f4d-cc8c7cb03e-026fe32c60'

    url = f"https://px6.me/api/{token}/getproxy"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        proxy_data = response.json().get("list", {})

        if not proxy_data:
            raise ValueError("Пустой список прокси")

        item = choice(list(proxy_data.values()))

        proxy_auth = f'{item["user"]}:{item["pass"]}@{item["ip"]}:{item["port"]}'

        return {
            "http": f"http://{proxy_auth}",
            "https": f"http://{proxy_auth}",
        }

    except Exception as e:
        print(f"[Ошибка получения прокси] {e}")
        return None


def get_product_link(product_name):
    cookies = {
        'user_id': 'd405adc69302fa642e2e6da98ad0748c',
        'status_id': '1',
        '_ym_uid': '1721719735519807660',
        '_ym_d': '1737495251',
        'isCookieNotes': 'true',
        '_ym_isad': '1',
        'PHPSESSID': 'n6q73rea91hn95p5ke2181721k',
        '_ym_visorc': 'w',
    }
    headers = {
        'accept': 'text/html, */*; q=0.01',
        'accept-language': 'ru,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://polezniemelochi.ru',
        'priority': 'u=1, i',
        'referer': 'https://polezniemelochi.ru/',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "YaBrowser";v="25.4", "Yowser";v="2.5"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        # 'cookie': 'user_id=d405adc69302fa642e2e6da98ad0748c; status_id=1; _ym_uid=1721719735519807660; _ym_d=1737495251; isCookieNotes=true; _ym_isad=1; PHPSESSID=n6q73rea91hn95p5ke2181721k; _ym_visorc=w',
    }

    data = {
        'word': product_name,
    }

    response = requests.post(
        'https://polezniemelochi.ru/shop/search/ajax_search_hints.php',
        cookies=cookies,
        headers=headers,
        data=data,
    )
    time.sleep(1)

    match = re.search(r'<a\s+href="([^"]+)"', response.text)
    if match:
        return match.group(1)


def get_price(url):
    user_agents = [
        "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.170 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.111 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 11; Mi 11 Ultra) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.170 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 12; OnePlus 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.111 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; Samsung Galaxy S22) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.170 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 10; Huawei P40 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.131 Mobile Safari/537.36"
    ]

    fake_ua = user_agents[randint(0, 9)]
    proxy = get_rand_proxy_list()

    headers = {
        "User-Agent": fake_ua
    }

    response = requests.get(url, headers=headers, proxies=proxy)

    if response.ok:
        soup = BeautifulSoup(response.text, 'html.parser')
        goods_card = soup.find('div', {'class': 'goods-card'})

        if not goods_card:
            return None

        old_price = goods_card.find('span', {'class': 'old'}).get_text(strip=True)
        price = goods_card.find('span', {'class': 'strong'}).get_text(strip=True)

        if old_price:
            old_price = float(old_price.replace(' ₽', '').replace(',', '.').replace(' ', ''))
        if price:
            price = float(price.replace(' ₽', '').replace(',', '.').replace(' ', ''))

        return old_price, price


if __name__ == "__main__":
    get_price("https://polezniemelochi.ru/shop/goods/cherenok_30mm_d_tyapok_120sm_v_s_suh-218071")
