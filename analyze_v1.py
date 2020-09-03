# coding:utf-8
import threading
import time
import datetime
import netsnmp
import os
import Queue
import json
import re
import pymysql
import psutil
import ConfigParser
from operator import itemgetter
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor
import collections
from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import commands
import sys

es_addr = '114.212.112.36'
es_port = 9206

mysql_addr = '114.212.112.36'
mysql_account = 'root'
mysql_pw = '123456'
mysql_name = 'communication_test'
mysql_port = 3306


experiment_id = sys.argv[1]
hosts = {}     #记录ping和iperf的目的ip
counter = 0  # record the time of index
counter_ping = 0
oid_set1 = ".1.3.6.1.2.1.14.10.1.1"
oid_set2 = ".1.3.6.1.2.1.2.2.1.10"
oid_set3 = ".1.3.6.1.2.1.2.2.1.16"
oid_set4 = "ifDescr"
oid_set5 = "ifInDiscards"
oid_set6 = "ifOutDiscards"
oid_set7 = "ifInErrors"
oid_set8 = "ifOutErrors"


class SnmpClass(object):
    def __init__(self, oid_set, version=1, destHost="localhost", community="public"):
        self.oid_set = oid_set
        self.version = version
        self.destHost = destHost
        self.community = community

    def snmp_query(self):
        try:
            result = netsnmp.snmpwalk(self.oid_set, Version=self.version, DestHost=self.destHost,
                                      Community=self.community)
        except Exception, err:
            print(err)
            result = None
        return result


