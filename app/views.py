# Asynchronized account creation,
# dated 5th of May 2020
# Modified by Jemshid
# Incase memory is shooting up, check the contents of redis channel "transactionStates"
# as all all exception will be logged to the channel


from rq import Connection, Queue
from redis import Redis
# import time
from peerplays.account import Account
from peerplays import PeerPlays
import re
# from pprint import pprint
import json
# import os
from flask import render_template, request, jsonify, abort
from . import app, models
# from datetime import datetime
import traceback
from . import config
# from graphenebase.account import PasswordKey
from peerplaysbase.account import PublicKey

redis = Redis()
log = app.logger

# redis is being used to track the transaction state of account creation.
transactionStates = redis.get("transactionStates")
if type(transactionStates) == type(None):
    transactionStates = dict()
    transactionStates = json.dumps(transactionStates)
    redis.set('transactionStates', transactionStates)


peerplays = PeerPlays(
    config.witness_url,
    nobroadcast=config.nobroadcast,
    keys=[config.wif]
)


def api_error(msg):
    return jsonify({"error": {"base": [msg]}})


@app.route('/')
def index():
    # return "Jemshid is diagnosing this machine"
    return render_template('index.html')


@app.route('/api/v1/accounts', methods=['POST'], defaults={'referrer': None})
@app.route('/<referrer>/api/v1/accounts', methods=['POST'])
def tapbasic(referrer):
    # test if request has 'account' key
    if not request.json or 'account' not in request.json:
        abort(400)
    account = request.json.get('account', {})

    # make sure all keys are present
    if any([key not in account
            for key in ["active_key", "memo_key", "owner_key", "name"]]):
        abort(400)

    # prevent massive account registration
    if request.remote_addr != "127.0.0.1" and models.Accounts.exists(request.remote_addr):
        return api_error("Only one account per IP")

    # Check if account name is cheap name
    if (not re.search(r"[0-9-]", account["name"]) and
            re.search(r"[aeiouy]", account["name"])):
        return api_error("Only cheap names allowed!")

    # This is not really needed but added to keep API-compatibility with Rails Faucet
    account.update({"id": None})

    peerplays = PeerPlays(
        config.witness_url,
        nobroadcast=config.nobroadcast,
        keys=[config.wif]
    )

    try:
        Account(account["name"], peerplays_instance=peerplays)
        return api_error("Account exists")
    except:
        pass

    # Registrar
    registrar = account.get("registrar", config.registrar) or config.registrar
    try:
        registrar = Account(registrar, peerplays_instance=peerplays)
    except:
        return api_error("Unknown registrar: %s" % registrar)

    # Referrer
    referrer = account.get("referrer", config.default_referrer) or config.default_referrer
    try:
        referrer = Account(referrer, peerplays_instance=peerplays)
    except:
        return api_error("Unknown referrer: %s" % referrer)
    referrer_percent = account.get("referrer_percent", config.referrer_percent)

    # Create new account
    try:
        peerplays.create_account(
            account["name"],
            registrar=registrar["id"],
            referrer=referrer["id"],
            referrer_percent=referrer_percent,
            owner_key=account["owner_key"],
            active_key=account["active_key"],
            memo_key=account["memo_key"],
            proxy_account=config.get("proxy", None),
            additional_owner_accounts=config.get("additional_owner_accounts", []),
            additional_active_accounts=config.get("additional_active_accounts", []),
            additional_owner_keys=config.get("additional_owner_keys", []),
            additional_active_keys=config.get("additional_active_keys", []),
        )
    except Exception as e:
        log.error(traceback.format_exc())
        return api_error(str(e))

    models.Accounts(account["name"], request.remote_addr)

    try:
        if config.get("enable_initial_balance", None) == 1:
            peerplays.transfer(
                account["name"],
                config.get("initial_balance", 100),
                config.get("core_asset", "LLC"),
                "Initial Balance",
                registrar["id"],
            )
    except Exception as e:
        log.error(traceback.format_exc())
        return api_error(str(e))

    balance = registrar.balance(config.core_asset)
    if balance and balance.amount < config.balance_mailthreshold:
        log.critical(
            "The faucet's balances is below {}".format(
                config.balance_mailthreshold
            ),
        )

    return jsonify({"account": {
        "name": account["name"],
        "owner_key": account["owner_key"],
        "active_key": account["active_key"],
        "memo_key": account["memo_key"],
        "referrer": referrer["name"]
    }})


