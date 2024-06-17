import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
import requests
from fastapi.background import BackgroundTasks

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)

redis = get_redis_connection(
    host='redis_db_public_endpoint',
    port='port',
    password='password',
    decode_responses=True
)

class ProductOrder(HashModel):
    product_id: str
    quantity: int
    class Meta():
        database = redis

class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int
    status: str
    class Meta():
        database = redis

@app.post('/orders', tags=['store'])
def create(product_order: ProductOrder, background_tasks: BackgroundTasks):
    req = requests.get(f'http://localhost:8000/product/{product_order.product_id}')
    product = req.json()
    fee = product['price'] * 0.2

    order = Order(
        product_id = product_order.product_id,
        price = product['price'],
        fee = fee,
        total = product['price'] + fee,
        quantity = product_order.quantity,
        status = 'pending'
    )

    order.save()

    background_tasks.add_task(order_complete, order)

    return order

@app.get('/orders/{pk}', tags=['store'])
def get(pk: str):
    return Order.get(pk)

@app.get('/orders', tags=['store'])
def get_all():
    return [format(pk) for pk in Order.all_pks()]

def format(pk: str):
    order = Order.get(pk)
    return {
        'pk': order.pk,
        'product_id': order.product_id,
        'fee': order.fee,
        'total': order.total,
        'quantity': order.quantity,
        'status': order.status
    }

def order_complete(order: Order):
    time.sleep(5)
    order.status = 'completed'
    order.save()
    redis.xadd(name='order-completed', fields=order.model_dump())