class MYSQL:
    def __init__(self, host, user, password, database, port, charset="utf8"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.charset = charset
        self.conn = None

    # 连接数据库
    def connect(self):
        self.conn = pymysql.connect(host=self.host,
                                    user=self.user,
                                    password=self.password,
                                    database=self.database,
                                    port=self.port,
                                    charset=self.charset)
        if self.conn.open == 1:
            print(">> 数据库连接成功!")
            return 1
        return 0

    # 关闭数据库连接
    def disconnect(self):
        self.conn.close()
        print(">> 数据库关闭成功!")

    # 输出全部
    def fetchAll(self, column, table):
        cursor = self.conn.cursor()
        sql = 'select %s from %s;' % (column, table)
        cursor.execute(sql)
        res = cursor.fetchall()
        cursor.close()
        return res

def getmip(nodename):
    db_adddesip = pymysql.connect(host=mysql_addr, port=mysql_port, user=mysql_account, password=mysql_pw, database=mysql_name)
    hostPort = nodename + '%'  # 用于数据库的模糊查询，例如leo11_1
    if 'leo' in hostPort:
        c1 = db_adddesip.cursor()
        c1.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where destport like '%s' AND sourcetype='geo'" % hostPort)
        c1.close()
        leo_links = c1.fetchall()
        c2 = db_adddesip.cursor()
        c2.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where sourceport like '%s' AND desttype='geo'" % hostPort)
        leo_links += c2.fetchall()
        c2.close()

        # use id in link_table1
        c3 = db_adddesip.cursor()
        leo_flow0 = []
        for j in range(len(leo_links)):
            c3.execute(
                "select id,link_id,starttime,endtime from selectflow where link_id=%s and starttime=0" % leo_links[j][
                    0])
            leo_flow0 += c3.fetchall()
        c3.close()

        c4 = db_adddesip.cursor()
        c4.execute(
            "select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where id=%s" %
            leo_flow0[0][1])
        leo_link0 = c4.fetchall()
        c4.close()

        if leo_link0[0][3] == 'geo':
            home_address_ip = leo_link0[0][4]
        else:
            home_address_ip = leo_link0[0][1]
    return home_address_ip

def adddesip():                 #记录数据表中本节点对应的目的节点，存成字典形式
    for i in range(0, len(feature_ping)):
        if feature_ping[i][0] == hostname.strip():
            home_address_ip = getmip(feature_ping[i][2])
            hosts[str(feature_ping[i][2])] = home_address_ip
        else:
            continue


def Edelay(ip, desnode, counter_ping):
    dict = {}
    command_delay = 'ping ' + ip + ' -c 1 | grep from'
    delay_message = os.popen(command_delay).read()
    if delay_message == "":
        print("this package is lost")
        dict['sourceNode'] = hostname.strip()
        dict['desNode'] = desnode
        dict['delay'] = '0'
        dict['collection counter'] = counter_ping
        dict['time'] = float(time.time())
        j = json.dumps(dict)
        # save the data to elasticseearch
        index_name = 'delay'+str(experiment_id)
        es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
        if es.indices.exists(index=index_name):
            result = es.index(index=index_name, doc_type='doc', body=j)
        else:
            es.indices.create(index=index_name, ignore=400)
            result = es.index(index=index_name, doc_type='doc', body=j)  # index可以自动生成id，create要设置id
    else:
        delay = delay_message.split('time=')[1].split()[0]
        nbrnum = str(ip).split('.')[-1]
        dict['sourceNode'] = hostname.strip()
        dict['desNode'] = desnode
        dict['delay'] = delay
        dict['collection counter'] = counter_ping
        dict['time'] = float(time.time())
        j = json.dumps(dict)
        # save the data to elasticseearch
        index_name = 'delay'+str(experiment_id)
        es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
        if es.indices.exists(index=index_name):
            result = es.index(index=index_name, doc_type='doc', body=j)
        else:
            es.indices.create(index=index_name, ignore=400)
            result = es.index(index=index_name, doc_type='doc', body=j)  # index可以自动生成id，create要设置id


def Eloss(ip, desnode, counter_ping):
    dict = {}
    command_loss = 'iperf -c ' + ip + ' -u -t 1 -b 2M -y C | head -n 2 | tail -n 1'
    loss_message = os.popen(command_loss).read()
    if len(loss_message.split(',')) == 9:
        nbrnum = str(ip).split('.')[-1]
        # dict[str((hostnum, nbrnum))] = loss
        dict['sourceNode'] = hostname.strip()
        dict['desNode'] = desnode
        dict['loss'] = '100'
        dict['collection counter'] = counter_ping
        dict['time'] = float(time.time())
        j = json.dumps(dict)
        # save the data to elasticseearch
        index_name = 'loss'+str(experiment_id)
        es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
        if es.indices.exists(index=index_name):
            result = es.index(index=index_name, doc_type='doc', body=j)
        else:
            es.indices.create(index=index_name, ignore=400)
            result = es.index(index=index_name, doc_type='doc', body=j)
    else:
        loss = loss_message.split(',')[12]
        nbrnum = str(ip).split('.')[-1]
        dict['sourceNode'] = hostname.strip()
        dict['desNode'] = desnode
        dict['loss'] = loss
        dict['collection counter'] = counter_ping
        dict['time'] = float(time.time())
        j = json.dumps(dict)
        # save the data to elasticseearch
        index_name = 'loss'+str(experiment_id)
        es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
        if es.indices.exists(index=index_name):
            result = es.index(index=index_name, doc_type='doc', body=j)
        else:
            es.indices.create(index=index_name, ignore=400)
            result = es.index(index=index_name, doc_type='doc', body=j)


def main_v1():
    interval = 10
    adddesip()
    thread_pool = ThreadPoolExecutor(max_workers=2)
    for i in range(0, len(feature_ping)):
        if feature_ping[i][2] == hostname.strip():  # desnode
            os.system('iperf -s -u -B {} &'.format(getmip(feature_ping[i][2])))
            break
        else:
            continue
    for i in range(0, len(feature_ping)):
        if feature_ping[i][0] == hostname.strip():
            while True:
                time_remain = interval - time.time() % interval
                time.sleep(time_remain)
                for desnode, ip in hosts.items():
                    thread_pool.submit(Edelay, ip, desnode, counter_ping)
                    thread_pool.submit(Eloss, ip, desnode, counter_ping)
                global counter_ping
                counter_ping = counter_ping + 1


# next is v2
def PortInThroughput(i, counter):  # portInThroughput and rx.utilization
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur = time.time()
    ifIn_cur = ()
    snmp_query_obj2 = SnmpClass(oid_set=oid_set2)
    ifIn_cur = snmp_query_obj2.snmp_query()
    if (long(ifIn_pre[i]) <= long(ifIn_cur[i])):
        inthroughput = (long(ifIn_cur[i]) - long(ifIn_pre[i])) / (time_cur - time_pre_in)
    else:
        inthroughput = (2 ** 32 - long(ifIn_pre[i]) + long(ifIn_cur[i])) / (time_cur - time_pre_in)
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["inthroughput"] = inthroughput
    dict["time"] = float(time_cur)
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'inthroughput'+str(experiment_id)
    es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)

    ifspeed = 1024 * (10 ** 6)
    dict_rx = {}
    rx_utilization = inthroughput / (ifspeed / 8)
    dict_rx["hostname"] = hostname
    dict_rx["port"] = port
    dict_rx["collection couter"] = counter
    dict_rx["rx_utilization"] = str(rx_utilization * 100) + '%'
    dict_rx["time"] = float(time_cur)
    j_rx = json.dumps(dict_rx)
    index_name_rx = 'rx_utilization'+str(experiment_id)
    if es.indices.exists(index=index_name_rx):
        result = es.index(index=index_name_rx, doc_type='politics', body=j_rx)
    else:
        es.indices.create(index=index_name_rx, ignore=400)
        result = es.index(index=index_name_rx, doc_type='politics', body=j_rx)

    if rx_utilization > 0.9:
        dict_rx_up = {}
        dict_rx_up["hostname"] = hostname
        dict_rx_up["port"] = port
        dict["collection couter"] = counter
        dict_rx_up["rx_utilization"] = str(rx_utilization * 100) + '%'
        dict_rx_up["time"] = float(time_cur)
        j_rx_up = json.dumps(dict_rx_up)
        index_name_rxup = 'rx_up'+str(experiment_id)
        if es.indices.exists(index=index_name_rxup):
            result = es.index(index=index_name_rxup, doc_type='politics', body=j_rx_up)
        else:
            es.indices.create(index=index_name_rxup, ignore=400)
            result = es.index(index=index_name_rxup, doc_type='politics', body=j_rx_up)

    global time_pre_in
    global ifIn_pre
    time_pre_in = time_cur
    ifIn_pre = ifIn_cur