def AccountCreationForWorker(account):
    log.info("Account creation on chain started in the worker for the account")
    log.info(account)
    transactionStates = redis.get("transactionStates")
    transactionStates = json.loads(transactionStates)
    transactionStates[account["name"]] = "run"
    transactionStates = json.dumps(transactionStates)
    redis.set('transactionStates', transactionStates)

    peerplays = PeerPlays(
        config.witness_url,
        nobroadcast=config.nobroadcast,
        keys=[config.wif]
    )

    # Registrar
    registrar = account.get("registrar", config.registrar) or config.registrar
    try:
        registrar = Account(registrar, peerplays_instance=peerplays)
    except:
        transactionStates = redis.get("transactionStates")
        transactionStates = json.loads(transactionStates)
        transactionStates[account["name"]] = "Unknown registrar " + registrar
        transactionStates = json.dumps(transactionStates)
        redis.set('transactionStates', transactionStates)
        return

    # Referrer
    referrer = account.get("referrer", config.default_referrer) or config.default_referrer
    try:
        referrer = Account(referrer, peerplays_instance=peerplays)
    except:
        transactionStates = redis.get("transactionStates")
        transactionStates = json.loads(transactionStates)
        transactionStates[account["name"]] = "Unknown referrer" + referrer
        transactionStates = json.dumps(transactionStates)
        redis.set('transactionStates', transactionStates)
        return

    referrer_percent = account.get("referrer_percent", config.referrer_percent)

    # Create new account
    try:
        peerplays.create_account(
            account["name"],
            registrar=registrar["id"],
            referrer=referrer["id"],
            referrer_percent=referrer_percent,
            owner_key=account["owner_key"],
            active_key=account["active_key"],
            memo_key=account["memo_key"],
            proxy_account=config.get("proxy", None),
            additional_owner_accounts=config.get("additional_owner_accounts", []),
            additional_active_accounts=config.get("additional_active_accounts", []),
            additional_owner_keys=config.get("additional_owner_keys", []),
            additional_active_keys=config.get("additional_active_keys", []),
        )
        transactionStates = redis.get("transactionStates")
        transactionStates = json.loads(transactionStates)
        transactionStates.pop(account["name"])
        transactionStates = json.dumps(transactionStates)
        redis.set('transactionStates', transactionStates)
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
        print('views.py, line 186:', str(e))
        log.error(traceback.format_exc())
        transactionStates = redis.get("transactionStates")
        transactionStates = json.loads(transactionStates)
        transactionStates[account["name"]] = str(e)
        transactionStates = json.dumps(transactionStates)
        redis.set('transactionStates', transactionStates)
        # return api_error(str(e))

    try:
        if config.get("enable_initial_balance", None) == 1:
            peerplays.transfer(
                account["name"],
                config.get("initial_balance", 100),
                config.get("core_asset", "LLC"),
                "Initial Balance",
                registrar["id"],
            )
    except Exception as e:
        log.error(traceback.format_exc())
        transactionStates = redis.get("transactionStates")
        transactionStates = json.loads(transactionStates)
        transactionStates[account["name"]] = str(e)
        transactionStates = json.dumps(transactionStates)
        redis.set('transactionStates', transactionStates)
        # return api_error(str(e))

    balance = registrar.balance(config.core_asset)
    if balance and balance.amount < config.balance_mailthreshold:
        log.critical(
            "The faucet's balances is below {}".format(
                config.balance_mailthreshold
            ),
        )
    log.info('Account created on the chain')
    print(account)


@app.route('/api/v2/accounts', methods=['POST'], defaults={'referrer': None})
@app.route('/<referrer>/api/v2/accounts', methods=['POST'])
def tapbasicAsynchronous(referrer):

    # test is request has 'account' key
    if not request.json or 'account' not in request.json:
        abort(400)
    account = request.json.get('account', {})

    # make sure all keys are present
    if any([key not in account
            for key in ["active_key", "memo_key", "owner_key", "name"]]):
        abort(400)

    # prevent massive account registration
    if request.remote_addr != "127.0.0.1" and models.Accounts.exists(request.remote_addr):
        return api_error("Only one account per IP")

    # Check if account name is cheap name
    if (not re.search(r"[0-9-]", account["name"]) and
            re.search(r"[aeiouy]", account["name"])):
        return api_error("Only cheap names allowed!")

    # This is not really needed but added to keep API-compatibility with Rails Faucet
    account.update({"id": None})

    # check the transactionState of account
    # if the account creation is assigned to worker, account status is changed to "init"
    # if the account creation is taken up by worker, account status is changed to "run"
    # The pop statement in else is for the removal of other states, to minimize redis memory footprint
    # Repeat call returns the excepiton or nature of error.
     
    transactionStates = redis.get("transactionStates")
    transactionStates = json.loads(transactionStates)
    if account["name"] in transactionStates.keys():
        transactionState = transactionStates[account["name"]]
        if transactionState == "init":
            return api_error("Account init")
        elif transactionState == "run":
            return api_error("Account run")
        else:
            transactionState = transactionStates[account["name"]]
            transactionStates.pop(account["name"])
            transactionStates = json.dumps(transactionStates)
            redis.set('transactionStates', transactionStates)
            return api_error("Account " + transactionState)

    try:
        Account(account["name"], peerplays_instance=peerplays)
        return api_error("Account exists")
    except:
        pass

    try:
        for key in ['owner_key', 'active_key', 'memo_key']:
            PublicKey(account[key], peerplays.prefix)
    except:
        print('Wrong', key)
        return api_error("Wrong " + key)

    # models.Accounts(account["name"], request.remote_addr)

    with Connection(redis):
        q = Queue('faucet', connection=redis)
        job = q.enqueue(AccountCreationForWorker, args=(account,))
        transactionStates = redis.get("transactionStates")
        transactionStates = json.loads(transactionStates)
        transactionStates[account["name"]] = "init"
        transactionStates = json.dumps(transactionStates)
        redis.set('transactionStates', transactionStates)


    return jsonify({"account": account})

