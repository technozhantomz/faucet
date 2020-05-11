#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import numpy as np
import json
import time
from multiprocessing import Pool

urlBase = 'https://dick-faucet.peerplays.download'

# 35.183.11.136
# urlBase = 'http://35.183.11.136:5000'
urlBase = 'http://localhost:5000'
api = '/api/v1/accounts'
api = '/api/v2/accounts'

url = urlBase + api


def JTest(name=None):
    jTemplate = {'account': {
        'name': 'qa3',
        'owner_key': 'TEST6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV',
        'active_key': 'TEST6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV',
        'memo_key': 'TEST6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV',
        'refcode': '',
        'referrer': ''}}
    if isinstance(name, type(None)):
        name = 'j1-' + str(np.random.randint(100000000000000000))
    jTest = jTemplate
    jTest['account']['name'] = name
    return jTest

def TestStates(jTest):
    r = requests.post(url, json=jTest, timeout=(300, 600))
    text = r.text
    text = json.loads(text)
    return text

def TestStatesAll():
    jTest = JTest()
    print('Test Started')
    while True:
        text = TestStates(jTest)
        if "account" in text:
            break
    print('Test Account Creation Started')
    while True:
        text = TestStates(jTest)
        # print(text)
        if "error" in text:
            if text["error"]["base"][0] == "Account init":
                break
    print('Test Account in queue')
    while True:
        text = TestStates(jTest)
        # print(text)
        if "error" in text:
            if text["error"]["base"][0] == "Account run":
                break
    print('Test Account is in the current worker process')
    while True:
        text = TestStates(jTest)
        # print(text)
        if "error" in text:
            if text["error"]["base"][0] == "Account exists":
                break
    print('Test Account Created')
    print("Test Successful, All transaction states are reproduced")

def Bombard(jTest):
    tic = time.time()
    try:
        r = requests.post(url, json=jTest, timeout=(300, 600))
        tocReq = time.time() - tic
        # print('time = ', time.time() - tic)
        text = r.text
        # print(jTest)
        textDict = json.loads(text)
        if 'account' in textDict:
            print('name:', textDict['account']['name'], tocReq, time.time() - tic)
            return (True, time.time(), tocReq)
            # return True, textDict
        else:
            print('FAILED:', text, tocReq, time.time() - tic)
            # return False, textDict
            return (False, time.time(), tocReq)
    except Exception as e:
        # print('text:', text)
        print('exception Type:', type(e))
        print('exception Args:', e.args)
        print('e', e)
        return (False, time.time(), 0)


def Bombards(count, numberOfProcesses):
    jTests = []
    for k in range(count):
        jTest = JTest()
        jTests.append(jTest)
    # resBombards = []
    # textDicts = []
    p = Pool(processes=numberOfProcesses)
    print('starting pool map')
    tic = time.time()
    r = p.map(Bombard, jTests)
    print('done pool map')
    p.close()
    print('closed pool')
    #r = list(map(Bombard, jTests))
    toc = time.time() - tic
    print('time Total=', toc, 'count=', count, 'average=', toc/count)
    #print('timePerCall = ', toc / count, 'succeesScore:', np.sum(r) * 100 / count)
    return r
#    for k in range(count):
#        jTest = jTests[k]
#        print(k, jTest)
#        resBombard, textDict = Bombard(jTest)
#        resBombards.append(resBombard)
#        textDicts.append(textDict)
#    return resBombards, textDicts

    

if __name__ == "__main__":
    TestStatesAll()