def PortOutThroughput(i, counter):  # portOutThroughput and tx.utilization
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur = time.time()
    ifOut_cur = ()
    snmp_query_obj3 = SnmpClass(oid_set=oid_set3)
    ifOut_cur = snmp_query_obj3.snmp_query()
    if (long(ifOut_pre[i]) <= long(ifOut_cur[i])):
        outthroughput = (long(ifOut_cur[i]) - long(ifOut_pre[i])) / (time_cur - time_pre_out)
    else:
        outthroughput = (2 ** 32 - long(ifOut_pre[i]) + long(ifOut_cur[i])) / (time_cur - time_pre_out)
    # dict[str((hostnum,port))] = outthroughput
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["outthroughput"] = outthroughput
    dict["time"] = float(time_cur)
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'outthroughput'+str(experiment_id)
    es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)

    ifspeed = 10 ** 9
    dict_tx = {}
    tx_utilization = outthroughput / (ifspeed / 8)
    # dict_tx[str((hostnum,port))] = str(tx_utilization*100)+'%'
    dict_tx["hostname"] = hostname
    dict_tx["port"] = port
    dict_tx["collection couter"] = counter
    dict_tx["tx_utilization"] = str(tx_utilization * 100) + '%'
    dict_tx["time"] = time_cur
    j_tx = json.dumps(dict_tx)
    index_name_tx = 'tx_utilization'+str(experiment_id)
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
        dict_tx_up["counter"] = counter
        j_tx_up = json.dumps(dict_tx_up)
        index_name_txup = 'tx_up'+str(experiment_id)
        if es.indices.exists(index=index_name_txup):
            result = es.index(index=index_name_txup, doc_type='politics', body=j_tx_up)
        else:
            es.indices.create(index=index_name_txup, ignore=400)
            result = es.index(index=index_name_txup, doc_type='politics', body=j_tx_up)

    global time_pre_out
    global ifOut_pre
    time_pre_out = time_cur
    ifOut_pre = ifOut_cur


def PortifInDiscards(i, counter):
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur = time.time()
    ifIndis_cur = ()
    snmp_query_obj5 = SnmpClass(oid_set=oid_set5)
    ifIndis_cur = snmp_query_obj5.snmp_query()
    indiscards = (int(ifIndis_cur[i]) - int(ifIndis_pre[i])) / (time_cur - time_pre_indis)
    dict["hostname"] = hostname.strip()
    dict["port"] = port
    dict["collection couter"] = counter
    dict["indiscards"] = indiscards
    dict["time"] = time_cur
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'indiscards'+str(experiment_id)
    es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    global time_pre_indis
    global ifIndis_pre
    time_pre_indis = time_cur
    ifIndis_pre = ifIndis_cur


def PortifOutDiscards(i, counter):
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur = time.time()
    ifOutdis_cur = ()
    snmp_query_obj6 = SnmpClass(oid_set=oid_set6)
    ifOutdis_cur = snmp_query_obj6.snmp_query()
    outdiscards = (int(ifOutdis_cur[i]) - int(ifOutdis_pre[i])) / (time_cur - time_pre_outdis)
    # dict[str((hostnum,port))] = str(outdiscards*100)+'%'
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["outdiscards"] = outdiscards
    dict["time"] = time_cur
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'outdiscards'+str(experiment_id)
    es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    global time_pre_outdis
    global ifOutdis_pre
    time_pre_outdis = time_cur
    ifOutdis_pre = ifOutdis_cur


