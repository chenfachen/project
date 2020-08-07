import threading
import time
import netsnmp
import pymysql
import json
import os
import Queue
import re
import collections
from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

counter=0         #record the time of index
oid_set1=".1.3.6.1.2.1.14.10.1.1"
oid_set2=".1.3.6.1.2.1.2.2.1.10"
oid_set3=".1.3.6.1.2.1.2.2.1.16"
oid_set4="ifDescr"
oid_set5="ifInDiscards"
oid_set6="ifOutDiscards"
oid_set7="ifInErrors"
oid_set8="ifOutErrors"


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

def preInThroughput():
    global time_pre_in
    global ifIn_pre
    time_pre_in = time.time()
    snmp_query_obj2 = SnmpClass(oid_set=oid_set2)
    ifIn_pre = snmp_query_obj2.snmp_query()

def PortInThroughput(i,counter):                #portInThroughput and rx.utilization
    dict = {}
    #dict = collections.OrderedDict()
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur=time.time()
    ifIn_cur = ()
    snmp_query_obj2 = SnmpClass(oid_set=oid_set2)
    ifIn_cur = snmp_query_obj2.snmp_query()
    if(ifIn_pre[i]<=ifIn_cur[i]):
        inthroughput = (int(ifIn_cur[i])-int(ifIn_pre[i]))/(time_cur-time_pre_in)
    else:
        inthroughput = (2**32-ifIn_pre[i]+ifIn_cur[i])/(time_cur-time_pre_in)
    #dict[str((hostnum,port))] = inthroughput
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["inthroughput"] = inthroughput
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'inthroughput'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    print(result)

    ifspeed=1024*(10**6)
    dict_rx={}
    rx_utilization=(inthroughput*8)/ifspeed
    dict_rx["hostname"] = hostname
    dict_rx["port"] = port
    dict_rx["collection couter"] = counter
    dict_rx["rx_utilization"] = str(rx_utilization*100)+'%'
    #dict_rx[str((hostnum,port))] = str(rx_utilization*100)+'%'
    j_rx=json.dumps(dict_rx)
    index_name_rx = 'rx_utilization'
    if es.indices.exists(index=index_name_rx):
        result = es.index(index=index_name_rx, doc_type='politics', body=j_rx)
    else:
        es.indices.create(index=index_name_rx, ignore=400)
        result = es.index(index=index_name_rx, doc_type='politics', body=j_rx)

    if rx_utilization>0.9:
        dict_rx_up = {}
        dict_rx_up["hostname"] = hostname
        dict_rx_up["port"] = port
        dict_rx_up["rx_utilization"] = rx_utilization
        dict_rx_up["time"] = time_cur
        j_rx_up = json.dumps(dict_rx_up)
        index_name_rxup = 'rx_up'
        if es.indices.exists(index=index_name_rxup):
            result = es.index(index=index_name_rxup, doc_type='politics', body=j_rx_up)
        else:
            es.indices.create(index=index_name_rxup, ignore=400)
            result = es.index(index=index_name_rxup, doc_type='politics', body=j_rx_up)

    global time_pre_in
    global ifIn_pre
    time_pre_in = time_cur
    ifIn_pre = ifIn_cur

def preOutThroughput():
    global time_pre_out
    global ifOut_pre
    time_pre_out = time.time()
    snmp_query_obj3 = SnmpClass(oid_set=oid_set3)
    ifOut_pre = snmp_query_obj3.snmp_query()

