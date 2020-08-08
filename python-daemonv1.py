import threading
import time
import netsnmp
import os
import Queue
import json
import re
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor

hosts = ['']

class SnmpClass(object):
    def __init__(self, oid_set, version=1, destHost="localhost", community="public"):
        self.oid_set = oid_set
        self.version = version
        self.destHost = destHost
        self.community = community

    def snmp_query(self):
        try:
            result = netsnmp.snmpwalk(self.oid_set, Version=self.version, DestHost=self.destHost, Community=self.community)
        except Exception, err:
            print err
            result = None
        return result

def Edelay(ip):
    dict = {}
    command_delay = 'ping ' + ip + ' -c 1 | grep from'
    delay_message = os.popen(command_delay).read()
    if delay_message=="":
        print("this package is lost")
    else:
        delay = delay_message.split('time=')[1].split()[0]
        nbrnum = str(ip).split('.')[-1]
        dict[str((hostnum, nbrnum))] = delay

        j = json.dumps(dict)
        #save the data to elasticseearch
        index_name=hostname+'-delay'
        es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
        if es.indices.exists(index=index_name):
            result = es.index(index=index_name, doc_type='doc', body=j)
            #result = es.create(index=index_name, doc_type='politics', id=str(hostnum)+str(":")+str(i), body=j)
        else:
            es.indices.create(index=index_name, ignore=400)
            result = es.index(index=index_name, doc_type='doc', body=j)     #index可以自动生成id，create要设置id
            #result = es.create(index=index_name, doc_type='politics', id=str(hostnum)+str(":")+str(i), body=j)
        print(result)


def Eloss(ip):
    dict = {}
    command_loss = 'iperf -c ' + ip + ' -u -t 1 -b 2M -y C | head -n 2 | tail -n 1'
    loss_message = os.popen(command_loss).read()
    loss = loss_message.split(',')[12]
    nbrnum = str(ip).split('.')[-1]
    dict[str((hostnum, nbrnum))] = loss
    j = json.dumps(dict)
    #save the data to elasticseearch
    index_name=hostname.strip()+'loss'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='doc', body=j)
        #result = es.create(index=index_name, doc_type='politics', id=str(hostnum)+str(":")+str(i), body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='doc', body=j)
        #result = es.create(index=index_name, doc_type='politics', id=str(hostnum)+str(":")+str(i), body=j)
    print(result)

def main():
    while True:
        for ip in hosts:
            thread_pool.submit(Edelay, ip)
            thread_pool.submit(Eloss, ip)

if __name__ == '__main__':
    thread_pool = ThreadPoolExecutor(max_workers=2)
    hostname = os.popen('echo $HOSTNAME').read()
    hostnum = re.findall('\d+',hostname)[0]
    main()