def PortifInErrors(i, counter):
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur = time.time()
    ifInerr_cur = ()
    snmp_query_obj7 = SnmpClass(oid_set=oid_set7)
    ifInerr_cur = snmp_query_obj7.snmp_query()
    inerror = (int(ifInerr_cur[i]) - int(ifInerr_pre[i])) / (time_cur - time_pre_inerr)
    # dict[str((hostnum,port))] = str(inerror*100)+'%'
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["inerror"] = str(inerror * 100) + '%'
    dict["time"] = time_cur
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'inerrors'+str(experiment_id)
    es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    # print(result)
    global time_pre_inerr
    global ifInerr_pre
    time_pre_inerr = time_cur
    ifInerr_pre = ifInerr_cur


def PortifOutErrors(i, counter):
    dict = {}
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    port = if_num[i]
    time_cur = time.time()
    ifOuterr_cur = ()
    snmp_query_obj8 = SnmpClass(oid_set=oid_set8)
    ifOuterr_cur = snmp_query_obj8.snmp_query()
    outerror = (int(ifOuterr_cur[i]) - int(ifOuterr_pre[i])) / (time_cur - time_pre_outerr)
    dict["hostname"] = hostname
    dict["port"] = port
    dict["collection couter"] = counter
    dict["outerror"] = str(outerror * 100) + '%'
    dict["time"] = time_cur
    j = json.dumps(dict)
    # save the data to elasticseearch
    index_name = 'outerrors'+str(experiment_id)
    es = Elasticsearch(es_addr, http_auth=('elastic', 'password'), port=es_port)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='politics', body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='politics', body=j)
    global time_pre_outerr
    global ifOuterr_pre
    time_pre_outerr = time_cur
    ifOuterr_pre = ifOuterr_cur


def main_v2(counter):
    snmp_query_obj1 = SnmpClass(oid_set=oid_set1)
    snmp_query_obj2 = SnmpClass(oid_set=oid_set2)
    snmp_query_obj3 = SnmpClass(oid_set=oid_set3)
    snmp_query_obj4 = SnmpClass(oid_set=oid_set4)
    if_num = snmp_query_obj4.snmp_query()
    ip_nbr = snmp_query_obj1.snmp_query()

    thread_pool = ThreadPoolExecutor(max_workers=6)
    for i in range(0, len(if_num)):
        if hostname.strip() in if_num[i]:
            thread_pool.submit(PortInThroughput, i, counter)
            thread_pool.submit(PortOutThroughput, i, counter)
            thread_pool.submit(PortifInDiscards, i, counter)
            thread_pool.submit(PortifOutDiscards, i, counter)
            thread_pool.submit(PortifInErrors, i, counter)
            thread_pool.submit(PortifOutErrors, i, counter)
        else:
            continue


def func_snmp():
    interval = 10

    while True:
        time_remain = interval - time.time() % interval
        #  print("sleep %f seconds", time_remain)
        time.sleep(time_remain)
        main_v2(counter)
        global counter
        counter = counter + 1


#next is tc
#tc第一行
def write_begin_tc():
    tc_file = open("tc.sh", "w")
    tc_file.write('#!/bin/bash\n')
    tc_file.close()

# 追加写一行文件
def write_add_tc(str_add):
    tc_file = open("tc.sh", "a")
    tc_file.write(str_add)
    tc_file.close()

#del only eth
def write_del_eth(num,localname):
    tc_file = open("tc.sh", "a")
    for i in range(num):
        tc_file.write('tc qdisc del dev '+localname+'_' + str(i) + ' root\n')
    tc_file.close()

#add only eth
def write_add_eth(num,localname):
    tc_file = open("tc.sh", "a")
    for i in range(num):
        tc_file.write('tc qdisc add dev '+localname+'_' + str(i) + ' root handle 1: htb\n')
        tc_file.write('tc class add dev '+localname+'_' + str(i) + ' parent 1: classid 1:10 htb rate 1gbit ceil 1gbit\n')
        tc_file.write('tc filter add dev '+localname+'_' + str(i) + ' protocol ip parent 1:0 prio 1 u32 match ip dst 0.0.0.0/0 flowid 1:10\n')
        tc_file.write('tc qdisc add dev '+localname+'_' + str(i) + ' parent 1:10 netem delay 0ms limit 10000000\n')
         
    tc_file.close()


