'''
Developed by Lotobaev P.N.

Changing URL of datasources.
'''

import logging
import re
import time
import sys
import os
import AdminTask
import AdminJMS
import AdminNodeManagement
import AdminControl
import AdminConfig
import AdminApp

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
# Is current node is DMGR?
#################################################################################################################


def nodeIsDmgr(nodename):
    return nodeHasServerOfType(nodename, 'DEPLOYMENT_MANAGER')

#################################################################################################################
# Defining type of node. Example:DEPLOYMENT_MANAGER - cell
#################################################################################################################


def nodeHasServerOfType(nodename, servertype):
    node_id = getNodeId(nodename)
    serverEntries = _splitlines(AdminConfig.list('ServerEntry', node_id))
    for serverEntry in serverEntries:
        sType = AdminConfig.showAttribute(serverEntry, "serverType")
        if sType == servertype:
            return 1


def getNodeId(nodename):
    """Given a node name, get its config ID"""
    return AdminConfig.getid('/Cell:%s/Node:%s/' % (cellName, nodename))

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
# Datasource properties changing
#################################################################################################################

def changeDataSource(scope, old_url, new_url):
    logging.info('Reading Data sources parameters...')
    dataSources = AdminConfig.list('DataSource', scope).splitlines()
    cou = 0
    if len(dataSources) > 0:
        for dataSource in dataSources:
            if dataSource.find('DefaultEJBTimerDataSource') < 0:

                # Datasource properties WebSphere Application Server

                propSet = AdminConfig.showAttribute(dataSource, 'propertySet')
                propList = AdminConfig.list('J2EEResourceProperty', propSet).splitlines()
                for prop in propList:
                    if AdminConfig.showAttribute(prop, 'name') == 'URL':
                        if AdminConfig.showAttribute(prop, 'value').find("" + old_url + "") > 0:
                            logging.warn('Front found! Lets change value!')
                            AdminConfig.modify(prop, [["value", "" + new_url + ""]])
                            cou += 1
                            logging.warn('Change complete!')
                            break
    return cou

#################################################################################################################
#                                                       Script body
#################################################################################################################

cellName = AdminControl.getCell()
cellManager = AdminControl.getNode()
applist = AdminApp.list().splitlines()
old_url = sys.argv[0]
new_url = sys.argv[1]
changedDS = 0

for app in applist:
    appscope = AdminApp.listModules(app, '-server')
    if 'cluster' in appscope:
        appClusterServer = re.findall('(?<=cluster=)[\w-]*', appscope)[0]
        clusterID = AdminConfig.getid('/ServerCluster:' + appClusterServer + '/')
        clusterMemberList = AdminConfig.list('ClusterMember', clusterID)
        clusterMembers = clusterMemberList.splitlines()
        nodename = AdminConfig.showAttribute(clusterMembers[0], 'nodeName')
        scope = AdminConfig.getid('/Cell:' + cellName + '/ServerCluster:' + appClusterServer + '/')
    elif 'server=' in appscope:
        appClusterServer = re.findall('(?<=server=)[\w-]*', appscope)[0]
        serverCompleteName = AdminControl.completeObjectName('WebSphere:type=Server,name=' + appClusterServer + ',*')
        nodename = AdminControl.getAttribute(serverCompleteName, 'nodeName')
        scope = AdminConfig.getid('/Cell:' + cellName + '/Node:' + nodename + '/Server:' + appClusterServer + '/')

    logging.info('Script beginning!')
    changedDS += changeDataSource(scope, old_url, new_url)

logging.warn('!!!!   ' + str(changedDS) + ' datasources was changed   !!!!')

AdminConfig.save()
logging.info('Save successfully ended')
syncAllNodes()
logging.info('Nodes successfully synchronized')
logging.info('Script successfully ended')
