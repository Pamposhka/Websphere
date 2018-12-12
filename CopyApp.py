'''
Developed by Lotobaev P.N.

Copy applications and environment.
'''

import logging
import re
import time
import sys
import os
import ConfigParser
import AdminApp
import AdminTask
import AdminJMS
import AdminNodeManagement
import AdminControl
import AdminConfig

#################################################################################################################
# Classes
#################################################################################################################


class ConfigParserNotLower(ConfigParser):
    def optionxform(self, optionstr):
        return optionstr


#################################################################################################################
# Functions
#################################################################################################################

#################################################################################################################
# Configure logging
#################################################################################################################

logging.basicConfig(level=logging.DEBUG, format = '%(asctime)s %(levelname)s %(message)s')

#################################################################################################################
# Nodes synchronisation
#################################################################################################################


def syncNodes(nodeName):
    if nodeIsDmgr(nodeName) == 'false':
        nodeSync = AdminControl.completeObjectName('type=NodeSync,node=' + nodeName + ',*')
        AdminControl.invoke(nodeSync, 'sync')
    else:
        pass


def syncAllNodes():
    for node in AdminConfig.list('Node').splitlines():
        syncNodes(AdminConfig.showAttribute(node, 'name'))


#################################################################################################################
# Lines splitting
#################################################################################################################


def _splitlines(s):
    rv = [s]
    if '\r' in s:
        rv = s.split('\r\n')
    elif '\n' in s:
        rv = s.split('\n')
    if rv[-1] == '':
        rv = rv[:-1]
    return rv

#################################################################################################################
# Функция вычисления атрибута объекта
#################################################################################################################


def getObjectAttribute(objectid, attributename):
    result = AdminConfig.showAttribute(objectid, attributename)
    if result is not None and result.startswith("[") and result.endswith("]"):
        # List looks like "[value1 value2 value3]"
        result = _splitlist(result)
    return result

#################################################################################################################
# Функция вычисления, является ли нода DMGR'ом
#################################################################################################################


def nodeIsDmgr(nodename):
    return nodeHasServerOfType(nodename, 'DEPLOYMENT_MANAGER')

#################################################################################################################
# Функция определения типа ноды. Например:DEPLOYMENT_MANAGER - ячейка
#################################################################################################################


def nodeHasServerOfType(nodename, servertype):
    node_id = getNodeId(nodename)
    serverEntries = _splitlines(AdminConfig.list('ServerEntry', node_id))
    for serverEntry in serverEntries:
        sType = AdminConfig.showAttribute(serverEntry, "serverType")
        if sType == servertype:
            return 1

#################################################################################################################
# Вычисление имени ноды
#################################################################################################################


def getNodeId(nodename):
    """Given a node name, get its config ID"""
    return AdminConfig.getid('/Cell:%s/Node:%s/' % (cellName, nodename))


def getNodeName(node_id):
    return getObjectAttribute(node_id, 'name')


def nodeHasServerOfType(nodename, servertype):
    node_id = getNodeId(nodename)
    serverEntries = _splitlines(AdminConfig.list('ServerEntry', node_id))
    for serverEntry in serverEntries:
        sType = AdminConfig.showAttribute(serverEntry, "serverType")
        if sType == servertype:
            return 1

#################################################################################################################
# Проверка наличия конфигурации SSL на хосте
#################################################################################################################

def isSSLConfExists(SSLAlias):
    sslConfigs = AdminTask.listSSLConfigs().splitlines()
    sslConfigNames = []
    for i in sslConfigs:
        i = i.split(' ')
        sslConfigNames.append(i[1])
    if SSLAlias in sslConfigNames:
        result = True
        logging.warning("SSL config with name '" + SSLAlias + "' found on host.")
    else:
        result = False
        logging.warning("SSL config with name '" + SSLAlias + "' was not found on host.")
    return result



#################################################################################################################
# Главная функция, которая вычисляет список нод, на которые возможно установить приложение и его окружающую среду.
# Для установки берём первую возможную ноду.
# Связанные функции: getNodeName, nodeHasServerOfType, nodeIsDmgr, getObjectAttribute.
#################################################################################################################


def listNodes():
    m = "listNodes:"
    node_ids = _splitlines(AdminConfig.list('Node'))
    result = []
    for node_id in node_ids:
        nodename = getNodeName(node_id)
        if not nodeIsDmgr(nodename):
            result.append(nodename)
    return result

#################################################################################################################
# Вычисление номера кластера, следующего за существующим
#################################################################################################################


def calculateNumberOfCluster():
    logging.info('Started count of creating cluster number...')
    try:
        clusterList = AdminConfig.list('ServerCluster', AdminConfig.getid('/Cell:' + cellName + '/')).split('\r\n')
        clusterNameList = []
        for id in clusterList:
            cluster = AdminConfig.showAttribute(id, 'name').capitalize()
            clusterNameList.append(cluster)
        i = 1
        clusterName = 'Cluster'+str(i)
        while clusterName in clusterNameList:
            i += 1
            clusterName = 'Cluster'+str(i)
        clusterName = clusterName.capitalize()
    except:
        logging.info('There is no clusters, so Cluster1 will be created')
        clusterName = 'Cluster1'
    return clusterName

################################################################################################################
# Вычисление номеров серверов приложений - участников кластера
#################################################################################################################


def calculateNumberOfClusterMember(countClusterMembers):
    logging.info('Started count of creating cluster member...')
    serverList = AdminConfig.list('Server', AdminConfig.getid('/Cell:' + cellName + '/')).split('\r\n')
    serverNameList = []
    for id in serverList:
        server = AdminConfig.showAttribute(id, 'name').lower()
        serverNameList.append(server)
    s = 1
    length = countClusterMembers
    clusterMemberName = 'server'+str(s)
    clusterMembers = []
    while clusterMemberName in serverNameList:
        s += 1
        clusterMemberName = 'server'+str(s)
    clusterMemberName = clusterMemberName.capitalize()
    clusterMembers.append(clusterMemberName)
    while int(len(clusterMembers)) < int(length):
        s += 1
        clusterMemberName = 'server'+str(s)
        if clusterMemberName in serverNameList:
            while clusterMemberName in serverNameList:
                s += 1
                clusterMemberName = 'server'+str(s)
            clusterMemberName = clusterMemberName.capitalize()
            clusterMembers.append(clusterMemberName)
        else:
            clusterMemberName = clusterMemberName.capitalize()
            clusterMembers.append(clusterMemberName)
    else:
        pass
    logging.info('' + countClusterMembers + ' cluster member(s) will be create.')
    return clusterMembers