def str_change_eth(port, delay, packetloss, localname):
    if float(packetloss) == 0:
        str1 = 'tc qdisc replace dev '+localname+'_' + port \
               + ' parent 1:10 netem delay ' + delay + 'ms' \
               + ' limit 10000000' + '\n'
    else:
        loss = str(float(packetloss) * 100) + '%'
        str1 = 'tc qdisc replace dev '+localname+'_' + port \
               + ' parent 1:10 netem delay ' + delay + 'ms' \
               + ' loss ' + loss+ ' limit 10000000' + '\n'
    return str1

def str_change_eth_geo(port, delay, packetloss, localname):
    str1 = 'tc qdisc add dev '+localname+'_'+ port + ' root handle 1: htb\n'
    str2 = 'tc class add dev '+localname+'_'+ port + ' parent 1: classid 1:10 htb rate 1gbit ceil 1gbit\n'
    str4 = 'tc filter add dev '+localname+'_'+port+' protocol ip parent 1:0 prio 1 u32 match ip dst 0.0.0.0/0 flowid 1:10\n'
    if float(packetloss) == 0:
        str3 = 'tc qdisc replace dev '+localname+'_' + port \
               + ' parent 1:10 netem delay ' + delay + 'ms' \
               + ' limit 10000000' + '\n'
    else:
        loss = str(float(packetloss) * 100) + '%'
        str3 = 'tc qdisc replace dev '+localname+'_' + port \
               + ' parent 1:10 netem delay ' + delay + 'ms' \
               + ' loss ' + loss + ' limit 10000000' + '\n'
    return str1+str2+str3+str4

def str_eth_add_geo1(port, delay, packetloss,destip,flag,localname):
    str1 = 'tc qdisc add dev '+localname+'_'+ port + ' root handle 1: htb\n'
    return str1

def str_eth_add_geo2(port, delay, packetloss,destip,flag,localname):
    str2 = 'tc class add dev '+localname+'_'+ port + ' parent 1: classid 1:'+flag+' htb rate 1gbit ceil 1gbit\n'
    str4 = 'tc filter add dev '+localname+'_'+port+' protocol ip parent 1:0 prio 1 u32 match ip dst '+destip+'/32 flowid 1:'+flag+'\n'

    if float(packetloss) == 0:
        str3 = 'tc qdisc replace dev '+localname+'_' + port + ' parent 1:' + flag + ' netem delay ' + delay + 'ms limit 10000000\n'
    else:
        loss = str(float(packetloss) * 100) + '%'
        str3 = 'tc qdisc replace dev '+localname+'_' + port + ' parent 1:' + flag + ' netem delay ' + delay + 'ms' + ' loss ' + loss + ' limit 10000000\n'
    return str2+str3+str4