def PortOutThroughput(i,counter):                #portOutThroughput and tx.utilization
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur=time.time()
    ifOut_cur = ()
    snmp_query_obj3 = SnmpClass(oid_set=oid_set3)
    ifOut_cur = snmp_query_obj3.snmp_query()
    if(ifOut_pre[i]<=ifOut_cur[i]):
        outthroughput = (int(ifOut_cur[i])-int(ifOut_pre[i]))/(time_cur-time_pre_out)
    else:
        outthroughput = (2**32-ifOut_pre[i]+ifOut_cur[i])/(time_cur-time_pre_out)
    #dict[str((hostnum,port))] = outthroughput
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["outthroughput"] = outthroughput
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'outthroughput'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    print(result)

    ifspeed=1024*(10**6)
    dict_tx={}
    tx_utilization=(outthroughput*8)/ifspeed
    #dict_tx[str((hostnum,port))] = str(tx_utilization*100)+'%'
    dict_tx["hostname"] = hostname
    dict_tx["port"] = port
    dict_tx["collection couter"] = counter
    dict_tx["tx_utilization"] = str(tx_utilization*100)+'%'
    j_tx=json.dumps(dict_tx)
    index_name_tx = 'tx_utilization'
    if es.indices.exists(index=index_name_tx):
        result = es.index(index=index_name_tx, doc_type='politics', body=j_tx)
    else:
        es.indices.create(index=index_name_tx, ignore=400)
        result = es.index(index=index_name_tx, doc_type='politics', body=j_tx)

    if tx_utilization > 0.9:
        dict_tx_up = {}
        dict_tx_up["hostname"] = hostname
        dict_tx_up["port"] = port
        dict_tx_up["rx_utilization"] = tx_utilization
        dict_tx_up["time"] = time_cur
        j_tx_up = json.dumps(dict_tx_up)
        index_name_txup = 'tx_up'
        if es.indices.exists(index=index_name_txup):
            result = es.index(index=index_name_txup, doc_type='politics', body=j_tx_up)
        else:
            es.indices.create(index=index_name_txup, ignore=400)
            result = es.index(index=index_name_txup, doc_type='politics', body=j_tx_up)

    global time_pre_out
    global ifOut_pre
    time_pre_out = time_cur
    ifOut_pre = ifOut_cur

def preifInDiscards():
    global time_pre_indis
    global ifIndis_pre
    time_pre_indis = time.time()
    snmp_query_obj5 = SnmpClass(oid_set=oid_set5)
    ifIndis_pre = snmp_query_obj5.snmp_query()

def PortifInDiscards(i,counter):           
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur=time.time()
    ifIndis_cur = ()
    snmp_query_obj5 = SnmpClass(oid_set=oid_set5)
    ifIndis_cur = snmp_query_obj5.snmp_query()
    indiscards = (int(ifIndis_cur[i])-int(ifIndis_pre[i]))/(time_cur-time_pre_indis)
    #dict[str((hostnum,port))] = str(indiscards*100)+'%'
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["indiscards"] = str(indiscards*100)+'%'
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'indiscards'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    print(result)
    global time_pre_indis
    global ifIndis_pre
    time_pre_indis = time_cur
    ifIndis_pre = ifIndis_cur

def preifOutDiscards():
    global time_pre_outdis
    global ifOutdis_pre
    time_pre_outdis = time.time()
    snmp_query_obj6 = SnmpClass(oid_set=oid_set6)
    ifOutdis_pre = snmp_query_obj6.snmp_query()

def PortifOutDiscards(i,counter):           
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur=time.time()
    ifOutdis_cur = ()
    snmp_query_obj6 = SnmpClass(oid_set=oid_set6)
    ifOutdis_cur = snmp_query_obj6.snmp_query()
    outdiscards = (int(ifOutdis_cur[i])-int(ifOutdis_pre[i]))/(time_cur-time_pre_outdis)
    #dict[str((hostnum,port))] = str(outdiscards*100)+'%'
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["outdiscards"] = outdiscards
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'outdiscards'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    print(result)
    global time_pre_outdis
    global ifOutdis_pre
    time_pre_outdis = time_cur
    ifOutdis_pre = ifOutdis_cur

def preifInErrors():
    global time_pre_inerr
    global ifInerr_pre
    time_pre_inerr = time.time()
    snmp_query_obj7 = SnmpClass(oid_set=oid_set7)
    ifInerr_pre = snmp_query_obj7.snmp_query()