#################################################################################################################
# Вычисление номера сервера, следующего за существующим
#################################################################################################################


def calculateNumberOfServer():
    logging.info('Started count of creating application server number...')
    try:
        serverList = AdminConfig.list('Server', AdminConfig.getid('/Cell:' + cellName + '/')).split('\r\n')
        serverNameList = []
        for id in serverList:
            server = AdminConfig.showAttribute(id, 'name').capitalize()
            serverNameList.append(server)
        s = 1
        serverName = 'Server'+str(s)
        while serverName in serverNameList:
            s += 1
            serverName = 'Server'+str(s)
    except:
        logging.info('There is no servers, so Server1 will be created')
        serverName = 'Server1'
    return serverName


#################################################################################################################
# Поиск идентификационных данных
#################################################################################################################


def findAuthData(authDataAlias, userID):
    authList = AdminConfig.list("JAASAuthData").splitlines()
    for auth in authList:
        authAliasExist = AdminConfig.showAttribute(auth, 'alias')
        userName = re.findall('(?<=/)[\w-]*', auth)[0]
        if authDataAlias == authAliasExist or userID == authAliasExist or userID == userName:
            logging.info('Alias for J2c auth found on the cell.')
            res = True
            break
        else:
            res = False
    if res is False:
        logging.info('Alias for J2c auth was not found on the cell.')

    return res

#################################################################################################################
# Формирование ini-файла со слепком окружения приложения
# 1. Фабрика(-и) соединений очереди
# 2. JDBC драйвера
# 3. Источник(-и) данных
# 4. Очереди
#################################################################################################################

#################################################################################################################
# Вычитка фабрик соединений очереди указанного приложения
#################################################################################################################


def readWMQConnFactories(scope, cellName, appClusterServer, nodename):
    logging.info('Reading Websphere MQ Connection factories parameters...')
    connFactories = AdminConfig.list('MQQueueConnectionFactory', scope).splitlines()
    if (len(connFactories) > 0):
        i = 1
        for connFactory in connFactories:
            printList = []
            printConnPoolList = []
            printSessionPoolList = []
            printList.append('host=' + str(AdminConfig.showAttribute(connFactory, 'host')))
            printList.append('port=' + str(AdminConfig.showAttribute(connFactory, 'port')))
            printList.append('name=' + str(AdminConfig.showAttribute(connFactory, 'name')))
            printList.append('jndiName=' + str(AdminConfig.showAttribute(connFactory, 'jndiName')))
            try:
                printList.append('sslConfiguration=' + str(AdminConfig.showAttribute(connFactory, 'sslConfiguration')))
                printList.append('sslType=' + str(AdminConfig.showAttribute(connFactory, 'sslType')))
            except:
                logging.info("SSL configuration doesn't found.")
            try:
                queueManger = str(AdminConfig.showAttribute(connFactory, 'queueManager'))
                if queueManger == 'None':
                    queueManger = ''
                else:
                    printList.append('queueManager=' + str(AdminConfig.showAttribute(connFactory, 'queueManager')))
            except:
                pass
            printList.append('channel=' + str(AdminConfig.showAttribute(connFactory, 'channel')))
            printList.append('transportType=' + str(AdminConfig.showAttribute(connFactory, 'transportType')))
            try:
                printList.append('description=' + str(AdminConfig.showAttribute(connFactory, 'description')))
            except:
                pass

            connPool = AdminConfig.showAttribute(connFactory, 'connectionPool')
            connPoolProperties = AdminConfig.show(connPool).splitlines()
            for prop in connPoolProperties:
                prop = prop[+1:-1].split(' ')
                if prop[1] != '[]':
                    printConnPoolList.append('' + prop[0] + '=' + str(prop[1]))

            sessPool = AdminConfig.showAttribute(connFactory, 'sessionPool')
            sessPoolProperties = AdminConfig.show(sessPool).splitlines()
            for sessProp in sessPoolProperties:
                sessProp = sessProp[+1:-1].split(' ')
                if sessProp[1] != '[]':
                    printSessionPoolList.append('' + sessProp[0] + '=' + str(sessProp[1]))

            print >> fileOpen, '[connectionFactory' + str(i) + ']'
            for elem in printList:
                print >> fileOpen, elem
            print >> fileOpen, '[connectionFactoryConnPool' + str(i) + ']'
            for param in printConnPoolList:
                print >> fileOpen, param
            print >> fileOpen, '[connectionFactorySessionPool' + str(i) + ']'
            for property in printSessionPoolList:
                print >> fileOpen, property
            print >> fileOpen, ''
            i = i + 1
            printList = []
            printConnPoolList = []
            printSessionPoolList = []
        logging.info('Websphere MQ Connection factories parameters was read and wrote to Ini file.')
    else:
        logging.warn('No connection factories was found.')
        pass

#################################################################################################################
# Вычитка настроек драйвера OJDBC
#################################################################################################################


def readJDBC(scope, cellName, appClusterServer, nodename):
    logging.info('Reading JDBC driver parameters...')
    listJDBCDrivers = _splitlines(AdminConfig.list('JDBCProvider', scope))
    if (len(listJDBCDrivers) > 0):
        for driver in listJDBCDrivers:
            if AdminConfig.showAttribute(driver, 'name') == 'Oracle JDBC Driver':
                i = 1
                printList = []
                printList.append('name=' + str(AdminConfig.showAttribute(driver, 'name')))
                printList.append('description=' + str(AdminConfig.showAttribute(driver, 'description')))
                printList.append('providerType=' + str(AdminConfig.showAttribute(driver, 'providerType')))
                printList.append('isolatedClassLoader=' + str(AdminConfig.showAttribute(driver, 'isolatedClassLoader')))
                printList.append('implementationClassName=' + str(AdminConfig.showAttribute(driver, 'implementationClassName')))
                printList.append('xa=' + str(AdminConfig.showAttribute(driver, 'xa')))
                printList.append('classpath=' + str(AdminConfig.showAttribute(driver, 'classpath')))
                print >> fileOpen, '[JDBCDriver' + str(i)+']'
                for elem in printList:
                    print >> fileOpen, elem
                print >> fileOpen, ''
                i = i + 1
                printList = []
                logging.info('JDBC driver parameters was read and wrote to Ini file.')
            else:
                continue
    else:
        logging.warn('No JDBC driver parameters was found.')
        pass

