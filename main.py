# -*- coding=utf8 -*-
# This file is to get the crash amounts during a period

import re
import requests
import json
import time
import logging
from twilio.rest import Client

session = requests.Session()
endTime = int(time.time())
startTime = endTime - 1200
versionNumber = ""
buildNumber = ""

crashAmount = -1
totalUser = -1
crashUser = -1

# set the log
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("crashlog.log")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# get the newest version
def getVersion():
    headers_base = {
        # get your own version from server
    }
    contents = session.get(
        "https:******",
        headers=headers_base)
    return contents.json()['data']['version']


# get the latest version
try:
    version = getVersion()
except Exception as e:
    version = "###"
    logger.error("version get occurs error " + e.__str__())
if (version == ""):
    version = "###"


# get the crsf code
def getCRSF():
    contents = session.get("https://fabric.io/login", timeout=30).text
    pattern = re.compile('.*?<meta content="(.*?)" name="csrf-token" />.*?')
    match = re.findall(pattern, contents)
    return match[0]


# get the config data before every refresh or data fetch
def getConfig():
    configUrl = 'https://fabric.io/api/v2/client_boot/config_data'
    response = session.get(configUrl, timeout=30)
    return response


def login(email, password):
    login_data = {
        'email': email,
        'password': password,
    }

    headers_base = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Host': "fabric.io",
        'Connection': "keep-alive",
        'Origin': "https://fabric.io",
        'X-CSRF-Token': getCRSF(),
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
        'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
        'X-Requested-With': "XMLHttpRequest",
        'Referer': "https://fabric.io/login",
        'Accept-Encoding': "gzip, deflate, br",
        'Accept-Language': "zh-CN,zh;q=0.9",
        # 'Cache-Control': 'no-cache',
        # 'Pragma': 'no-cache',
    }

    response = getConfig()
    loginUrl = "https://fabric.io/api/v2/session"
    headers_base['X-CRASHLYTICS-DEVELOPER-TOKEN'] = response.json()['developer_token']
    content = session.post(loginUrl, headers=headers_base, data=login_data, timeout=30)


def getCrash():
    response = getConfig()
    global version
    global versionNumber
    global buildNumber
    global crashAmount
    global totalUser
    global crashUser

    crashUrl = "https://api-dash.fabric.io/graphql"
    buildUrl = "https://api-dash.fabric.io/graphql"

    buildData = {
        'query': "query Project_route($externalId_0:String!) {project(externalId:$externalId_0) {id,...F2}} fragment F0 on ProjectVersion {id,externalId} fragment F1 on Project {id,externalId} fragment F2 on Project {answers {_topBuilds3bGBpV:topBuilds(first:3,days:7) {synthesizedBuildVersion}},_versions4zJYbv:versions(first:100,omitVersionsWithNoEvents:true,days:90) {edges {node {id,externalId,pinned,sortOrder,name,...F0},cursor},pageInfo {hasNextPage,hasPreviousPage}},id,...F1}",
        'variables': {
            'externalId_0': response.json()['current_application']['id']
        }
    }
    dataHeader = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Host': "api-dash.fabric.io",
        'Connection': "keep-alive",
        'Content-Type': "application/json",
        'Origin': "https://fabric.io",
        'X-Relay-Debug-Name': "Project_route",
        'Authorization': "Bearer " + response.json()['current_account']['frontend_access_token'],
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
        'Referer': "https://fabric.io/",
        'Accept-Encoding': "gzip, deflate, br",
        'Accept-Language': "zh-CN,zh;q=0.9",
        'X-CRASHLYTICS-DEVELOPER-TOKEN': response.json()['developer_token']
    }
    build = session.post(buildUrl, data=json.dumps(buildData), headers=dataHeader, timeout=30)
    dict = build.json()['data']['project']
    for key in dict.keys():
        if (re.match(".*?_version.*?", key)):
            buildList = build.json()['data']['project'][key]['edges']
            for i in buildList:
                str = i['node']['name']
                if (str.split("(")[0].strip() == version):
                    versionNumber = i['node']['name']
                    buildNumber = i['node']['externalId']
                    break
            break

    logger.info("result build info is " + versionNumber + "build:" + buildNumber)
    data = {
        'query': "query AppScalars($externalId_0:String!,$type_1:IssueType!,$start_2:UnixTimestamp!,$end_3:UnixTimestamp!,$filters_4:IssueFiltersType!) {project(externalId:$externalId_0) {crashlytics {_scalars1ZlL1k:scalars(synthesizedBuildVersions:[\"" + versionNumber + "\"],type:$type_1,start:$start_2,end:$end_3,filters:$filters_4,buildIds:[\"" + buildNumber + "\"]) {crashes,issues,impactedDevices}},id}}",
        'variables': {
            'externalId_0': response.json()['current_application']['id'],
            'type_1': "crash",
            'start_2': startTime,
            'end_3': endTime,
            'filters_4': {}
        }
    }

    userData = {
        "query": "query SessionAndUserMetrics($externalId_0:String!,$start_1:UnixTimestamp!,$end_2:UnixTimestamp!) {project(externalId:$externalId_0) {answers {_totalSessionsForBuilds3q9E5j:totalSessionsForBuilds(synthesizedBuildVersions:[\"" + versionNumber + "\"],start:$start_1,end:$end_2) {synthesizedBuildVersion,values {timestamp,value}},_dauByBuilds2nCNpm:dauByBuilds(builds:[\"" + versionNumber + "\"],start:$start_1,end:$end_2) {scalar,values {timestamp,value}}},id}}",
        "variables": {
            'externalId_0': response.json()['current_application']['id'],
            "start_1": startTime,
            "end_2": endTime,
        }
    }

    dataHeader['X-Relay-Debug-Name'] = "AppScalars"
    r = session.post(crashUrl, data=json.dumps(data), headers=dataHeader, timeout=30)
    crashDict = r.json()['data']['project']['crashlytics']
    for key in crashDict:
        if (re.match(".*?_scalars.*?", key)):
            crashAmount = crashDict[key]['crashes']
            crashUser = crashDict[key]['impactedDevices']
    logger.info("crash json is " + r.text)

    dataHeader['X-Relay-Debug-Name'] = "SessionAndUserMetrics"
    rr = session.post(crashUrl, data=json.dumps(userData), headers=dataHeader, timeout=30)
    totalDict = rr.json()['data']['project']['answers']
    for key in totalDict:
        if (re.match(".*?_dauByBuild.*?", key)):
            totalUser = totalDict[key]['scalar']
    logger.info("user amount json is " + rr.text)


def callme():
    account = "yourAccount(starts with AC)"
    token = "your token"
    client = Client(account, token)
    call = client.calls.create(
        url='https://demo.twilio.com/docs/voice.xml',
        to='yourPhone',
        from_='registerCode'
    )
    logger.info(call.sid)


logger.info("\n\n\n")
logger.info("Start now")
# check crash start
try:
    login("yourAccount", "yourPassword")
    getCrash()
except Exception as e:
    logger.error("get Crash occurs error " + e.__str__())

logger.info("start time is " + str(startTime) + "  end time is " + str(endTime))
logger.info(
    "whole device is " + str(totalUser) + "crashAmount is " + str(crashAmount) + "crash user is" + str(crashUser))
logger.info(str(crashUser / totalUser))

if (totalUser > 0 and crashUser > 0 and float(crashUser / totalUser) > 0.005):
    callme()
