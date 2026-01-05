from datetime import datetime
import asyncio
import psycopg

from logger import logger
from settings import WORK_CNT_DB, POL_MEL_DB, PARSX_DB

# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class DBMagic:
    def __init__(self, DB, product_db=None):
        self.CONNECT_QWERY = (f"""dbname={DB['DB_NAME']} user={DB["DB_USERNAME"]} password={DB["DB_PASSWORD"]} 
                                  host={DB["HOST"]} port={DB["PORT"]}""")
        if not product_db:
            try:
                conn = psycopg.connect(self.CONNECT_QWERY)
                with conn.cursor() as cursor:
                    cursor.execute("""CREATE TABLE IF NOT EXISTS Users
                                    (
                                        tg_id BIGINT NOT NULL,
                                        user_name TEXT NOT NULL,
                                        PRIMARY KEY (tg_id)
                                    );
                        
                                    CREATE TABLE IF NOT EXISTS Tables (
                                            table_id SERIAL,
                                            table_name TEXT NOT NULL,
                                            reg_time TIMESTAMP WITH TIME ZONE,
                                            min_cost INTEGER,
                                            max_cost INTEGER,
                                            user_id BIGINT,
                                            verified_status BOOL default false,
                                            PRIMARY KEY (table_id),
                                            CONSTRAINT fk_user FOREIGN KEY (user_id)
                                                REFERENCES Users (tg_id)
                                                ON UPDATE NO ACTION
                                                ON DELETE NO ACTION
                                        );
                                        """)
                    conn.commit()
            except Exception as e:
                logger.error(f"Ошибка при инициализации БД {e}")

    async def add_table_data(self, table_name: str):
        """
        Возвращает всю таблицу.
        :param table_name: Имя таблицы
        """
        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                query = f'''SELECT * FROM {table_name}'''
                await cursor.execute(query)
                object_data = await cursor.fetchall()
                return object_data if object_data else None

    async def check_exist(self, table_name: str, id_field=None, id_="All"):
        """
        Проверяет, существует ли объект в таблице. Если таковой есть, возвращает его полностью.
        :param table_name: Имя таблицы
        :param id_field: Название поля
        :param id_: ID объекта
        """
        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                if id_ == "All":
                    query = f"SELECT * FROM {table_name}"
                    await cursor.execute(query)
                else:
                    query = f"SELECT * FROM {table_name} WHERE {id_field} = %s"
                    await cursor.execute(query, (id_,))
                object_data = await cursor.fetchall()
                return object_data if object_data else None

    async def add_data(self, table_name, data):
        """
        Добавляет новый объект в таблицу.

        :param table_name: Имя таблицы, в которую нужно добавить данные.
        :param data: Словарь, где ключи - это названия столбцов, а значения - значения для вставки.
        """
        # Проверяем, что переданный словарь не пуст
        logger.debug(f'data - {data}')
        if not data:
            raise ValueError("Data dictionary cannot be empty")
        # Получаем имена столбцов и их значения
        columns = data.keys()
        values = tuple(data.values())

        # Формируем строки со столбцами и плейсхолдерами
        column_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))

        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {table_name} ({column_names})
                VALUES ({placeholders});
                """
                await cursor.execute(query, values)
                await conn.commit()

    async def update_data(self, table_name, pk_object_id: dict, field_data: dict):
        """Обновляет данные в таблице
        :param table_name: имя таблицы
        :param pk_object_id: словарь {PK_поле: значение}
        :param field_data: словарь {поле: значение} - поля с данные, которые нужно обновить
        """
        # Проверяем, что переданный словарь не пуст
        if not field_data:
            raise ValueError("Data dictionary cannot be empty")

        # Создаем строку для SET и для WHERE
        set_clause = ', '.join([f"{key} = %s" for key in field_data.keys()])
        where_clause = ' AND '.join([f"{key} = %s" for key in pk_object_id.keys()])
        values = tuple(field_data.values()) + tuple(pk_object_id.values())

        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"

        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, values)
                await conn.commit()

    async def update_verified_status(self):
        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""UPDATE Tables SET verified_status = TRUE;""")
                await conn.commit()

    async def get_unverified_table(self):
        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM Tables WHERE verified_status = False;")
                product = await cursor.fetchall()
                if product:
                    return product
                else:
                    return False

    async def get_auth(self, obj_id):
        async with await psycopg.AsyncConnection.connect(self.CONNECT_QWERY) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT authorization_code "
                                     "FROM vk_sync_integrations "
                                     "WHERE id = %s;", (obj_id,))

                data = await cursor.fetchall()
                if data:
                    authorization_code = data[0]

                    return authorization_code


if __name__ == "__main__":
    # asyncio.run(update_verified_status())
    # print(asyncio.run(get_unverified_table()))
    # print(asyncio.run(get_user()))

    # print(12436236735686796780467)
    product_db = DBMagic(POL_MEL_DB)
    print(asyncio.run(product_db.check_exist("products_product", "sbis_id", "X1749805"))[0][2])