#################################################################################################################
# Вычитка источников данных указанного приложения
#################################################################################################################


def readDataSources(scope, cellName, appClusterServer, nodename):
    logging.info('Reading Data sources parameters...')
    dataSources = AdminConfig.list('DataSource', scope).splitlines()
    if (len(dataSources) > 0):
        i = 1
        printList = []
        printConnPoolList = []
        printPropertySetList = []
        printMappingList = []
        for dataSource in dataSources:
            if (dataSource.find('DefaultEJBTimerDataSource') < 0):

                # Основные настройки источника данных.
                dsProps = AdminConfig.show(dataSource).splitlines()
                for dsProp in dsProps:
                    if dsProp.startswith('[') and dsProp.endswith(']'):
                        dsProp = dsProp[+1:-1].split(' ', 1)
                    elif (dsProp[1].find('[') > 0) or (dsProp[1].find(']') == 0):
                        dsProp = dsProp.split[+1:](' ', 1)
                    elif (dsProp[1].find('[') == 0) or (dsProp[1].find(']') > 0):
                        dsProp = dsProp.split[:-1](' ', 1)
                    else:
                        dsProp = dsProp.split(' ', 1)
                    if (dsProp[1].find('[') > 0) or (dsProp[1].find(']') > 0) or (dsProp[1].find('(') > 0) or (dsProp[1].endswith(')')):
                        pass
                    else:
                        printList.append('' + dsProp[0] + '=' + dsProp[1] + '')

                # Настройки пула соединений
                connPool = AdminConfig.show(dataSource, 'connectionPool')[+1:-1].split(' ')
                connPoolList = AdminConfig.show(connPool[1]).splitlines()
                for attr in connPoolList:
                    if attr.startswith('[') and attr.endswith(']'):
                        attr = attr[+1:-1].split(' ', 1)
                    elif (attr[1].find('[') > 0) or (attr[1].find(']') == 0):
                        attr = attr.split[+1:](' ', 1)
                    elif (attr[1].find('[') == 0) or (attr[1].find(']') > 0):
                        attr = attr.split[:-1](' ', 1)
                    else:
                        attr = attr.split(' ', 1)
                    if (attr[1].find('[') > 0) or (attr[1].find(']') > 0) or (attr[1].startswith('(')) or (attr[1].endswith(')')) or (attr[1].startswith('"')):
                        pass
                    else:
                        printConnPoolList.append('' + attr[0] + '=' + attr[1] + '')

                # Настройки свойств источника данных WebSphere Application Server
                propSet = AdminConfig.showAttribute(dataSource, 'propertySet')
                propList = AdminConfig.list('J2EEResourceProperty', propSet).splitlines()
                for prop in propList:
                    if AdminConfig.showAttribute(prop, 'name'):
                        if AdminConfig.showAttribute(prop, 'value'):
                            printPropertySetList.append('' + str(AdminConfig.showAttribute(prop, 'name')) + '=' + str(AdminConfig.showAttribute(prop, 'value')))

                # Настройки маппинга модулей источника данных WebSphere Application Server
                mappingSet = AdminConfig.showAttribute(dataSource, 'mapping')
                mappingList = AdminConfig.show(mappingSet).splitlines()
                for map in mappingList:
                    #print map[0][1:-1].split(' ')[1]
                    printMappingList.append('' + str(map[1:-1].split(' ')[0]) + '=' + str(map[1:-1].split(' ')[1]))

                # Запись собранных данных в ini-файл
                print >> fileOpen, '[DataSource' + str(i)+']'
                for elem in printList:
                    print >> fileOpen, elem
                print >> fileOpen, '[DataSourceConnPool' + str(i)+']'
                for param in printConnPoolList:
                    print >> fileOpen, param
                print >> fileOpen, '[DataSourcePropertySet' + str(i)+']'
                for property in printPropertySetList:
                    print >> fileOpen, property
                print >> fileOpen, '[DataSourceMapping' + str(i)+']'
                for mapElem in printMappingList:
                    print >> fileOpen, mapElem
                print >> fileOpen, ''
                i = i + 1
                printConnPoolList = []
                printList = []
                printPropertySetList = []
                printMappingList = []
        logging.info('Data sources parameters was read and wrote to Ini file.')
    else:
        logging.warn('No Data sources parameters was found.')
        pass

#################################################################################################################
# Queues properties
#################################################################################################################


def readQueues(scope, cellName, appClusterServer, nodename):
    logging.info('Reading Queues parameters...')
    queues = _splitlines(AdminConfig.list('MQQueue', scope))
    if (len(queues) > 0):
        i = 1
        printList = []
        for queue in queues:
            printList.append('name=' + str(AdminConfig.showAttribute(queue, 'name')))
            printList.append('jndiName=' + str(AdminConfig.showAttribute(queue, 'jndiName')))
            printList.append('baseQueueName=' + str(AdminConfig.showAttribute(queue, 'baseQueueName')))
            print >> fileOpen, '[Queue' + str(i) + ']'
            for elem in printList:
                print >> fileOpen, elem
            print >> fileOpen, ''
            printList = []
            i = i + 1
        logging.info('Queues parameters was read and wrote to Ini file.')
    else:
        logging.warn('No Queues parameters was found.')
        pass

#################################################################################################################
# Application properties
#################################################################################################################


def getAdminAppViewValue(appname, keyname, parsename):

    verboseString = AdminApp.view(appname, keyname)
    verboseStringList = _splitlines(verboseString)
    resultList = []
    for str in verboseStringList:
        if str.startswith(parsename):
            resultString = str[len(parsename):].strip()
            resultList.append(resultString)
    return resultList

    logging.warn("Exit. Did not find value from application parameters. Returning None.")
    return None


