import requests


data = {
    "customer_id": 418
}

url = "https://parsx.ru/vk_login/api/update_products/"

response = requests.post(url=url, json=data)
print(response)
