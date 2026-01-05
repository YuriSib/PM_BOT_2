import requests
import json
from pathlib import Path
import time

from settings import VK_owner_id, VK_code
from sql_magic import PgSqlModel
from sqlite_comands import DBMagic
from logger import logger
from get_from_sbis import pic_download, get_item_list, main_sinc as sbis_db_sync
from get_from_unisiter import get_product_link, get_price


class ProductIntegrations:
    def __init__(self, sbis_data=None):
        self.sbis_data = sbis_data

    @staticmethod
    async def get_tokens(refresh_token, device_id, state):
        "Для получения access_token"
        url = "https://id.vk.com/oauth2/auth"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": "53476139",
            "device_id": device_id,
            "state": state,
            "scope": "market"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        logger.debug(f'refresh_token, device_id, state : {refresh_token, device_id, state}')
        response = requests.post(url, data=payload, headers=headers)

        logger.debug("Status code:", response.status_code)
        logger.debug("Response:", response.json())
        return response.json()

    @staticmethod
    async def get_url(access_token, one_photo=True):
        "Метод для получения URL для загрузки изображения"
        data = {
            'group_id': VK_owner_id,
            'access_token': access_token,
            'v': '5.199',
        }
        "Если планируется загрузить более одного фото, добавляем параметр bulk"
        if one_photo:
            data['bulk'] = 1
        resp = requests.post('https://api.vk.com/method/market.getProductPhotoUploadServer', data=data).json()

        if resp.get('error'):
            logger.error(f'''Ошибка в ответ на запрос - {resp.get('error')}''')
            return None

        upload_url, bulk_upload = resp['response'].get('upload_url'), resp['response'].get('bulk_upload')

        if upload_url:
            return upload_url.split('token=')[1]
        else:
            return bulk_upload

    @staticmethod
    async def download_photo(upload_url, photo_path):
        "Аргумент photo или list или str"
        params = {
            'token': upload_url,
        }

        if type(photo_path) is str:
            files = {'file': open(photo_path, 'rb')}
        else:
            files = {}
            cnt = 1
            for photo in photo_path:
                files[f'file{cnt}'] = open(photo, 'rb')

        response = requests.post('https://pu.vk.com/gu-s/photo/v2/upload', params=params, files=files).json()
        if response.get('error_msg'):
            logger.error(f'''Ошибка в ответ на запрос - {response.get('error_msg')}''')
            return None
        return response

    @staticmethod
    async def get_photo_id(photo_data, access_token, one_photo=True):
        method = 'market.saveProductPhoto' if one_photo else 'market.saveProductPhotoBulk'
        upload_response = json.dumps(photo_data)

        data = {
            'upload_response': upload_response,
            'access_token': access_token,
            'v': '5.199',
        }

        response = requests.post(f'''https://api.vk.com/method/{method}''', data=data).json()
        if response.get('error'):
            logger.error(f'''Ошибка в ответ на запрос - {response['error']['error_msg']}''')
            return None
        return response['response'].get('photo_id')

    @staticmethod
    async def add_product(category_id, main_photo_id, name, desc, site_link, price, access_token):
        price = str(price)
        data = {
            'owner_id': -VK_owner_id,
            'name': name,
            'description': desc,
            'category_id': category_id,
            'main_photo_id': main_photo_id,
            'access_token': access_token,
            'v': '5.199',
            'price': price,
        }

        if site_link:
            data['url'] = site_link

        response = requests.post('https://api.vk.com/method/market.add', data=data).json()
        logger.info(response)
        time.sleep(1)
        if response.get('response'):
            return response['response']['market_item_id']

    @staticmethod
    async def get_products(access_token):
        data = {
            'owner_id': -VK_owner_id,
            'access_token': access_token,
            'v': '5.199',
        }

        response = requests.post('https://api.vk.com/method/market.get', data=data).json()

        if response.get('error_msg'):
            logger.error(f'''Ошибка в ответ на запрос - {response.get('error_msg')}''')
            return None

        logger.debug(f'''Получено {response['response']['count']}''')

        return response['response']['items']

    @staticmethod
    async def product_delete(prod_id, access_token):
        data = {
            'owner_id': -VK_owner_id,
            'access_token': access_token,
            'item_id': prod_id,
            'v': '5.199',
        }

        response = requests.post('https://api.vk.com/method/market.delete', data=data).json()
        if response.get('error'):
            logger.error(f'''Ошибка в ответ на запрос - {response['error']['error_msg']}''')

    async def sync_one_prod(self, sbis_id):
        site_price, pic_urls, unisiter_url = None, None, None

        # sbis_db_sync(sbis_id)

        # products_sql = PgSqlModel('products_product')
        # product_data = products_sql.get_category_prod(sbis_id)

        category_list, product_list = get_item_list()

        if not product_list:
            logger.error('Из прайса ничего не излечено!')

        for prod in product_list:
            if prod['sbis_id'] == sbis_id:
                logger.debug(f"Товар {sbis_id} найден в прайсе")

                name = prod['name']
                desc = prod['description']
                pic_urls = prod['images']
                site_price = prod['price']
                category_id = prod['category']
                category = prod['category']
                params = prod['params']

                logger.debug(f"Ссылка на фото -  {pic_urls}")

                category_name = None
                for ctg in category_list:
                    if int(ctg[0]) == int(category):
                        category_parent = ctg[1]
                        category_name = ctg[2]
                        break
                if not category_name or not name:
                    return None

        "Если изображения нет в каталоге, пропускаем итерацию с этим товаром"
        if not pic_urls:
            logger.error(f'Отсутствует ссылка на изображение. Проверить наличие товара {sbis_id} в прайсе!')
            return f'Отсутствует ссылка на изображение. Проверить наличие товара  {sbis_id} в прайсе!'

        pic_download(sbis_id, pic_urls)
        directory = Path(f'media/products/')
        main_photo_path = directory / f"{sbis_id}-1.jpg"
        if not main_photo_path.is_file():
            logger.warning(f'изображения нет в каталоге, пропускаем итерацию с товаром {name}')
            return 'изображения нет в каталоге'

        # получаем url товара и его old_price, price
        logger.debug(f'Пытаюсь получить ссылку для {name}')
        unisiter_url = get_product_link(name)
        if unisiter_url:
            logger.debug(f'Нашел ссылку для {name}')
            site_link = "https://polezniemelochi.ru" + unisiter_url
        else:
            logger.debug(f'Ссылку для {name} не нашел!')

        if not unisiter_url or unisiter_url == "Товар не найден":
            return "Товар не найден на сайте"
        try:
            old_price, price = get_price(site_link)
        except Exception as e:
            old_price, price = None, int(site_price)
            logger.error(f'Ошибка при работе функции get_price - \n{e}')
            return f'Ошибка при работе функции get_price - \n{e}'

        "Загружаем товар в ВК"
        product_data = {
            'sbis_id': sbis_id,
            'images': pic_urls,
            'name': name,
            'description': desc,
            'site_link': site_link,
            'price': price,
            'old_price': old_price,
            'category': category_id,
            'category_parent_id': category_parent,
            'category_name': category_name,
            'parameters': params
        }

        logger.debug(f'product_data - {product_data}')

        if not old_price:
            product_data.pop('old_price', None)
        url = "https://parsx.ru/vk_sync/api/integrations/"
        data = {
            'authorization_code': VK_code,
            'product_data': product_data
        }
        "Логика интеграции на стороне ParsX"
        response = requests.post(url, json=data)
        if response.status_code == 200:
            prod_vk_id = response.json()
            if "ERROR" in prod_vk_id:
                return prod_vk_id["ERROR"]
        else:
            logger.error(f"status_code - {response.status_code}")


if __name__ == "__main__":
    # vk_sync = ProductIntegrations()
    # vk_sync.sync_one_prod("РТ000018924")
    pass