def readAppParams(applist):
    logging.info('Reading Application parameters...')
    resourceRef = getAdminAppViewValue(applist, '-MapResRefToEJB', 'Resource Reference:')
    targetJNDI = getAdminAppViewValue(applist, '-MapResRefToEJB', 'Target Resource JNDI Name:')
    contextRoot = getAdminAppViewValue(applist, '-CtxRootForWebMod', 'Context Root:')
    uri = getAdminAppViewValue(applist, '-MapResRefToEJB', 'URI:')
    module = getAdminAppViewValue(applist, '-MapResRefToEJB', 'Module:')
    resType = getAdminAppViewValue(applist, '-MapResRefToEJB', 'Resource type:')
    i = 1
    print >> fileOpen, '[Application]'
    print >> fileOpen, 'context=%s' % contextRoot[0]
    print >> fileOpen, 'name=%s' % applist
    for res in resourceRef:
        print >> fileOpen, '[ResourceMapping' + str(i) + ']'
        print >> fileOpen, 'resourceReference=%s' % res
        elementIndex = resourceRef.index(res)
        print >> fileOpen, 'targetJNDI=%s' % targetJNDI[elementIndex]
        print >> fileOpen, 'URI=%s' % uri[elementIndex]
        print >> fileOpen, 'module="%s+"' % module[elementIndex]
        print >> fileOpen, 'ResourceType=%s' % resType[elementIndex]
        i = i + 1
    logging.info('Application parameters was read and wrote to Ini file.')


#################################################################################################################
# Application server properties
#################################################################################################################


def readAppServerProps(scopeType, scope, cellName, appClusterServer, nodename):
    logging.info('Reading Application servers (cluster members) parameters...')
    defaultSystemProperties = ['com.ibm.security.jgss.debug', 'com.ibm.security.krb5.Krb5Debug']
    if scopeType == 'Cluster':
        clustermembersList = AdminConfig.showAttribute (scope, 'members')
        clustermembersList = clustermembersList.replace('[', '')
        clustermembersList = clustermembersList.replace(']', '')
        clustermembersList = clustermembersList.split(' ')
        i = 1
        for clusterMember in clustermembersList:
            clusterMemberName = AdminConfig.showAttribute(clusterMember, 'memberName')
            clusterMemberId = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + clusterMemberName + '/')
            jvm = AdminConfig.list('JavaVirtualMachine', clusterMemberId)
            threadPoolManager = AdminConfig.list('ThreadPoolManager', clusterMemberId)
            threadPoolsList = AdminConfig.showAttribute(threadPoolManager,'threadPools')
            threadPoolsList = threadPoolsList.replace('[', '')
            threadPoolsList = threadPoolsList.replace(']', '')
            threadPoolsList = threadPoolsList.split(' ')
            threadPoolPropsList = []
            for pool in threadPoolsList:
                if AdminConfig.showAttribute(pool, 'name') == 'WebContainer':
                    threadPoolPropsList.append('inactivityTimeout=' + str(AdminConfig.showAttribute(pool, 'inactivityTimeout')))
                    threadPoolPropsList.append('maximumSize=' + str(AdminConfig.showAttribute(pool, 'maximumSize')))
                    threadPoolPropsList.append('minimumSize=' + str(AdminConfig.showAttribute(pool, 'minimumSize')))
            printList = []
            printList.append('initialHeapSize=' + str(AdminConfig.showAttribute(jvm, 'initialHeapSize')))
            printList.append('maximumHeapSize=' + str(AdminConfig.showAttribute(jvm, 'maximumHeapSize')))
            params = AdminConfig.showAttribute(jvm, 'systemProperties')
            params = params.replace('[', '')
            params = params.replace(']', '')
            params = params.split(' ')
            systemProperties = []
            for param in params:
                if AdminConfig.showAttribute(param, 'name') and AdminConfig.showAttribute(param, 'name') not in defaultSystemProperties:
                    if AdminConfig.showAttribute(param, 'value'):
                        systemProperties.append('' + str(AdminConfig.showAttribute(param, 'name')) + '=' + str(AdminConfig.showAttribute(param, 'value').replace('\\', '/')))
            print >> fileOpen, '[ClusterMember' + str(i) + ']'
            for jvmParam in printList:
                print >> fileOpen, jvmParam
            print >> fileOpen, '[systemProperties' + str(i) + ']'
            for elem in systemProperties:
                print >> fileOpen, elem
            print >> fileOpen, ''
            print >> fileOpen, '[threadPools' + str(i) + ']'
            for prop in threadPoolPropsList:
                print >> fileOpen, prop
            print >> fileOpen, ''
            i = i + 1
            printList = []
            propList = []
            systemProperties = []
        logging.info('Application servers (cluster members) parameters was read and wrote to Ini file.')
    elif scopeType == 'Server':
        jvm = AdminConfig.list('JavaVirtualMachine', scope)
        printList = []
        printList.append('initialHeapSize=' + str(AdminConfig.showAttribute(jvm, 'initialHeapSize')))
        printList.append('maximumHeapSize=' + str(AdminConfig.showAttribute(jvm, 'maximumHeapSize')))
        params = AdminConfig.showAttribute(jvm, 'systemProperties')
        params = params.replace('[', '')
        params = params.replace(']', '')
        params = params.split(' ')
        systemProperties = []
        i = 1
        for param in params:
            if AdminConfig.showAttribute(param, 'name') and AdminConfig.showAttribute(param, 'name') not in defaultSystemProperties:
                if AdminConfig.showAttribute(param, 'value'):
                    systemProperties.append('' + str(AdminConfig.showAttribute(param, 'name')) + '=' + str(AdminConfig.showAttribute(param, 'value').replace('\\', '/')))
        print >> fileOpen, '[ApplicationServer' + str(i) + ']'
        for jvmParam in printList:
            print >> fileOpen, jvmParam
        print >> fileOpen, '[systemProperties' + str(i) + ']'
        for elem in systemProperties:
            print >> fileOpen, elem
        print >> fileOpen, ''
        i = i + 1
        printList = []
        propList = []
        systemProperties = []
        logging.info('Application servers parameters was read and wrote to Ini file.')