def func_tc():
    # 获取当前节点的名字
    localname = str(commands.getoutput('hostname'))
    #localname ='geo1'

    # 连接数据库
    mysql.connect()
    feature_tc = mysql.fetchAll("sourceport,destport,destip,delaytime,packetlossrate,time", 'linkfeature_table')
    #    sourceport,destport,destip,delaytime,packetlossrate,time:int

    # 定义res取出的所需要的行
    # res表示遍历完feature_tc后，所有的节点名一样，端口不一样的数据
    res = []
    for i in range(len(feature_tc)):
        sourceport = feature_tc[i][0].split('_')
        if sourceport[0] == localname:
            temp = list(feature_tc[i]) + sourceport
            res.append(temp)

    # 根据res的time进行排序，res_sort表示需要的数据按照time排序后
    # res的格式如下：sourceport,destport,destip,delaytime,packetlossrate,time,source,port
    res_sort = sorted(res, key=(lambda x: x[5]))

    #leo设置出端tc
    if localname[0:3] != 'geo':
        # 遍历看一下多少个端口
        maxport = 0
        for i in range(len(res_sort)):
            if maxport < int(res_sort[i][7]):
                maxport = int(res_sort[i][7])

        write_begin_tc()
        write_del_eth(int(maxport) + 1, localname)
        write_add_eth(int(maxport) + 1, localname)

        delta_time = '60'
        row_tc = 0
        rows = len(res_sort)
        while row_tc < rows - 1:
            tc_array = []
            while True:
                tc_array.append(res_sort[row_tc])
                for i in range(row_tc, rows - 1):
                    if res_sort[i][5] == res_sort[i + 1][5]:
                        tc_array.append(res_sort[i + 1])
                        if i == rows - 2:
                            tc_array.pop()
                            row_tc = rows - 1
                            delta_time = '0'
                    else:
                        row_tc = i + 1
                        delta_time = str(res_sort[i + 1][5] - res_sort[i][5])
                        break
                break

            for j in range(len(tc_array)):
                portj = str(tc_array[j][7])
                delayj = str(tc_array[j][3])
                packetlossj = str(tc_array[j][4])
                write_add_tc(str_change_eth(portj, delayj, packetlossj, localname))
            write_add_tc('sleep ' + delta_time + 's\n')

        # 最后一行，最后一个时刻
        portj = str(res_sort[row_tc][7])
        delayj = str(res_sort[row_tc][3])
        packetlossj = str(res_sort[row_tc][4])
        write_add_tc(str_change_eth(portj, delayj, packetlossj, localname))
        write_add_tc('sleep 60s\n')

        write_del_eth(int(maxport) + 1, localname)

    else:
        write_begin_tc()
        write_del_eth(3, localname)

        delta_time = '60'
        row = 0
        rows = len(res_sort)
        num = 0
        flag = 10
        while row < rows-1:
            tc_array = []
            while True:
                tc_array.append(res_sort[row])
                for i in range(row, rows-1):
                    if res_sort[i][5] == res_sort[i+1][5]:
                        tc_array.append(res_sort[i+1])
                        if i == rows-2:
                            tc_array.pop()
                            row = rows-1
                            delta_time = '0'
                    else:
                        row = i+1
                        delta_time = str(res_sort[i+1][5]-res_sort[i][5])
                        break
                break

            num = 0  # 同一个geo，只开启一次
            flag = 10
            write_del_eth(3, localname)
            for j in range(len(tc_array)):
                if tc_array[j][1][0:3] == 'geo':
                    portj = str(tc_array[j][7])
                    delayj = str(tc_array[j][3])
                    packetlossj = str(tc_array[j][4])
                    write_add_tc(str_change_eth_geo(portj, delayj, packetlossj, localname))
                else:
                    portj = str(tc_array[j][7])
                    delayj = str(tc_array[j][3])
                    packetlossj = str(tc_array[j][4])
                    destipj = str(tc_array[j][2])
                    flagj = str(flag)
                    if num == 0:
                        write_add_tc(str_eth_add_geo1(portj, delayj, packetlossj, destipj, flagj, localname))
                        num = 1
                    write_add_tc(str_eth_add_geo2(portj, delayj, packetlossj, destipj, flagj, localname))
                    flag += 10
            write_add_tc('sleep ' + delta_time + 's\n')

        # 最后一行
        if res_sort[row][5] != res_sort[row - 1][5]:
            write_del_eth(3, localname)
            num = 0
            flag = 10

        if res_sort[row][1][0:3] == 'geo':
            portj = str(res_sort[row][7])
            delayj = str(res_sort[row][3])
            packetlossj = str(res_sort[row][4])
            write_add_tc(str_change_eth_geo(portj, delayj, packetlossj, localname))
        else:
            portj = str(res_sort[row][7])
            delayj = str(res_sort[row][3])
            packetlossj = str(res_sort[row][4])
            destipj = str(res_sort[row][2])
            flagj = str(flag)
            if num == 0:
                write_add_tc(str_eth_add_geo1(portj, delayj, packetlossj, destipj, flagj, localname))
                num = 1
            write_add_tc(str_eth_add_geo2(portj, delayj, packetlossj, destipj, flagj, localname))
        write_add_tc('sleep 60s\n')

        write_del_eth(3, localname)

    while True:
        os.system('chmod 777 /tc.sh')
        os.system('./tc.sh')


