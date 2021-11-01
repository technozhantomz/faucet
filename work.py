from redis import Redis
from rq import Queue, Worker, Connection

r = Redis()
# queue = Queue('faucet')

with Connection(r):
    worker = Worker(["faucet"], connection=r, name='faucet')
    print('worker started')
    worker.work()
    print('worker exited')