#################################################################################################################
# Функции создания окружения приложения
# 1. Кластер + сервер приложений или только сервер приложений (с параметрами JVM)
# 2. Создание источников данных + JDBC
# 3. Создание фабрик соединения очереди
# 4. Создание очередей
# 5. Деплой приложения
#################################################################################################################


def findScopeType(fileIni):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    Sections = fileSettings.sections()
    scopeType = None
    for section in Sections:
        if section == 'Scope':
            scopeType = fileSettings.get(section, 'scopeType')
    return scopeType

#################################################################################################################
# Функция подсчета количества серверов приложений - участников кластера
#################################################################################################################


def findCountClusterMembers(fileIni):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    Sections = fileSettings.sections()
    scopeType = None
    for section in Sections:
        if section == 'Scope':
            countClusterMembers = fileSettings.get(section, 'countClusterMembers')
            return countClusterMembers

#################################################################################################################
# Создание кластера + сервера приложений или только сервера приложений с использованием переменных JVM
#################################################################################################################


def createScope(scopeType, newScope, nodename, newScopeMembers):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    if scopeType == 'Cluster':
        logging.info('Creating cluster with cluster member(s)...')
        AdminTask.createCluster('[-clusterConfig [-clusterName ' + newScope + ' ] ' + ' -replicationDomain [-createDomain false ] ]' )
        logging.info('' + newScope + ' created.')
        for clusterMember in newScopeMembers:
            AdminTask.createClusterMember('[-clusterName ' + newScope + ' -memberConfig [-memberNode ' + nodename + ' -memberName ' + clusterMember +' -replicatorEntry false]]')
            logging.info('' + clusterMember + ' created.')
        scope = AdminConfig.getid('/Cell:' + cellName + '/ServerCluster:' + newScope + '/')
        clustermembersList = AdminConfig.showAttribute(scope, 'members')
        clustermembersList = clustermembersList.replace('[', '')
        clustermembersList = clustermembersList.replace(']', '')
        clustermembersList = clustermembersList.split(' ')
        i = 1
        isClusterMemberExist = fileSettings.has_section('ClusterMember' + str(i))
        ClusterMemberSections = fileSettings.sections()
        while isClusterMemberExist is True:
            for section in ClusterMemberSections:
                if section == 'ClusterMember' + str(i):
                    clusterMemberName = AdminConfig.showAttribute(clustermembersList[i-1], 'memberName')
                    clusterMemberId = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + clusterMemberName + '/')
                    jvm = AdminConfig.list('JavaVirtualMachine', clusterMemberId)
                    attrs = []
                    anotherAttrs = []
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        attrs.append([option, fileSettings.get(section, option)])
                    section = 'systemProperties' + str(i)
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        anotherAttrs.append([['name', option], ['value', fileSettings.get(section, option)]])
                    attrs.append(['systemProperties', anotherAttrs])
                    AdminConfig.modify(jvm, attrs)
                    logging.info('JVM parameters was applied.')
                    section = 'threadPools' + str(i)
                    threadPoolManager = AdminConfig.list('ThreadPoolManager', clusterMemberId)
                    threadPoolsList = AdminConfig.showAttribute(threadPoolManager, 'threadPools')
                    threadPoolsList = threadPoolsList.replace('[', '')
                    threadPoolsList = threadPoolsList.replace(']', '')
                    threadPoolsList = threadPoolsList.split(' ')
                    for pool in threadPoolsList:
                        if AdminConfig.showAttribute(pool, 'name') == 'WebContainer':
                            poolID = pool
                    sectionOptions = fileSettings.options(section)
                    threadIniAttrs = '['
                    for option in sectionOptions:
                        threadIniAttrs += '['+option+' "'+fileSettings.get(section, option)+'"]'
                    threadIniAttrs += ']'
                    AdminConfig.modify(poolID, threadIniAttrs)
                    logging.info('Thread pools parameters was applied.')
                    attrs = []
                    i = i + 1
                isClusterMemberExist = fileSettings.has_section('ClusterMember' + str(i))
    elif scopeType == 'Server':
        logging.info('Creating application server...')
        AdminTask.createApplicationServer(nodename, '[-name ' + newScope + ']')
        logging.info('Application server ' + newScope + ' created.')
        scope = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + newScope + '/')
        appServerSections = fileSettings.sections()
        i = 1
        for section in appServerSections:
            if section == 'ApplicationServer' + str(i):
                jvm = AdminConfig.list('JavaVirtualMachine', scope)
                attrs = []
                anotherAttrs = []
                sectionOptions = fileSettings.options(section)
                for option in sectionOptions:
                    attrs.append([option, fileSettings.get(section, option)])
                section = 'systemProperties' + str(i)
                sectionOptions = fileSettings.options(section)
                for option in sectionOptions:
                    anotherAttrs.append([['name', option], ['value', fileSettings.get(section, option)]])
                attrs.append(['systemProperties', anotherAttrs])
                AdminConfig.modify(jvm, attrs)
                logging.info('JVM parameters was applied.')
                section = 'threadPools' + str(i)
                threadPoolManager = AdminConfig.list('ThreadPoolManager', scope)
                threadPoolsList = AdminConfig.showAttribute(threadPoolManager, 'threadPools')
                threadPoolsList = threadPoolsList.replace('[', '')
                threadPoolsList = threadPoolsList.replace(']', '')
                threadPoolsList = threadPoolsList.split(' ')
                for pool in threadPoolsList:
                    if AdminConfig.showAttribute(pool, 'name') == 'WebContainer':
                        poolID = pool
                sectionOptions = fileSettings.options(section)
                threadIniAttrs = '['
                for option in sectionOptions:
                    threadIniAttrs += '['+option+' "'+fileSettings.get(section, option)+'"]'
                threadIniAttrs += ']'
                AdminConfig.modify(poolID, threadIniAttrs)
                logging.info('Thread pools parameters was applied.')
                attrs = []
                i = i + 1
    logging.info('End of scope creating.')

#################################################################################################################
# Определение драйвера JDBC
#################################################################################################################