def mk_cfg():
    p = os.popen("hostname")
    line = p.readline()
    hostname = line.strip()
    hostname = hostname + '%'
    #print(hostname)

    db1 = pymysql.connect(host=mysql_addr, port=mysql_port, user=mysql_account, password=mysql_pw, database=mysql_name)
    if 'leo' in hostname:
        c1 = db1.cursor()
        c1.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where destport like '%s' AND sourcetype='geo'" % hostname)
        leo_links = c1.fetchall()
        c1.close()
        c2 = db1.cursor()
        c2.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where sourceport like '%s' AND desttype='geo'" % hostname)
        c2.close()
        leo_links += c2.fetchall()

        # use id in link_table1
        c3 = db1.cursor()
        leo_flow0 = []
        for i in range(len(leo_links)):
            c3.execute("select id,link_id,starttime,endtime from selectflow where link_id=%s and starttime=0" % leo_links[i][0])
            leo_flow0 += c3.fetchall()
        c3.close()

        c4 = db1.cursor()
        c4.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where id=%s" % leo_flow0[0][1])
        leo_link0 = c4.fetchall()
        c4.close()

        if leo_link0[0][3] == 'geo':
            home_agent_ip = leo_link0[0][1]
        else:
            home_agent_ip = leo_link0[0][4]

        if leo_link0[0][3] == 'geo':
            home_address_ip = leo_link0[0][4]
        else:
            home_address_ip = leo_link0[0][1]

        if_gw_table = {}
        for i in range(len(leo_links)):
            if leo_links[i][3] == 'geo':
                if_gw_table[leo_links[i][5]] = leo_links[i][1]
            else:
                if_gw_table[leo_links[i][2]] = leo_links[i][4]

        CONFIG_FILE = "mn.cfg"

        spi = 256
        key = 1234567812345678
        home_agent = home_agent_ip
        home_address = home_address_ip
        if_gateways = if_gw_table

        conf = ConfigParser.ConfigParser()

        cfgfile = open(CONFIG_FILE, 'w')

        conf.add_section("MobileNodeAgent")

        conf.set("MobileNodeAgent", "SPI", spi)
        conf.set("MobileNodeAgent", "KEY", key)
        conf.set("MobileNodeAgent", "HOME_AGENT", home_agent)
        conf.set("MobileNodeAgent", "HOME_ADDRESS", home_address)
        conf.set("MobileNodeAgent", "IF_GATEWAYS", if_gateways)

        conf.write(cfgfile)
        cfgfile.close()
        os.system('sysctl net.ipv4.conf.all.rp_filter=2')

    else:
        c5 = db1.cursor()
        c5.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where destport like '%s' AND sourcetype='leo'" % hostname)
        geo_links = c5.fetchall()
        c5.close()
        c6 = db1.cursor()
        c6.execute("select id,sourceip,sourceport,sourcetype,destip,destport,desttype from selectlink where sourceport like '%s' AND desttype='leo'" % hostname)
        geo_links += c6.fetchall()
        c6.close()

        for i in range(len(geo_links)):
            if geo_links[i][3] == 'geo':
                address_ip = geo_links[i][1]
            else:
                address_ip = geo_links[i][4]
            # creat ha.cfg
        CONFIG_FILE = "ha.cfg"
        address = address_ip
        auth_table = {256: "1234567812345678"}
        conf = ConfigParser.ConfigParser()

        cfgfile = open(CONFIG_FILE, 'w')

        conf.add_section("HomeAgent")

        conf.set("HomeAgent", "ADDRESS", address)
        conf.set("HomeAgent", "AUTH_TABLE", auth_table)
        conf.write(cfgfile)

        cfgfile.close()
        os.system('sysctl net.ipv4.conf.all.rp_filter=2')
        os.system('nohup python /home/MobileIP-master/home_agent.py /ha.cfg &')



def mk_sh():
    mysql_sh = MYSQL(mysql_addr, mysql_account, mysql_pw, mysql_name, mysql_port)
    mysql_sh.connect()
    res_flow = mysql_sh.fetchAll("link_id,starttime,endtime", "selectflow")
    res_link = mysql_sh.fetchAll("id,sourceip,destip,sourceport,destport", "selectlink")


    p = os.popen("hostname")
    line = p.readline()
    hostname=line.strip()
    if 'leo' in hostname:
        hostname1=hostname+'%'
        hostname=hostname.lower()
        #print('%s'%hostname)
        #修改


        sp=[]
        dp=[]
        for i  in range(len(res_link)):
            sourceport=str(res_link[i][3]).split('_')
            destport=str(res_link[i][4]).split('_')
            sp.append(sourceport[0])
            dp.append(destport[0])

        link=[]
        for i in range(len(res_link)):
        #    test=re.compile('%s+'%hostname)

            if(hostname == sp[i] or hostname== dp[i]):
                link.append(res_link[i])

        link.sort()

        flow=[]
        for m in range(len(res_flow)):
            for n in range(len(link)):
                if(res_flow[m][0]==link[n][0]):
                    flow.append(res_flow[m])

        flow=list(set(flow))
        for i in range(len(flow)):
            flow[i]=list(flow[i])

        for i in range(len(flow)):
            flow[i][1]=int(flow[i][1])

        flow.sort(key=(lambda x:x[1]))

        #print(flow)


        link_dic=dict()
        for i in range(len(link)):
            link_dic[link[i][0]]=link[i][1:]

        f = open("leo_route.sh", "w")
        f.write("ip route | awk '{print $1}' | while read line; do ip route del $line; done ")
        f.write("\n")
        command_geteth0 = 'ifconfig eth0 | grep \'inet\' | sed \'s/^.*inet//g\' | sed \'s/netmask.*$//g\''
        eth0_ip =os.popen(command_geteth0).read()
        f.write("route add -host 114.212.112.36 gw {}".format(eth0_ip))
        f.write("\n")        

        f.write("while true \n")
        f.write("do\n")

        #f.write("cd /home/MobileIP-master \n")
        f.write("nohup python /home/MobileIP-master/mn_agent.py start /mn.cfg & \n")

        gw=[]
        for k in range(len(flow)):
            gw.append(link_dic[flow[k][0]])

            f.write("route add -net 10.0.0.0/16 gw "+gw[0][0]+"\n" )
            f.write("route add -net 10.0.0.0/16 gw "+gw[0][1]+"\n" )
            f.write("\n")
            #f.write("cd /home/MobileIP-master \n")
            f.write("python /home/MobileIP-master/"
                    "mn_agent.py register " + gw[0][2] + "\n")
            f.write("sleep "+str(int(flow[k][2])-int(flow[k][1]))+"\n")
            f.write("\n")
            f.write("route del -net 10.0.0.0/16\n")
            f.write("route del -net 10.0.0.0/16\n")
            f.write("\n")
            del gw[:]

        f.write("done\n")
        f.close()
        while True:
            os.system('chmod 777 leo_route.sh')
            os.system('./leo_route.sh')
    else:
        return


