import requests
import time
import json
import aiohttp
import asyncio
from pathlib import Path

from settings import SBIS_TOKEN, SBIS_PRICE_ID
from sql_magic import PgSqlModel
from logger import logger
from get_from_unisiter import get_product_link
from utilits import strip_tags


headers_ = {"X-SBISAccessToken": SBIS_TOKEN}


def measure_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Функция {func.__name__} выполнилась за {elapsed_time:.6f} секунд")
        return result
    return wrapper


async def fetch_data(url, parameters, download_file_path=None):
    headers = {
        "X-SBISAccessToken": SBIS_TOKEN
    }
    while True:
        connector = aiohttp.TCPConnector(ssl=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=headers, params=parameters) as response:
                if response.status == 200 and not download_file_path:
                    return await response.json()
                elif response.status == 200 and download_file_path:
                    with open(download_file_path, 'wb') as file:
                        file.write(await response.read())
                        break
                else:
                    continue


def get_products(price, point_id):
    page = 0
    nomenclatures = []
    while True:
        parameters = {
            'pointId': point_id,
            'priceListId': price,
            'withBalance': 'true',
            'withBarcode': 'false',
            'page': page,
            'pageSize': '2000'
        }
        url = 'https://api.sbis.ru/retail/nomenclature/list?'

        response = requests.get(url=url, params=parameters, headers=headers_).json()
        nomenclatures.extend(response['nomenclatures'])

        if response['outcome']['hasMore']:
            logger.info(f'Получил ответ по странице №{page}')
            page += 1
            # logger.warning('Работа фунцкии прекращена досрочно')
            # return nomenclatures
        else:
            return nomenclatures


@measure_time
def get_item_list(point_id=None):
    prices_list = [SBIS_PRICE_ID]

    responses = []
    for price in prices_list:
        if point_id:
            response = get_products(price, point_id)
        else:
            response = get_products(price, 206)
        responses.append(response)

    nomenclatures = []
    for response in responses:
        nomenclatures.extend(response)

    category_list, product_list = [], []
    for product in nomenclatures:
        if product["isParent"]:
            category_list.append((product["hierarchicalId"], product["hierarchicalParent"], product["name"]))
        elif not product["isParent"]:
            product_list.append(({
                'sbis_id': product['nomNumber'],
                'name': product['name'],
                'description': product['description'],
                'parameters': product['attributes'],
                'images': product['images'],
                'price': product['cost'],
                'category': product['hierarchicalParent'],
                'stocks': product['balance'],
                'params': product['attributes']
            }))
    return category_list, product_list


@measure_time
def catalog_sync(sbis_id, product_list):
    PG_product = PgSqlModel("products_product")
    for product in product_list:
        if product['sbis_id'] == sbis_id:
            parameters = json.dumps(product['parameters'])

            description = strip_tags(product['description']) if product['description'] else ''
            unisiter_url = get_product_link(product['name'])

            product_data = {
                "sbis_id": product['sbis_id'], 'name': product['name'], 'description': description,
                'parameters': parameters, 'price': product['price'], 'images_response': product['images'],
                'category_id': product['category'], 'stocks_mol': product['stocks'], 'unisiter_url': unisiter_url
            }

            try:
                PG_product.add_object(**product_data)
            except Exception as e:
                logger.error(f'Ошибка {e}')


@measure_time
def stocks_update(product_list, point_name):
    cnt_zero_remains = 0
    PG_product = PgSqlModel('products_product')
    for product in product_list:
        sbis_id, stocks = product['sbis_id'], product['stocks']
        if stocks == 0.0:
            cnt_zero_remains += 1
        else:
            update_data = {'sbis_id': sbis_id, point_name: stocks}
            PG_product.add_object(**update_data)
    logger.info(f"В результате обновления остатков {point_name} установлено, что {cnt_zero_remains} товаров имеют 0 остаток.")


def count_files_in_directory(directory_path):
    """Возвращает количество файлов в указанной директории."""
    directory = Path(directory_path)
    if not directory.is_dir():
        raise ValueError(f"Указанный путь {directory_path} не является директорией.")

    return sum(1 for item in directory.iterdir() if item.is_file())


def pic_download(sbis_id, pic_urls):
    '''Итерируясь по списку товаров, ищем обновления в поле БД "images_response", если обновление есть,
    скачиваем картинки и вставляем обновление в БД'''
    parent_dir = Path(__file__).resolve().parent
    media_dir = parent_dir / "media" / "products"

    if pic_urls:
        cnt_img = 1
        for img in pic_urls:
            url = 'https://api.sbis.ru/retail/' + img
            file_name = sbis_id + '-' + str(cnt_img)
            file_path = media_dir / f"{file_name}.jpg"

            response = requests.get(url, headers={"X-SBISAccessToken": SBIS_TOKEN})
            with open(file_path, 'wb') as file:
                file.write(response.content)
                cnt_img += 1


def main_sinc(sbis_id):
    category_list, product_list = get_item_list(334198)
    catalog_sync(sbis_id, product_list)


if __name__ == "__main__":
    print(asyncio.run(get_item_list()))
    # main_sinc()
    # get_products(headers_, 0)