def findJDBCDriver(cellName, scopeType, newScope, nodename):
    print 'findJDBCDriver started'
    if scopeType == 'Cluster':
        scope = AdminConfig.getid('/Cell:' + cellName + '/ServerCluster:' + newScope + '/')
    elif scopeType == 'Server':
        scope = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + newScope + '/')
    listJDBCDrivers = AdminConfig.list('JDBCProvider', scope).splitlines()
    JDBC =[]
    if (len(listJDBCDrivers) > 0):
        for driver in listJDBCDrivers:
            if AdminConfig.showAttribute(driver, 'name') == 'Oracle JDBC Driver':
                JDBC.append(driver)
            else:
                continue
    if len(JDBC) > 0:
        return JDBC[0]
        print 'Found JDBC'
    else:
        JDBC = 'Empty'
        return JDBC

#################################################################################################################
# JDBC-driver creating
#################################################################################################################


def createJDBCDriver(cellName, scopeType, newScope, nodename):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    i = 1
    if fileSettings.has_section('JDBCDriver' + str(i)):
        logging.info('Creating JDBC driver')
        JDBCSections = fileSettings.sections()
        for section in JDBCSections:
            if section == 'JDBCDriver' + str(i):
                attrs = []
                sectionOptions = fileSettings.options(section)
                for option in sectionOptions:
                    attrs.append([option, fileSettings.get(section, option)])
        if scopeType == 'Cluster':
            clusterID = AdminConfig.getid('/Cell:' + cellName + '/ServerCluster:' + newScope + '/')
            JDBC = AdminConfig.create('JDBCProvider', clusterID, attrs)
        elif scopeType == 'Server':
            serverID = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + newScope + '/')
            JDBC = AdminConfig.create('JDBCProvider', serverID, attrs)
        return JDBC
    else:
        logging.warn('No JDBC driver found.')

#################################################################################################################
# Datasource creating
#################################################################################################################

def createDataSources(cellName, scopeType, newScope, nodename, JDBC):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    i = 1
    isDataSourceExist = fileSettings.has_section('DataSource' + str(i))
    DataSourceSections = fileSettings.sections()
    if isDataSourceExist:
        logging.info('Creating datasource...')
        security = AdminConfig.getid('/Cell:' + cellName + '/Security:/')
        while isDataSourceExist is True:
            for section in DataSourceSections:
                if section == 'DataSource' + str(i):
                    connPoolAttrs = []
                    dsParams = []
                    propertySetParams = []
                    mappingSetParams = []
                    jaasAttrs = []
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        if option == 'name':
                            dsName = fileSettings.get(section, option)
                        elif option == 'authDataAlias':
                            try:
                                j2cAuth = fileSettings.get(section, option)
                                userID = re.findall('(?<=/)[\w-]*', j2cAuth)[0]
                                authDataAlias = '' + cellName + '/' + userID + ''
                                if findAuthData(authDataAlias, userID) is False:
                                    jaasAttrs.append(["password", userID])
                                    jaasAttrs.append(["userId", userID])
                                    jaasAttrs.append(["alias", authDataAlias])
                                    #print 'here'
                                    AdminConfig.create('JAASAuthData', security, jaasAttrs)
                                    print 'User %s created.' % authDataAlias
                                    dsParams.append([option, authDataAlias])
                                    print dsParams
                                    continue
                                    #print 'or here'
                                else:
                                    dsParams.append(['authDataAlias', '' + cellName + '/' + userID + ''])
                                    logging.info('User with alias ' + authDataAlias + ' will be used for datasource.')
                            except:
                                pass
                        dsParams.append([option, fileSettings.get(section, option)])
                    section = 'DataSourceConnPool' + str(i)
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        connPoolAttrs.append([option, fileSettings.get(section, option)])
                    connPool = ["connectionPool", connPoolAttrs]
                    dsParams.append(connPool)
                    section = 'DataSourcePropertySet' + str(i)
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        propertySetParams.append([['name', option], ['value', fileSettings.get(section, option)], ["type", "java.lang.String"]])

                    propertySets = [["propertySet", [["resourceProperties", propertySetParams]]]]

                    try:
                        section = 'DataSourceMapping' + str(i)
                        print section
                        sectionOptions = fileSettings.options(section)
                        for option in sectionOptions:
                            if option == 'authDataAlias':
                                auth = fileSettings.get(section, option)
                                userName = re.findall('(?<=/)[\w-]*', auth)[0]
                                authDataAlias = '' + cellName + '/' + userName + ''
                                mappingSetParams.append([[option+"" + authDataAlias + ""]])
                    except:
                        pass

                    if scopeType == 'Cluster':
                        logging.info('Create on cluster')
                        clusterID = AdminConfig.getid('/Cell:' + cellName + '/ServerCluster:' + newScope + '/')
                        try:
                            newds = AdminConfig.create('DataSource', JDBC, dsParams)  # Создание источника данных
                            AdminConfig.modify(newds, propertySets)
                            try:
                                mapp = AdminConfig.showAttribute(newds, 'mapping')  # Поиск модуля маппинга источника данных
                                if mapp is None:  # Если не существует, создаём, иначе используем существующий
                                    logging.info('Creating MappingModule for datasource ' + dsName + '.')
                                    attrs = [['authDataAlias','' + authDataAlias + ''], ['mappingConfigAlias','DefaultPrincipalMapping']]
                                    mapp = AdminConfig.create('MappingModule', newds, attrs)
                                    print mapp
                                    print attrs
                                else:
                                    logging.info('MappingModule of datasource ' + dsName + ' was modified.')
                                    AdminConfig.modify(mapp, mappingSetParams)
                            except:
                                pass
                            logging.info('Data source ' + dsName + ' was created.')
                        except:
                            logging.warn('Datasource ' + dsName + ' already exist, or properties are broken.')
                    elif scopeType == 'Server':
                        print 'Create on server'
                        serverID = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + newScope + '/')
                        try:
                            newds = AdminConfig.create('DataSource', JDBC, dsParams)  # Создание фабрики соединений очереди
                            AdminConfig.modify(newds, propertySets)
                            logging.info('Data source ' + dsName + ' was created.')
                        except:
                            logging.warn('Datasource ' + dsName + ' already exist, or properties are broken.')
                    i = i + 1
                isDataSourceExist = fileSettings.has_section('DataSource' + str(i))
    else:
        logging.warn('No data sources was found.')


#################################################################################################################
# JMS creating
#################################################################################################################