def PortifInErrors(i,counter):           
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur=time.time()
    ifInerr_cur = ()
    snmp_query_obj7 = SnmpClass(oid_set=oid_set7)
    ifInerr_cur = snmp_query_obj7.snmp_query()
    inerror = (int(ifInerr_cur[i])-int(ifInerr_pre[i]))/(time_cur-time_pre_inerr)
    #dict[str((hostnum,port))] = str(inerror*100)+'%'
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["inerror"] = str(inerror*100)+'%'
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'inerrors'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    print(result)
    global time_pre_inerr
    global ifInerr_pre
    time_pre_inerr = time_cur
    ifInerr_pre = ifInerr_cur

def preifOutErrors():
    global time_pre_outerr
    global ifOuterr_pre
    time_pre_outerr = time.time()
    snmp_query_obj8 = SnmpClass(oid_set=oid_set8)
    ifOuterr_pre = snmp_query_obj8.snmp_query()

def PortifOutErrors(i,counter):
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur=time.time()
    ifOuterr_cur = ()
    snmp_query_obj8 = SnmpClass(oid_set=oid_set8)
    ifOuterr_cur = snmp_query_obj8.snmp_query()
    outerror = (int(ifOuterr_cur[i])-int(ifOuterr_pre[i]))/(time_cur-time_pre_outerr)
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["outerror"] = str(outerror*100)+'%'
    #dict[str((hostnum,port))] = str(outerror*100)+'%'
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'outerrors'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    print(result)
    global time_pre_outerr
    global ifOuterr_pre
    time_pre_outerr = time_cur
    ifOuterr_pre = ifOuterr_cur



def main(counter):
    snmp_query_obj1 = SnmpClass(oid_set=oid_set1)
    snmp_query_obj2 = SnmpClass(oid_set=oid_set2)
    snmp_query_obj3 = SnmpClass(oid_set=oid_set3)
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    #ip_nbr = []
    ip_nbr = snmp_query_obj1.snmp_query()
    # f = open("C:\\Users\\HOU\\Desktop\\snmp-nbr","r+")
    # for line in f:
    #     #ip_res = re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",line)
    #     ip_res = line.split()[-1]
    #     ip_nbr.append(ip_res)
    # #f.seek(0)
    # #f.truncate()
    # f.close
    print(ip_nbr)

    for i in range(0,len(if_num)):
        if hostname.strip() in if_num[i]:
            thread_pool.submit(PortInThroughput,i,counter)
            thread_pool.submit(PortOutThroughput,i,counter)
            thread_pool.submit(PortifInDiscards,i,counter)
            thread_pool.submit(PortifOutDiscards, i, counter)
            thread_pool.submit(PortifInErrors, i, counter)
            thread_pool.submit(PortifOutErrors, i, counter)
        else:
            continue


if __name__ == '__main__':
    #start = time.time()
    hostname = os.popen('echo $HOSTNAME').read()
    hostnum = re.findall('\d+',hostname)[0]

    thread_pool = ThreadPoolExecutor(max_workers=6)

    try:
        db = pymysql.connect('114.212.112.36', 'root', '123456', 'STARTTIME')
        print("connect successful")
    except pymysql.Error as e:
        print("fail to connect mysql" + str(e))
    cur = db.cursor()
    selecttime = cur.execute("SELECT time FROM Time ORDER BY id DESC LIMIT 0,1")
    results = cur.fetchall()
    for row in results:
        time_start = row[0]
        print(time_start)
    time_cur = float(time.time())
    time_sleep = float(time_start) - time_cur
    time.sleep(time_sleep)

    preInThroughput()
    preOutThroughput()
    preifInDiscards()
    preifOutDiscards()
    preifInErrors()
    preifOutErrors()
   # time_wait = start_time - time.time()
    time.sleep(3)

    interval = 6

    while True:
        time_remain = interval - time.time()%interval
      #  print("sleep %f seconds", time_remain)
        time.sleep(time_remain)
        main(counter)
        counter = counter+1


    #end = time.time()
    #print('Running time: %s Seconds' % (end - start))
