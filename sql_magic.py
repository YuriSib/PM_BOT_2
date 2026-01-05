import time

import psycopg
import json

from settings import VK_SYNC_DB, PARSX_DB
from logger import logger


DB_NAME, DB_USERNAME, DB_PASSWORD, HOST, PORT = (
    VK_SYNC_DB['DB_NAME'], VK_SYNC_DB['DB_USERNAME'], VK_SYNC_DB['DB_PASSWORD'], VK_SYNC_DB['HOST'], VK_SYNC_DB['PORT'])

class PgSqlModel:
    def __init__(self, table):
        """
        Инициализация объекта для работы с PgSql.
        Добавление тригеров.
        """
        self.table = table
        self.conn = psycopg.connect(
            f"dbname={DB_NAME} user={DB_USERNAME} password={DB_PASSWORD} host={HOST} port={PORT}")
        logger.debug("Соединение установлено.")

    def object_exists(self, column_name, primary_key):
        """
        Проверяет наличие объекта в таблице по заданным условиям.
        :param primary_key: первичный ключ.
        :param column_name: название поля
        :return: True, если объект существует, иначе False.
        """
        query = f"SELECT 1 FROM {self.table} WHERE {column_name} = '{primary_key}'"

        with self.conn.cursor() as cursor:
            cursor.execute(query)

            return cursor.fetchone() is not None

    def add_object(self, **kwargs):
        """
        Добавляет объект в таблицу.
        :param kwargs: Словарь с названиями колонок и значениями для вставки.
        """
        columns = ', '.join(kwargs.keys())
        fields_for_upd = ', '.join([f"{fld} = COALESCE(EXCLUDED.{fld}, {self.table}.{fld})" for fld in kwargs.keys()])

        placeholders = ', '.join(['%s'] * len(kwargs))
        values = tuple(kwargs.values())

        pk_field = {"products_product": "sbis_id", "products_category": "id"}
        query = (f"INSERT INTO {self.table} ({columns})\n"
                 f"VALUES ({placeholders})\n"
                 f"ON CONFLICT({pk_field[self.table]}) DO UPDATE SET "
                 f"{fields_for_upd};"
                 )
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, values)
                self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка запроска к БД. {kwargs}\n{e} \nЗапрос - {query}")

    def get_image_list(self, sbis_id):
        if self.table != 'products_product':
            logger.error('Метод get_image_list используется только с таблицей products_product')
            raise Exception
        query = (f"SELECT images_response "
                 f"FROM {self.table} "
                 f"WHERE sbis_id = '{sbis_id}'")
        with self.conn.cursor() as cursor:
            cursor.execute(query)

            result = cursor.fetchone()
        if result:
            return result[0]

    def get_product_data(self, sbis_id):
        if self.table != 'products_product':
            logger.error('Метод get_product_data используется только с таблицей products_product')
            raise Exception
        query = (f"SELECT * "
                 f"FROM {self.table} "
                 f"WHERE sbis_id = '{sbis_id}'")
        with self.conn.cursor() as cursor:
            cursor.execute(query)

            result = cursor.fetchone()
            if result:
                return result

    def get_category(self):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products_category")
        return cursor.fetchall()

    def edit_object(self, obj_id, field, value):
        """
        Обновляет объект, меняя значение одного из его полей.
        :param obj_id: ID объекта
        :param field: название поля
        :param value: значение
        """
        query = f"""
                UPDATE {self.table}
                SET {field} = %s
                WHERE id = %s
            """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (value, obj_id))
            self.conn.commit()

    def products_iteration(self, offset: int):
        """
        Возвращает список из 100 товаров из БД. БД обходится по очереди.
        :param offset: Индекс строки БД, с которой будет начинаться список.
        """
        batch_size = 100
        last_page = False
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products_product ORDER BY id LIMIT %s OFFSET %s", (batch_size, offset))
            rows = cursor.fetchall()

            if len(rows) < batch_size:
                last_page = True

            return rows, last_page

    def get_vk_category(self, category_id):
        query = f"""
                    SELECT vk_id 
                    FROM products_category 
                    WHERE id = %s
                """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (category_id,))

            return cursor.fetchone()

    def get_category_prod(self, sbis_id):
        "Метод вернет ID категории ВК и информацию о товаре"
        query_1 = f"""
                    SELECT *
                    FROM products_product
                    WHERE sbis_id = %s;
                """
        query_2 = f"""
                    SELECT vk_id FROM products_category
                    WHERE id = (
                            SELECT category_id
                            FROM products_product
                            WHERE sbis_id = %s
                    );
                """
        with self.conn.cursor() as cursor:
            cursor.execute(query_1, (sbis_id,))
            product_data = cursor.fetchone()

            cursor.execute(query_2, (sbis_id,))
            vk_category_id = cursor.fetchone()

            if not product_data:
                logger.warning(f'product_data нет в БД')
                return None
            elif not vk_category_id:
                logger.debug(f'vk_category_id нет в БД')
                return None

            return product_data, vk_category_id


if __name__ == "__main__":
    # conn = psycopg.connect(f"dbname={DB_NAME} user={DB_USERNAME} password={DB_PASSWORD} host={HOST} port={PORT}")
    # cur = conn.cursor()
    # cur.execute("SELECT * FROM products_product")
    # for row in cur:
    #     print(row)
    #
    # cur.close()
    # conn.close()

    sql = PgSqlModel(None)
    print(sql.get_category_prod("X5749947"))