def createWMQConnectionFactory(scopeType, cellName, newScope, nodename):
    if scopeType == 'Cluster':
        conFactStartLine = '"WebSphere MQ JMS Provider(cells/' + cellName + '/clusters/' + newScope + \
                           '|resources.xml#builtin_mqprovider)"'
    elif scopeType == 'Server':
        conFactStartLine = '"WebSphere MQ JMS Provider(cells/' + cellName + '/nodes' + nodename + '/servers/' + newScope + \
                           '|resources.xml#builtin_mqprovider)"'
    fileSettings = ConfigParserNotLower.ConfigParser()
    conFactCodeLine = AdminTask.createWMQConnectionFactory
    readConf = fileSettings.read(fileIni)
    c = 1
    isConnFactExist = fileSettings.has_section('connectionFactory' + str(c))
    connFactorySections = fileSettings.sections()
    if isConnFactExist:
        while isConnFactExist == True:
            for section in connFactorySections:
                if section == 'connectionFactory' + str(c):
                    # вычитка параметров из INI-файла
                    connFactoryParams = []
                    conn_pool = []
                    sess_pool = []
                    sectionOptions = fileSettings.options(section)
                    if 'sslConfiguration' in sectionOptions:
                        SSLAlias = fileSettings.get(section, 'sslConfiguration')
                        if isSSLConfExists(SSLAlias) == True:
                            for option in sectionOptions:
                                cfname = fileSettings.get(section, 'name')
                                connFactoryParams.append([option, fileSettings.get(section, option)])
                        else:
                            for option in sectionOptions:
                                if option != 'sslConfiguration' and option != 'sslType':
                                    cfname = fileSettings.get(section, 'name')
                                    connFactoryParams.append([option, fileSettings.get(section, option)])
                    else:
                        for option in sectionOptions:
                            cfname = fileSettings.get(section, 'name')
                            connFactoryParams.append([option, fileSettings.get(section, option)])
                    section = 'connectionFactoryConnPool' + str(c)
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        conn_pool.append([option, fileSettings.get(section, option)])
                    section = 'connectionFactorySessionPool' + str(c)
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        sess_pool.append([option, fileSettings.get(section, option)])

                    typeJMS = 'MQQueueConnectionFactory'
                    connFactoryParams.append(['connectionPool', conn_pool])
                    connFactoryParams.append(['sessionPool', sess_pool])

                    # окончание вычитки параметров из INI-файла
                    newqf = AdminConfig.create(typeJMS, conFactStartLine, connFactoryParams)  # Создание фабрики соединений очереди
                    logging.info('Connection factory ' + cfname + ' was created.')
                    connFactoryDescription = None
                    isConnFactExist = fileSettings.has_section('connectionFactory' + str(c))
                    c = c + 1
                isConnFactExist = fileSettings.has_section('connectionFactory' + str(c))
    else:
        logging.info('No connection factories was found.')

#################################################################################################################
# Creating queues
#################################################################################################################


def createQueues(scopeType, cellName, newScope, nodename):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    i = 1
    isQueueExist = fileSettings.has_section('Queue' + str(i))
    queueSections = fileSettings.sections()
    if isQueueExist:
        while isQueueExist is True:
            for section in queueSections:
                if section == 'Queue' + str(i):
                    attrs = []
                    sectionOptions = fileSettings.options(section)
                    for option in sectionOptions:
                        attrs.append([option, fileSettings.get(section, option)])
                    if scopeType == 'Cluster':
                        clusterID = '"WebSphere MQ JMS Provider(cells/' + cellName + '/clusters/' + newScope + \
                                                      '|resources.xml#builtin_mqprovider)"'
                        newQueue = AdminConfig.create('MQQueue', clusterID, attrs)  # Создание очереди
                    elif scopeType == 'Server':
                        serverID = '"WebSphere MQ JMS Provider(cells/' + cellName + '/nodes' + nodename + '/servers/' + newScope + \
                                                     '|resources.xml#builtin_mqprovider)"'
                        newQueue = AdminConfig.create('MQQueue', serverID, attrs)  # Создание очереди
                        logging.info('Queue was created.')
                    i = i + 1
                isQueueExist = fileSettings.has_section('Queue' + str(i))
    else:
        logging.warn('No queues was found.')

#################################################################################################################
# Application installing
#################################################################################################################


def deployApp(scopeType, cellName, newScope, nodename, pathToApp):
    fileSettings = ConfigParserNotLower.ConfigParser()
    readConf = fileSettings.read(fileIni)
    i = 1
    isAppExist = fileSettings.has_section('Application')
    isMapExist = fileSettings.has_section('ResourceMapping' + str(i) + '')
    appSections = fileSettings.sections()
    for section in appSections:
        if section == 'Application':
            appName = fileSettings.get(section, 'name')
            context = fileSettings.get(section, 'context')
    if isMapExist:
        mappingString = '-MapResRefToEJB ['
        while isMapExist:
            for section in appSections:
                if section == 'ResourceMapping' + str(i) + '':
                    resourceReference = fileSettings.get(section, 'resourceReference')
                    targetJNDI = fileSettings.get(section, 'targetJNDI')
                    uri = fileSettings.get(section, 'URI')
                    module = fileSettings.get(section, 'module')
                    ResourceType = fileSettings.get(section, 'ResourceType')
                    mapping = '[ ' + module + ' "" ' + uri + ' ' + resourceReference + ' ' + ResourceType + ' ' + targetJNDI + ' "" "" "" ]'
                    mappingString = mappingString + mapping
                    i = i + 1
                isMapExist = fileSettings.has_section('ResourceMapping' + str(i) + '')
        mappingString = mappingString + ']'
    else:
        logging.info('Installing application without mapping resources.')
        mappingString = ''
    if scopeType == 'Cluster':
        AdminApp.install(pathToApp, '[ -appname ' + appName + ' -MapModulesToServers [[ .* .* WebSphere:cell=' + cellName + ',cluster=' + newScope + ' ]] -MapWebModToVH [[ .* .* default_host]] -CtxRootForWebMod [[.* .* ' + context + ']] ' + mappingString + ' ]')
    elif scopeType == 'Server':
        AdminApp.install(pathToApp, '[ -appname ' + appName + ' -MapModulesToServers [[ .* .* WebSphere:cell=' + cellName + ',node=' + nodename + ',server=' + newScope + ' ]] -MapWebModToVH [[ .* .* default_host]] -CtxRootForWebMod [[.* .* ' + context + ']] ' + mappingString + ' ]')

