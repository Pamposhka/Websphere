import logging
import pymqi
import sys
import socket
import time
import os
import os.path

currentDate = time.strftime('%d')
currentMonth = time.strftime('%m')
currentYear = time.strftime('%Y')
logDate = currentDate + '.' + currentMonth + '.' + currentYear

try:
    os.makedirs('D:/IBM/AppServer_EPS/profiles/AppSrv01/logs')
except:
    logFile = "D:/IBM/AppServer_EPS/profiles/AppSrv01/logs/PrepareNT_" + logDate + ".log"

try:
    logging.basicConfig(filename=logFile, filemode='a', level=logging.DEBUG, format = '%(asctime)s %(levelname)s %(message)s')
except:
    logging.basicConfig(filename=logFile, filemode='w', level=logging.DEBUG, format = '%(asctime)s %(levelname)s %(message)s')

queueManagerList = sys.argv[1].split(',')
channelList = sys.argv[2].split(',')

for queue_manager in queueManagerList:
    queue_manager = ' ' + queue_manager + ' '
    queue_manager = queue_manager.replace( ' ', '')
    for channel in channelList:
        channel = ' ' + channel + ' '
        channel = channel.replace( ' ', '')
        host = socket.gethostbyname(socket.gethostname())
        host = ' ' + host + ' '
        port = "1414"
        conn_info = "%s(%s)" % (host, port)

        if host != '127.0.0.1':
            try:
                host = host.replace(' ', '')
                qmgr = pymqi.connect(queue_manager, channel, conn_info)
            except:
                logging.error("Can't connect to manager %s channel %s on %s(%s)" %(queue_manager, channel, host, port))
                host = '127.0.0.1'
                logging.info("Host changed to %s" %(host))
                try:
                    logging.info("Try to connect to manager %s channel %s on %s(%s)" %(queue_manager, channel, host, port))
                    qmgr = pymqi.connect(queue_manager, channel, conn_info)
                except:
                    logging.error("Can't connect to manager %s channel %s on %s(%s)" %(queue_manager, channel, host, port))
                    continue
        else:
            try:
                qmgr = pymqi.connect(queue_manager, channel, conn_info)
            except:
                logging.error("Can't connect to manager %s channel %s on %s(%s)" %(queue_manager, channel, host, port))
                continue
        logging.info("Successfully connected to manager %s channel %s on %s(%s)" %(queue_manager, channel, host, port))
        queuesList = sys.argv[3].split(',')
        for queueName in queuesList:
            prefix = ''+ queueName +''
            queue_type = pymqi.CMQC.MQQT_LOCAL

            args = {pymqi.CMQC.MQCA_Q_NAME: prefix,
                    pymqi.CMQC.MQIA_Q_TYPE: queue_type}

            pcf = pymqi.PCFExecute(qmgr)

            try:
                response = pcf.MQCMD_INQUIRE_Q(args)
            except pymqi.MQMIError, e:
                if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_UNKNOWN_OBJECT_NAME:
                    logging.error("Can't find queue %s."%queueName)
                else:
                    raise
            else:
                for queue_info in response:
                    queue_name = queue_info[pymqi.CMQC.MQCA_Q_NAME]
                    queue_name = queue_name.replace(' ', '')
                    logging.info('Found queue %s' %(queue_name))
                    queue = pymqi.Queue(qmgr, queue_name)
                    try:
                        while queue.get():
                            queue.get()
                    except pymqi.MQMIError, e:
                        logging.info("Queue '%s' is empty." %queue_name)
        qmgr.disconnect()
        break