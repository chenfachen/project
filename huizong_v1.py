# coding:utf-8
import threading
import time
import netsnmp
import os
import Queue
import json
import re
import pymysql
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor

#next is v2
import collections
from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

#next is tc
import commands

hosts = []

#next is v2
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

class MYSQL:
    def __init__(self, host, user, password, database, charset="utf8"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.conn = None

    # 连接数据库
    def connect(self):
        self.conn = pymysql.connect(host=self.host,
                                    user=self.user,
                                    password=self.password,
                                    database=self.database,
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

def adddesip():
    mysql = MYSQL('114.212.112.36', 'root', '123456', 'communication')
    mysql.connect()
    feature = mysql.fetchAll("sourceport,sourceip,destport,destip", 'ping')
    for i in range(0, len(feature)):
        if feature[i][0] == hostname.strip():
            hosts.append(str(feature[i][3]))
        else:
            continue

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
        index_name=hostname.strip()+'-delay'
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
    index_name=hostname.strip()+'-loss'
    es = Elasticsearch("114.212.112.36", http_auth=('elastic', 'password'), port=9206)
    if es.indices.exists(index=index_name):
        result = es.index(index=index_name, doc_type='doc', body=j)
        #result = es.create(index=index_name, doc_type='politics', id=str(hostnum)+str(":")+str(i), body=j)
    else:
        es.indices.create(index=index_name, ignore=400)
        result = es.index(index=index_name, doc_type='doc', body=j)
        #result = es.create(index=index_name, doc_type='politics', id=str(hostnum)+str(":")+str(i), body=j)
    print(result)

def main_v1():
    mysql = MYSQL('114.212.112.36', 'root', '123456', 'communication')
    mysql.connect()
    feature = mysql.fetchAll("sourceport,sourceip,destport,destip", 'ping')
    for i in range(0, len(feature)):
        if feature[i][2] == hostname.strip():       #desnode
            os.system('iperf -s -u -B {} &'.format(feature[i][3]))
            break
        else:
            continue
    for i in range(0,len(feature)):
        if feature[i][0] == hostname.strip():
            while True:
                for ip in hosts:
                    thread_pool.submit(Edelay, ip)
                    thread_pool.submit(Eloss, ip)

def func_ping():
    thread_pool = ThreadPoolExecutor(max_workers=2)
    hostname = os.popen('echo $HOSTNAME').read()
    hostnum = re.findall('\d+',hostname)[0]
    adddesip()
    main_v1()

#next is v2
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



def main_v2(counter):
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

    thread_pool = ThreadPoolExecutor(max_workers=6)
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

def func_snmp():
    # start = time.time()

    '''try:
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
    time.sleep(time_sleep)'''

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
        time_remain = interval - time.time() % interval
        #  print("sleep %f seconds", time_remain)
        time.sleep(time_remain)
        main_v2(counter)
        global  counter
        counter = counter + 1

    # end = time.time()
    # print('Running time: %s Seconds' % (end - start))

#next is tc
# 写入脚本前几行语句初始化，加入 eth 和ifb
def write_front(num):
    tc_file = open("tc.sh", "w")
    tc_file.write('#!/bin/bash\n')
    for i in range(num):
        tc_file.write('tc qdisc add dev eth' + str(i) + ' root handle 1:0 netem delay 0ms limit 2700000\n')
        tc_file.write('tc qdisc add dev eth' + str(i) + ' parent 1:1 handle 10: tbf rate 1gbit burst 1600000000 limit 3000000000\n')
    tc_file.close()

def write_front_geo():
    tc_file = open("tc.sh", "w")
    tc_file.write('#!/bin/bash\n')
    tc_file.close()

# 写入脚本最后几行语句，删除 eth 和ifb
def write_behind(num):
    tc_file = open("tc.sh", "a")
    for i in range(num):
        tc_file.write('tc qdisc del dev eth' + str(i) + ' root\n')
    tc_file.close()

# 追加写一行文件
def write_add(str_add):
    tc_file = open("tc.sh", "a")
    tc_file.write(str_add)
    tc_file.close()

# 改变tc命令的字符串，输入均为str数据
# port:表示端口，delay：单位为ms，packetloss：默认为小数，如0.01，表示1%
# eg:tc qdisc change dev eth0 root handle 1:0 netem delay 100ms loss 1% limit 2700000
def str_eth_add(port, delay, packetloss):
#    if float(packetloss) <= 0.0000000003:
    if float(packetloss) <= 0.0000015:
        str1 = 'tc qdisc add dev eth' + port \
               + ' root handle 1:0 netem delay ' + delay + 'ms' \
               + ' limit 2700000' + '\n'
    else:
        loss = str(float(packetloss) * 100) + '%'
        str1 = 'tc qdisc add dev eth' + port \
               + ' root handle 1:0 netem delay ' + delay + 'ms' \
               + ' loss ' + loss + ' limit 2700000' + '\n'
    return str1

def str_eth_change(port, delay, packetloss):
    #    if float(packetloss) <= 0.0000000003:
    if float(packetloss) <= 0.0000015:
        str1 = 'tc qdisc change dev eth' + port \
               + ' root handle 1:0 netem delay ' + delay + 'ms' \
               + ' limit 2700000' + '\n'
    else:
        loss = str(float(packetloss) * 100) + '%'
        str1 = 'tc qdisc change dev eth' + port \
               + ' root handle 1:0 netem delay ' + delay + 'ms' \
               + ' loss ' + loss + ' limit 2700000' + '\n'
    return str1

def str_eth_add_geo1(port, delay, packetloss,destip,flag):
    str1 = 'tc qdisc add dev eth'+ port + ' root handle 1: htb\n'
    return str1

def str_eth_add_geo2(port, delay, packetloss,destip,flag):
    str2 = 'tc class add dev eth'+ port + ' parent 1: classid 1:'+flag+' htb rate 200Mbit ceil 200Mbit\n'
    str4 = 'tc filter add dev eth'+port+' protocol ip parent 1:0 prio 1 u32 match ip dst '+destip+'/32 flowid 1:'+flag+'\n'
    #    if float(packetloss) <= 0.0000000003:
    if float(packetloss) <= 0.0000015:
        str3 = 'tc qdisc add dev eth' + port + ' parent 1:' + flag + ' netem delay ' + delay + 'ms limit 2700000\n'
    else:
        loss = str(float(packetloss) * 100) + '%'
        str3 = 'tc qdisc add dev eth' + port + ' parent 1:' + flag + ' netem delay ' + delay + 'ms loss ' + loss + ' limit 2700000\n'
    return str2+str3+str4

def func_tc():
    # 获取当前节点的名字
    localname = str(commands.getoutput('hostname'))
    # localname = 'leo1'

    # 连接数据库
    mysql = MYSQL('114.212.112.36', 'root', '123456', 'communication')
    mysql.connect()
    feature = mysql.fetchAll("sourceport,destport,destip,delaytime,packetlossrate,time", 'linkfeature_table')
    #    sourceport,destport,destip:vchar,delaytime:double,packetlossrate:double,time:int
    #    print(feature)

    # 定义res取出的所需要的行
    # res表示遍历完feature后，所有的节点名一样，端口不一样的数据
    res = []
    for i in range(len(feature)):
        sourceport = feature[i][0].split('_')
        if sourceport[0] == localname:
            temp = list(feature[i]) + sourceport
            res.append(temp)

    # 根据res的time进行排序，res_sort表示需要的数据按照time排序后
    # res的格式如下：
    # sourceport,destport,destip,delaytime,packetlossrate,time,source,port
    res_sort = sorted(res, key=(lambda x: x[5]))

    if localname[0] != 'g':
        # 遍历看一下多少个端口
        maxport = 0
        for i in range(len(res_sort)):
            if maxport < int(res_sort[i][7]):
                maxport = int(res_sort[i][7])
        # leo开始写脚本
        write_front(int(maxport) + 1)
        delta_time = '60'
        row = 0
        rows = len(res_sort)
        while row < rows - 1:
            tc_array = []
            while True:
                tc_array.append(res_sort[row])
                for i in range(row, rows - 1):
                    if res_sort[i][5] == res_sort[i + 1][5]:
                        tc_array.append(res_sort[i + 1])
                        if i == rows - 2:
                            tc_array.pop()
                            row = rows - 1
                            delta_time = '0'
                    else:
                        row = i + 1
                        delta_time = str(res_sort[i + 1][5] - res_sort[i][5])
                        break
                break
            # print(tc_array)
            for j in range(len(tc_array)):
                portj = str(tc_array[j][7])
                delayj = str(tc_array[j][3])
                packetlossj = str(tc_array[j][4])
                write_add(str_eth_change(portj, delayj, packetlossj))
            write_add('sleep ' + delta_time + 's\n')

        # 最后一行，最后一个时刻
        portj = str(res_sort[row][7])
        delayj = str(res_sort[row][3])
        packetlossj = str(res_sort[row][4])
        write_add(str_eth_change(portj, delayj, packetlossj))
        write_add('sleep 60s\n')

        # 脚本最后清除tc设置
        write_behind(int(maxport) + 1)

    else:
        # geo写脚本
        write_front_geo()
        delta_time = '60'
        row = 0
        rows = len(res_sort)
        num = 0
        flag = 10
        while row < rows - 1:
            tc_array = []
            while True:
                tc_array.append(res_sort[row])
                for i in range(row, rows - 1):
                    if res_sort[i][5] == res_sort[i + 1][5]:
                        tc_array.append(res_sort[i + 1])
                        if i == rows - 2:
                            tc_array.pop()
                            row = rows - 1
                            delta_time = '0'
                    else:
                        row = i + 1
                        delta_time = str(res_sort[i + 1][5] - res_sort[i][5])
                        break
                break
            # print(tc_array)
            num = 0  # 同一个geo，只开启一次
            flag = 10
            write_behind(3)
            for j in range(len(tc_array)):
                if tc_array[j][1][0] == 'g':
                    portj = str(tc_array[j][7])
                    delayj = str(tc_array[j][3])
                    packetlossj = str(tc_array[j][4])
                    write_add(str_eth_add(portj, delayj, packetlossj))
                else:
                    portj = str(tc_array[j][7])
                    delayj = str(tc_array[j][3])
                    packetlossj = str(tc_array[j][4])
                    destipj = str(tc_array[j][2])
                    flagj = str(flag)
                    if num == 0:
                        write_add(str_eth_add_geo1(portj, delayj, packetlossj, destipj, flagj))
                        num = 1
                    write_add(str_eth_add_geo2(portj, delayj, packetlossj, destipj, flagj))
                    flag += 10
            write_add('sleep ' + delta_time + 's\n')

        # 最后一行
        if res_sort[row][5] != res_sort[row - 1][5]:
            write_behind(3)
            num = 0
            flag = 10

        if res_sort[row][1][0] == 'g':
            portj = str(res_sort[row][7])
            delayj = str(res_sort[row][3])
            packetlossj = str(res_sort[row][4])
            write_add(str_eth_add(portj, delayj, packetlossj))
        else:
            portj = str(res_sort[row][7])
            delayj = str(res_sort[row][3])
            packetlossj = str(res_sort[row][4])
            destipj = str(res_sort[row][2])
            flagj = str(flag)
            if num == 0:
                write_add(str_eth_add_geo1(portj, delayj, packetlossj, destipj, flagj))
                num = 1
            write_add(str_eth_add_geo2(portj, delayj, packetlossj, destipj, flagj))
        write_add('sleep 60s\n')
        write_behind(3)

    mysql.disconnect()

if __name__ == '__main__':
    hostname = os.popen('echo $HOSTNAME').read()
    hostnum = re.findall('\d+', hostname)[0]
    threads = []
    threads.append(threading.Thread(target=func_ping))
    threads.append(threading.Thread(target=func_snmp))
    threads.append(threading.Thread(target=func_tc))
    for t in threads:
        print(t)
        t.start()