#################################################################################################################
#                                                       Script body
#################################################################################################################

command = sys.argv[0]  # deploy or read command

cellName = AdminControl.getCell()
cellManager = AdminControl.getNode()

lenArguments = len(sys.argv)

if lenArguments == 1 or command == 'help':
    command = 'help'
    if command == 'help':
        print 'This script can read properties of some application to Ini-file'
        print 'or deploy application to server by properties from Ini-file'
        print 'if you want to read properties, use next syntax: thinClient -host SERVER -port PORT -lang jython -f "PATH_TO_SCRIPT" read "PATH_TO_INI" APPLICATION_NAME'
        print 'if you want to deploy application, use next syntax: thinClient -host SERVER -port PORT -lang jython -f "PATH_TO_SCRIPT" deploy "PATH_TO_INI"'
    sys.exit()
elif lenArguments < 1 or lenArguments > 3:
    print 'Wrong count of arguments = %s, need min 1, max 3!' % lenArguments
    sys.exit()
elif lenArguments > 1 and command == 'help':
    print 'You cannot ask for help and try to do something with application or Ini file!'
    sys.exit()
elif command == 'deploy' or command == 'read':
    fileIni = sys.argv[1]
    if command == 'read':
        applist = sys.argv[2]
        try:
            appscope = AdminApp.listModules(applist, '-server')
            logging.info('Writing properties to ' + fileIni + '')
            logging.info('Copied application name is: ' + applist + '')
            print''
        except:
            logging.error('There is no application specified! Please, check the name of application!')
            sys.exit()
        try:
            fileOpen = open(fileIni, 'w')
            fileOpen.close()
        except:
            logging.error("Can't open ini file or can't find the path specified.")
            sys.exit()
        fileOpen = open(fileIni, 'a')  # Append to INI file
        print >> fileOpen, '#Application:%s' % applist
        if 'cluster' in appscope:
            global scopeType
            scopeType = 'Cluster'
            appClusterServer = re.findall('(?<=cluster=)[\w-]*', appscope)[0] # регулярное выражение для поиска кластеров, на которых развернуто приложение. Возвращает список кластеров.
            clusterID = AdminConfig.getid('/ServerCluster:' + appClusterServer + '/')
            clusterMemberList = AdminConfig.list('ClusterMember', clusterID)
            clusterMembers = clusterMemberList.splitlines()
            nodename = AdminConfig.showAttribute(clusterMembers[0], 'nodeName')
            scope = AdminConfig.getid('/Cell:' + cellName + '/ServerCluster:' + appClusterServer + '/')
            global countClusterMembers
            countClusterMembers = len(clusterMembers)
            print >> fileOpen, '#Application is deployed on Cluster, so scope will be the same. Was %s.' % appClusterServer
            print >> fileOpen, '[Scope]'
            print >> fileOpen, 'scopeType=Cluster'
            print >> fileOpen, 'countClusterMembers=%s' % countClusterMembers
            print >> fileOpen, ''
        elif 'server=' in appscope:
            global scopeType
            scopeType = 'Server'
            appClusterServer = re.findall('(?<=server=)[\w-]*', appscope)[0]
            serverCompleteName = AdminControl.completeObjectName('WebSphere:type=Server,name=' + appClusterServer + ',*')
            nodename = AdminControl.getAttribute(serverCompleteName, 'nodeName')
            scope = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + appClusterServer + '/')
            print >> fileOpen, '#Application is deployed on Application Server, so scope will be the same. Was %s.' % appClusterServer
            print >> fileOpen, '[Scope]'
            print >> fileOpen, 'scopeType=Server'
            print >> fileOpen, ''

        readWMQConnFactories(scope, cellName, appClusterServer, nodename)
        readDataSources(scope, cellName, appClusterServer, nodename)
        readJDBC(scope, cellName, appClusterServer, nodename)
        readQueues(scope, cellName, appClusterServer, nodename)
        readAppServerProps(scopeType, scope, cellName, appClusterServer, nodename)
        readAppParams(applist)
        fileOpen.close()
        if fileOpen.closed is False:
            fileOpen.close()
    elif command == 'deploy':
        try:
            fileOpen = open(fileIni, 'r')
        except:
            logging.error('There is no such file: ' + fileIni + '. Please check path specified!')
            sys.exit()
        logging.info('All properties taken from ' + fileIni + '')
        pathToApp = sys.argv[2]
        nodename = listNodes()[0]
        clusterName = []
        serverName = []
        clusterMembers = []
        scopeType = findScopeType(fileIni)
        if scopeType == 'Cluster':
            newScopeCluster = calculateNumberOfCluster()
            newScope = newScopeCluster
            countClusterMembers = findCountClusterMembers(fileIni)
            newScopeMembers = calculateNumberOfClusterMember(countClusterMembers)
            createScope(scopeType, newScope, nodename, newScopeMembers)
        elif scopeType == 'Server':
            newScopeServer = calculateNumberOfServer()
            newScope = newScopeServer
            createScope(scopeType, newScope, nodename, newScopeMembers=None)
        JDBC = findJDBCDriver(cellName, scopeType, newScope, nodename)
        if JDBC == 'Empty':
            JDBC = createJDBCDriver(cellName, scopeType, newScope, nodename)
        createDataSources(cellName, scopeType, newScope, nodename, JDBC)
        createWMQConnectionFactory(scopeType, cellName, newScope, nodename)
        createQueues(scopeType, cellName, newScope, nodename)
        AdminConfig.save()
        logging.info('Save successfully ended')
        syncAllNodes()
        logging.info('Nodes successfully synchronized')
        time.sleep(10)
        deployApp(scopeType, cellName, newScope, nodename, pathToApp)
        AdminConfig.save()
        logging.info('Save successfully ended')
        syncAllNodes()
        logging.info('Nodes successfully synchronized')
else:
    logging.error('Wrong type of command! Use [read] or [deploy]!')
    sys.exit()