if __name__ == '__main__':
    hostname = os.popen('echo $HOSTNAME').read()
    hostnum = re.findall('\d+', hostname)[0]
    mysql = MYSQL(mysql_addr, mysql_account, mysql_pw, mysql_name, mysql_port)
    #mysql.connect()
    #feature_ping = mysql.fetchAll("source_node_name,source_node_ip,dest_node_name,dest_node_name", 'test_link_selection')

    #选择本次实验id所对应的数据
    try:
        db = pymysql.connect(host=mysql_addr, port=mysql_port, user=mysql_account, password=mysql_pw, database=mysql_name)
    except pymysql.Error as e:
        print("fail to connect mysql" + str(e))
    cur = db.cursor()
    select_command = 'select source_node_name,source_node_ip,dest_node_name,dest_node_ip from test_link_selection where find_in_set('+str(experiment_id) +', experiment_id)'
    select = cur.execute(select_command)
    feature_ping = cur.fetchall()

    #睡眠直至实验开始时间
    while True:
        try:
            db = pymysql.connect(host=mysql_addr, port=mysql_port, user=mysql_account, password=mysql_pw, database=mysql_name)
        except pymysql.Error as e:
            print("fail to connect mysql" + str(e))
        cur = db.cursor()
        #selecttime = cur.execute("SELECT realstarttime FROM experiment ORDER BY realstarttime DESC LIMIT 0,1")
        select_time_command = 'SELECT realstarttime FROM experiment where find_in_set('+str(experiment_id) +', id)'
        selecttime = cur.execute(select_time_command)
        results_starttime = cur.fetchall()
        for row in results_starttime:
            time_start = row[0]
        if (float(time_start) < time.time()*1000):
            time.sleep(1)
        else:
            db.close()
            break
    print(time_start)
    time_cur = time.time()
    time_sleep = (float(time_start)/1000) - time_cur
    time.sleep(time_sleep)


    # preInThroughput
    time_pre_in = time.time()
    snmp_query_obj2 = SnmpClass(oid_set=oid_set2)
    ifIn_pre = snmp_query_obj2.snmp_query()

    # preOutThroughput
    time_pre_out = time.time()
    snmp_query_obj3 = SnmpClass(oid_set=oid_set3)
    ifOut_pre = snmp_query_obj3.snmp_query()

    # preifInDiscards
    time_pre_indis = time.time()
    snmp_query_obj5 = SnmpClass(oid_set=oid_set5)
    ifIndis_pre = snmp_query_obj5.snmp_query()

    # preifOutDiscards
    time_pre_outdis = time.time()
    snmp_query_obj6 = SnmpClass(oid_set=oid_set6)
    ifOutdis_pre = snmp_query_obj6.snmp_query()

    # preifInErrors
    time_pre_inerr = time.time()
    snmp_query_obj7 = SnmpClass(oid_set=oid_set7)
    ifInerr_pre = snmp_query_obj7.snmp_query()

    # preifOutErrors
    time_pre_outerr = time.time()
    snmp_query_obj8 = SnmpClass(oid_set=oid_set8)
    ifOuterr_pre = snmp_query_obj8.snmp_query()

    threads = []
    threads.append(threading.Thread(target=main_v1))
    threads.append(threading.Thread(target=func_snmp))
    threads.append(threading.Thread(target=func_tc))
    threads.append(threading.Thread(target=mk_cfg))
    threads.append(threading.Thread(target=mk_sh))
    for t in threads:
        print(t)
        t.start()