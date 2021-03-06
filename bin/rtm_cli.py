#! /usr/bin/env python
# -*- coding: utf-8 -*-

VERSION = "1.3.2"

# LICENSE
# ======================================================================
# REMEMBER THE MILK COMMAND LINE INTERFACE (RTM-CLI)
# Copyright (C) 2011 David Waring
# Email: dave@davidwaring.net
#
# ----------------------------------------------------------------------
#
# This program is a command line interface for Remember the Milk
# See ./rtm --help for more information
#
# ----------------------------------------------------------------------
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This program is in no way endorsed by or affiliated with Remember the Milk (TM)



# TODO:
# Improve suport for repeating tasks
#     - possibly display the last two most recent occurences of the recurring task
# add filter / smart lists to create list
# add estimate support
# add location support
# incoporate Google Calendar?  --> Using Google's CLI




# DISPLAY DEFAULTS
PLAIN = 0                   # print tasks in plain mode (=1) or color mode (=0)
DISP_TAGS = 1               # print tasks with (=1) or without (=0) tags
DISP_NOTES = 1              # print tasks with (=1) or without (=0) note indicators
DISP_COMP = 1               # print tasks with (=1) or without (=0) completed tasks
DISP_STATUS = 1             # print status messages (=1)
ENABLE_READLINE = 1         # enable the import of readline module (disable for better unicode support)

CLI_EDITOR = "nano"         # this is the name of the CLI text editor used to edit the body of notes
CLI_EDITOR_PAUSE = 0        # set this to 1 if you want the script to pause after starting the editor


# COLOR CODES:
# Use the following ANSI display attributes to set the colors for the various properties
#
#                           Foreground Colors
# 0 Reset all attributes    30 Black
# 1 Bright                  31 Red
# 2 Dim                     32 Green
# 4 Underscore              33 Yellow
# 5 Blink                   34 Blue
# 7 Reverse                 35 Magenta
# 8 Hidden                  36 Cyan
#                           37 White

COLOR_PRI1 = "\033[0;31m"
COLOR_PRI2 = "\033[0;34m"
COLOR_PRI3 = "\033[0;36m"
COLOR_DUE = "\033[0;32m"
COLOR_TAG = "\033[0;35m"
COLOR_LIST = "\033[4;33m"
COLOR_NOTE_BORDER = "\033[0;33m"
COLOR_NOTE_TITLE = "\033[1;31m"
COLOR_PLANNER_BORDER = ""
COLOR_PLANNER_DATE = "\033[1;32m"
COLOR_PLANNER_TODAY = "\033[4;32m"
COLOR_PLANNER_OA_HEADER = "\033[4;35m"
COLOR_RESET = "\033[0;m"




# IMPORT STATEMENTS
import rtm
import sys
import os
import re
import tempfile
import subprocess
import getopt
from datetime import datetime
from datetime import date
from datetime import timedelta
from datetime import tzinfo
from operator import itemgetter
import string
import webbrowser
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen
    from urllib import quote

# VARIABLES:
# IF YOU ARE PLANNING ON MAKING DRASTIC CHANGES OR USING THIS SCRIPT AS THE BASIS FOR ANOTHER PROGRAM,
# PLEASE OBTAIN A NEW API KEY & SECRET FROM REMEMBER THE MILK
api_key = "26a9a86a62967b40c5e8af96882475b8"    # The RTM API Key
api_secret = "4e947d71a0033072"                 # The RTM API Shared Secret
lookup_table = {}                               # An index of all tasks based on their id
lists = {}                                      # An index of list names based on their id
tasks = []                                      # A nested list of tasks containing their properties
MODE = ""                                       # The mode the script is currently running as
weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]


# TIMEZONE CLASSES:
# Dealing with timezone differences between RTM (UTC) and local machine
# Code from example under http://docs.python.org/library/datetime.html#tzinfo-objects

ZERO = timedelta(0)
HOUR = timedelta(hours=1)

# A UTC class.

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()



# ========================================================================================================= #
# Login                                                                                                     #
#    Login in to Remember the Milk and get a frob and authentication token                                  #
#    GLOBAL my_rtm: an authenticated remember the milk object                                               #
#    RETURN: username - the name of the logged in user                                                      #
# ========================================================================================================= #
def login():

    #status("Authenticating... |=     |")
    # TEST NETWORK CONNECTION

    # try to connect to the RTM API server
    try:
        test = urlopen("http://api.rememberthemilk.com/services/rest/")

    # when no internet connection is available...
    except URLError:
        display("ERROR: Cannot connect to RTM server.")
        sys.exit(1)

    # if a redirect occurs...
    if test.geturl() != "http://api.rememberthemilk.com/services/rest/":
        display("ERROR: Cannot connect to RTM server.")
        sys.exit(1)

    #status("Authenticating... |==    |")
    # CHECK FOR A CACHED TOKEN
    reauth = "true"
    try:
        full_dir = os.path.expanduser(os.path.join("~", ".rtm", api_key))
        full_path = os.path.expanduser(os.path.join(full_dir, "token"))
        try:
            os.makedirs(full_dir)
        except OSError:
            pass
        f = open(full_path, "rt")
        token = f.read()
        f.close()

        # Check cached token:
        #status("Authenticating... |===   |")
        rtm_check = rtm.createRTM(api_key, api_secret, token)
        #status("Authenticating... |====  |")
        try:
            rsp = rtm_check.test.login()
            reauth = "false"
        except rtm.RTMAPIError:
            reauth = "true"

    except IOError:
        #status("Authenticating... |====  |")
        reauth = "true"

    #status("Authenticating... |===== |")
    # IF THE TOKEN CACHE IS NOT FOUND...
    if reauth == "true":

        # AUTHENTICATE THE USER WITH RTM

        # create a temporary rtm object to get authURL
        rtm_init = rtm.createRTM(api_key, api_secret, "null")
        auth_url = rtm_init.getAuthURL()

        # Prompt and pause when we need to get a new token
        webbrowser.open(auth_url, True, True)
        display("This program requires access to your RTM account")
        display("If a browser has not opened, use the following URL:")
        display(auth_url)
        get_input("Press ENTER after you have authorized this program")

        # Get the authorized token
        token = rtm_init.getToken()

        # SAVE TOKEN TO DISK
        full_dir = os.path.expanduser(os.path.join("~", ".rtm", api_key))
        full_path = os.path.expanduser(os.path.join(full_dir, "token"))
        try:
            os.makedirs(full_dir)
        except OSError:
            pass
        f = open(full_path, "wt")
        f.write(token)
        f.close()


    #status("Authenticating... |===== |")
    # CREATE THE FINAL AUTHENTICATED GLOBAL RTM OBJECT
    global my_rtm
    my_rtm = rtm.createRTM(api_key, api_secret, token)
    #status("Authenticating... |======|")

    try:
        rsp = my_rtm.test.login()
        status(None)
        return rsp.user.username
    except rtm.RTMAPIError:
        status(None)
        display("ERROR! Could not properly authenticate with RTM")
        return "null"

# END login()
# ========================================================================================================= #



# ========================================================================================================= #
# Logout                                                                                                    #
#    Remove login credentials used by this program                                                          #
# ========================================================================================================= #
def logout():

    display("logging out...")

    # get the path to the rtm settings
    full_path = os.path.expanduser(os.path.join("~", ".rtm"))

    # remove the directory containing rtm settings
    import shutil
    shutil.rmtree(full_path)

    sys.exit(0)

# END logout()
# ========================================================================================================= #



# ========================================================================================================= #
# getTimeline                                                                                               #
#    this method will load the timeline id saved to disk, if present.  If not present, a new one will be    #
#      requested from RTM.                                                                                  #
#    RETURN timeline: the timeline id to be used in rtm methods                                             #
# ========================================================================================================= #
def getTimeline():

    # filename to keep Timeline ID
    filename = "timeline"

    # Generate path to keep the Timeline ID
    full_path = os.path.expanduser(os.path.join("~", ".rtm", api_key, filename))

    # attempt to read the timeline from disk, if there
    try:
        f = open(full_path, "r")
        timeline = f.read()
        f.close()

        return timeline.strip()

    # if no file is found...
    except IOError:
        # get a timeline
        rsp = my_rtm.timelines.create()
        timeline = rsp.timeline

        # write it to disk
        f = open(full_path, "w")
        f.write(timeline)
        f.close()

        # return the newly minted timeline id
        return timeline

# END getTimeline()
# ========================================================================================================= #



# ========================================================================================================= #
# getTransID                                                                                                #
#    this method will read the transaction ID(s) stored to disk, if present                                 #
#    RETURN a list of transIDs (return empty list when no trans ID is found)                                #
# ========================================================================================================= #
def getTransID():

    # filename to keep the transaction ID
    filename = "transID"
    transIDs = []

    # Generate path to keep the transaction ID
    full_path = os.path.expanduser(os.path.join("~", ".rtm", api_key, filename))

    # read transaction ID from disk
    try:
        f = open(full_path, "r")
        transIDs = f.readlines()
        f.close()

        for i in range(len(transIDs)):
            transIDs[i] = transIDs[i].strip()

    except IOError:
        transIDs = []

    # return the transaction ID
    return transIDs

# END getTransID()
# ========================================================================================================= #



# ========================================================================================================= #
# writeTransID <transaction ID>                                                                             #
#    this method will write the specified transaction ID to disk    (currently replacing the past one)      #
# ========================================================================================================= #
def writeTransID(transID, multi=""):

    # filename to keep the transaction ID
    filename = "transID"

    # Generate path to keep the transaction ID
    full_path = os.path.expanduser(os.path.join("~", ".rtm", api_key, filename))

    # clear old transIDs if "startMulti" flag is sent
    if transID == "startMulti":
        f = open(full_path, "w")
        f.close()

    else:

        # if multi, append new trans id to end of file
        if multi == "true":
            f = open(full_path, "a")
            f.write(transID+"\n")
            f.close()

        # otherwise, write the trans id to file (replacing old one)
        else:
            f = open(full_path, "w")
            f.write(transID+"\n")
            f.close()

# END writeTransID()
# ========================================================================================================= #



# ========================================================================================================= #
# genLookupTable                                                                                            #
#    this method will generate a lookup table in order to give an index value to all tasks.  The tasks'     #
#    id will be used to uniquely identify each task                                                         #
#    GLOBAL lookup_table={} : the dictionary used as the index                                              #
# ========================================================================================================= #
def genLookupTable():

    # request the tasks from rtm (grouped by list)
    tasks_by_list_t = my_rtm.tasks.getList()
    tasks_by_list = tasks_by_list_t.tasks

    # dictionary lookup table and key
    global lookup_table
    n = 1

    # for each list...
    for lists in tasks_by_list.list:

        if hasattr(lists, "taskseries"):

            # when there are multiple taskseries in a list...
            if isinstance(lists.taskseries, list):

                # cycle through each taskseries in the list...
                for series in lists.taskseries:

                    # when there are multiple tasks in a taskseries (recurring tasks)...
                    if isinstance(series.task, list):
                        for idx in range(0, len(series.task)):
                            lookup_table[n] = series.task[idx].id
                            n=n+1

                    # when there is only 1 task in a taskseries...
                    else:
                        lookup_table[n] = series.task.id
                        n=n+1


            # when there is only 1 taskseries in a list...
            else:

                series = lists.taskseries

                # when there are multiple tasks in a taskseries (recurring tasks)...
                if isinstance(series.task, list):
                    for idx in range(0, len(series.task)):
                        lookup_table[n] = series.task[idx].id
                        n=n+1

                # when there is only 1 task in a taskseries...
                else:
                    lookup_table[n] = series.task.id
                    n=n+1

# END genLookupTable()
# ========================================================================================================= #



# ========================================================================================================= #
# getLookupTable() <index> or <task id>                                                                     #
#    this method will return the task's id when given an index, or the index when given the task id.        #
#    RETURN <task id> or <index>                                                                            #
# ========================================================================================================= #
def getLookupTable(index="", id=""):

    # genereate the lookup table, if necessary
    global lookup_table
    if lookup_table == {}:
        genLookupTable()

    # return the task id, given the index number
    if index != "":
        return lookup_table[int(index)]

    # return the index number, given the task id
    elif id != "":
        for i in range(len(lookup_table)):
            if lookup_table[i+1] == id:
                return i+1

# END getLookupTable()
# ========================================================================================================= #



# ========================================================================================================= #
# getList <id> or <name>                                                                                    #
#    this method will lookup a given list id number and it's associated name                                #
#    RETURN either the list name (given its id) or the list id (given its name)                             #
# ========================================================================================================= #
def getList(id="", name=""):

    # CREATE A DICTIONARY OF LIST ID's AND LIST NAMES
    global lists


    # if lists is empty, request data from RTM
    if len(lists) == 0:

        # create a list of the rtm list elements
        lists_elem_t = my_rtm.lists.getList()
        lists_elem = lists_elem_t.lists.list

        # create a dictionary using the id as keys with the names
        for l in lists_elem:
            lists[l.id] = l.name


    # return the list name, when given the id
    if id != "":
        return lists[id]

    # return the id, when given the name
    elif name != "":
        for iter_id, iter_name in lists.iteritems():
            if iter_name == name:
                return iter_id

    # list not found...
    display("ERROR: List " + id + name + " not found")
    sys.exit(2)


# END getList()
# ========================================================================================================= #



# ========================================================================================================= #
# getTasks                                                                                                  #
#    Generate a nested list of all of the RTM tasks including the follow properties for each task:          #
#        - Taskseries ID    = taskseries_id      [*][0]                                                     #
#        - Task ID          = task_id            [*][1]                                                     #
#        - Task Name        = task_name          [*][2]                                                     #
#        - Task Priority    = task_pri           [*][3]                                                     #
#        - Task Due Date    = task_due           [*][4]                                                     #
#        - List Name        = list_name          [*][5]                                                     #
#        - List ID          = list_id            [*][6]                                                     #
#        - Complete Date    = task_comp          [*][7]                                                     #
#        - Tags             = tags[]             [*][8][#]                                                  #
#        - Number of Notes  = notes_num          [*][9]                                                     #
#        - Task URL         = task_url           [*][10]                                                    #
#    GLOBAL tasks[]: a nested list of all tasks and their properties                                        #
# ========================================================================================================= #
def getTasks(filterString=""):

    # CREATE A 2D ARRAY OF TASKS WITH THEIR PROPERTIES:
    global tasks
    tasks = []

    # get the root of the task element tree
    root = my_rtm.tasks.getList(filter=filterString)

    if hasattr(root.tasks, "list"):

        # cycle through each task series and gather all required data
        for lists in root.tasks.list:

            if hasattr(lists, "taskseries"):

                # When there are multiples taskseries in the list...
                if isinstance(lists.taskseries, list):

                    # cycle through each task in the current list...
                    for series in lists.taskseries:
                        task = series.task


                        # TASKSERIES PROPERTIES

                        taskseries_id = series.id
                        task_name = series.name
                        task_url = series.url

                        if series.tags == []:
                            tags = []
                        else:
                            if isinstance(series.tags.tag, list):
                                tags = series.tags.tag
                            else:
                                tags = [series.tags.tag]


                        if series.notes == []:
                            notes_num = 0
                        else:
                            if isinstance(series.notes.note, list):
                                notes_num = len(series.notes.note)
                            else:
                                notes_num = 1


                        # TASK PROPERTIES

                        # if there is more than one task in the taskseries (recurring tasks)...
                        if isinstance(task, list):
                            idx = 0
                            task_id = task[idx].id
                            task_pri = task[idx].priority
                            task_due = task[idx].due
                            task_comp = task[idx].completed

                        # when there is only one task in the taskseries...
                        else:
                            task_id = task.id
                            task_pri = task.priority
                            task_due = task.due
                            task_comp = task.completed


                        # LIST PROPERTIES

                        list_id = lists.id
                        list_name = getList(id=list_id)

                        # Add task properties to the nested list
                        tasks.append([taskseries_id, task_id, task_name, task_pri, task_due, list_name, list_id, task_comp, tags, notes_num, task_url])



                # When there is only one taskseries in the list
                else:
                    series = lists.taskseries
                    task = series.task


                    # TASKSERIES PROPERTIES

                    taskseries_id = series.id
                    task_name = series.name
                    task_url = series.url

                    if series.tags == []:
                        tags = []
                    else:
                        if type(series.tags.tag) == list:
                            tags = series.tags.tag
                        else:
                            tags = [series.tags.tag]

                    if series.notes == []:
                        notes_num = 0
                    else:
                        if isinstance(series.notes.note, list):
                            notes_num = len(series.notes.note)
                        else:
                            notes_num = 1


                    # TASK PROPERTIES

                    # if there is more than one task in the taskseries (recurring tasks)...
                    if isinstance(task, list):
                        idx = 0
                        task_id = task[idx].id
                        task_pri = task[idx].priority
                        task_due = task[idx].due
                        task_comp = task[idx].completed

                    # when there is only one task in the taskseries...
                    else:
                        task_id = task.id
                        task_pri = task.priority
                        task_due = task.due
                        task_comp = task.completed


                    # LIST PROPERTIES

                    list_id = lists.id
                    list_name = getList(id=list_id)

                    # Add task properties to the nested list
                    tasks.append([taskseries_id, task_id, task_name, task_pri, task_due, list_name, list_id, task_comp, tags, notes_num, task_url])


            # When there are no taskseries in the current list...
            else:
                pass


# END getTasks()
# ========================================================================================================= #



# ========================================================================================================= #
# getTask <index>                                                                                           #
#   this method will return task properties: taskseries id, task id, and list id for a specified task index #
#   RETURN (task id, taskseries id, list id) as strings                                                     #
# ========================================================================================================= #
def getTask(index):

    # get task details: task id, taskseries id, list id

    # use the lookuptable to get the task id
    task_id = getLookupTable(index=index)

    # load all tasks to find the one we need
    # TODO: this takes too long...find a way to load fewer tasks (or better yet, just the one we need)
    getTasks()

    # search through the tasks looking for our task id
    for i in range(len(tasks)):

        # when we find our task id, save its taskseries id and list id
        if tasks[i][1] == task_id:
            taskseries_id = tasks[i][0]
            list_id = tasks[i][6]

    # return our findings
    return (task_id, taskseries_id, list_id)

# END getTask()
# ========================================================================================================= #



# ========================================================================================================= #
# ls <filter>                                                                                               #
#   Print a list of all of the tasks sorted first by list, then completed, pri, due date, and then task     #
#   name.  The task list can be optionally filtered by RTM's built-in search filters.                       #
# ========================================================================================================= #
def ls(filterString=""):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # filter out completed tasks, if requested
    if DISP_COMP == 0:
        filterString = filterString + " status:incomplete"

    # get the tasks
    getTasks(filterString=filterString)

    # sort tasks by task list (5), then completed (7), priority (3), due date (4), and task name (2)
    global tasks

    tasks = sorted(tasks, key=itemgetter(3,4,5,7,2))

    # initial list heading
    current_list_name = ""

    # cycle through each task item
    for i in range(len(tasks)):

        # if the task item is in a new list...print the new list name
        #if tasks[i][5] != current_list_name:
        #    current_list_name = tasks[i][5]
        #    display("")

        #    if PLAIN == 1:
        #        display("  " + current_list_name + ":")
        #    else:
        #        display("  " + COLOR_LIST + current_list_name + ":" + COLOR_RESET)

        # print task index value, padded with zeros (depending on # of tasks)
        #if len(tasks) < 100:
        #    display("%02d " % getLookupTable(id=tasks[i][1]), 0)
        #elif len(tasks) < 1000:
        #    display("%03d " % getLookupTable(id=tasks[i][1]), 0)
        #elif len(tasks) < 10000:
        #    display("%04d " % getLookupTable(id=tasks[i][1]), 0)
        #else:
        #    display("%02d " % getLookupTable(id=tasks[i][1]), 0)

        # if task is completed...
        if tasks[i][7] != "":

            # print an 'x' instead of priority
            display(" x  " + tasks[i][2], 0)

            # print task url, if any
            if tasks[i][10]:
                display(" [" + tasks[i][10] + "]", 0)

            # print any notes indicators, if requested
            if DISP_NOTES == 1:
                for j in range(tasks[i][9]):
                   display("*", 0)

            # print the tags, if any
            if (len(tasks[i][8]) != 0) and (DISP_TAGS == 1):
                for j in range(len(tasks[i][8])):
                   display(" #" + tasks[i][8][j], 0)

            # get the completed date as a string
            date = str(tasks[i][7])

            # convert the date into a datetime object
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc).astimezone(Local)

            # print the completed date
            display(" x " + weekdays[date.weekday()] + " " + str(date)[5:10])

        # for incomplete tasks...
        else:
            # print the due date, if it has one and in color, if desired
            # has due date [4]
            if tasks[i][4] != "":

                # get the due date as a string
                date = str(tasks[i][4])

                # convert the date into a datetime object
                duedate = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ") #.replace(tzinfo=utc).astimezone(Local)

                nowdate = datetime.now()

                datedelta = duedate - nowdate

                # for plain output...
                if PLAIN == 1:
                    #display("| " + weekdays[date.weekday()] + " " + str(date)[5:10], 0)
                    display("<tr><td style=\"text-align:right\">" + str(datedelta.days + 1) + ":</td>", 0)

                # for colored output...
                else:
                   display(COLOR_DUE + '| ' + weekdays[date.weekday()] + " " + str(date)[5:10] + COLOR_RESET, 0)

            # print the priority, if present, and the task in color, if desired
            if tasks[i][3] != "N":

                # for plain output..
                if PLAIN == 1:
                    #display("(" + tasks[i][3] + ") " + tasks[i][2], 0)
                    display("<td>" + tasks[i][2] + "</td></tr>", 0)

                    # print url, if any
                    if tasks[i][10]:
                        display(" [" + tasks[i][10] + "]", 0)

                # for colored output...
                else:
                    if tasks[i][3] == "1":
                        display(COLOR_PRI1 + '(' + tasks[i][3] + ') ' + tasks[i][2], 0)
                    elif tasks[i][3] == "2":
                        display(COLOR_PRI2 + '(' + tasks[i][3] + ') ' + tasks[i][2], 0)
                    elif tasks[i][3] == "3":
                        display(COLOR_PRI3 + '(' + tasks[i][3] + ') ' + tasks[i][2], 0)

                    # print url, if any
                    if tasks[i][10]:
                        display(" [" + tasks[i][10] + "]", 0)

            # indent non-prioritized tasks further
            else:
                display("<tr><td>" + tasks[i][2] + "</td></tr>", 0)

                # print task url, if any
                if tasks[i][10]:
                    display(" [" + tasks[i][10] + "]", 0)


            # print notes indicator, if requested
            if DISP_NOTES == 1:
                for j in range(tasks[i][9]):
                    display("*", 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            display(" ", 0)

            # print the tags, if any
            # if (len(tasks[i][8]) != 0) and (DISP_TAGS == 1):
            #
            #     # for plain output...
            #     if PLAIN == 1:
            #         for j in range(len(tasks[i][8])):
            #             display("#" + tasks[i][8][j] + " ", 0)
            #
            #     # for colored output...
            #     else:
            #         display(COLOR_TAG, 0)
            #         for j in range(len(tasks[i][8])):
            #            display("#" + tasks[i][8][j] + " ", 0)
            #         display(COLOR_RESET, 0)



            # print new line
            display("")

    display("")

# END ls()
# ========================================================================================================= #



# ========================================================================================================= #
# lsp <filter>                                                                                              #
#   Print a list of all of the tasks sorted first by completed, then priority, task list, due date and      #
#   then by task name.  The task list can be optionally filtered using RTM's built-in search filters.       #
# ========================================================================================================= #
def lsp(filterString=""):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # filter out completed tasks, if requested
    if DISP_COMP == 0:
        filterString = filterString + " status:incomplete"

    # get the tasks
    getTasks(filterString=filterString)

    # sort tasks by completion, priority, task list, due date, then by task name
    global tasks
    tasks = sorted(tasks, key=itemgetter(7,3,5,4,2))


    # parse through each task
    for i in range(len(tasks)):

        # print task index value, padded with zeros (depending on # of tasks)
        if len(tasks) < 100:
            display("%02d " % getLookupTable(id=tasks[i][1]), 0)
        elif len(tasks) < 1000:
            display("%03d " % getLookupTable(id=tasks[i][1]), 0)
        elif len(tasks) < 10000:
            display("%04d " % getLookupTable(id=tasks[i][1]), 0)
        else:
            display("%02d " % getLookupTable(id=tasks[i][1]), 0)


        # for completed tasks...
        if tasks[i][7] != "":

            # print an "x" instead of priority and then the task list and name
            display(" x  " + tasks[i][5] + ": " + tasks[i][2], 0)

            # print task url, if any
            if tasks[i][10]:
                display(" [" + tasks[i][10] + "]", 0)

            # print notes indicator, if requested
            if DISP_NOTES == 1:
                for j in range(tasks[i][9]):
                    display("*", 0)

            # print the tags, if any
            if (len(tasks[i][8]) != 0) and (DISP_TAGS == 1):
                for j in range(len(tasks[i][8])):
                    display(" #" + tasks[i][8][j], 0)

            # get the completed date as a string
            date = str(tasks[i][7])

            # convert the date into a datetime object
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc).astimezone(Local)

            # print the completed date
            display(" x " + weekdays[date.weekday()] + " " + str(date)[5:10])


        # for uncompleted tasks..
        else:

            # print the priority and the task's list and task in color, if desired
            if tasks[i][3] != "N":

                # for plain output..
                if PLAIN == 1:
                    display("(" + tasks[i][3] + ") " + tasks[i][5] + ": " + tasks[i][2], 0)

                    # print task url, if any
                    if tasks[i][10]:
                        display(" [" + tasks[i][10] + "]", 0)

                # for colored output...
                else:
                    if tasks[i][3] == "1":
                        display(COLOR_PRI1 + "(" + tasks[i][3] + ") " + COLOR_LIST + tasks[i][5] + ":" + COLOR_PRI1 + " " + tasks[i][2], 0)
                    elif tasks[i][3] == "2":
                        display(COLOR_PRI2 + "(" + tasks[i][3] + ") " + COLOR_LIST + tasks[i][5] + ":" + COLOR_PRI2 + " " + tasks[i][2], 0)
                    elif tasks[i][3] == "3":
                        display(COLOR_PRI3 + "(" + tasks[i][3] + ") " + COLOR_LIST + tasks[i][5] + ":" + COLOR_PRI3 + " " + tasks[i][2], 0)

                    # print task url, if any
                    if tasks[i][10]:
                        display(" [" + tasks[i][10] + "]", 0)

            # when there is no priority, indent more and print the list and task
            else:
                display("    " + COLOR_LIST + tasks[i][5] + ":" + COLOR_RESET + " " + tasks[i][2], 0)

                # print task url, if any
                if tasks[i][10]:
                    display(" [" + tasks[i][10] + "]", 0)

            # print the notes indicator, if requested
            if DISP_NOTES == 1:
                for j in range(tasks[i][9]):
                    display("*", 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            display(" ", 0)

            # print the tags, if any
            if (len(tasks[i][8]) != 0) and (DISP_TAGS == 1):

                # for plain output...
                if PLAIN == 1:
                    for j in range(len(tasks[i][8])):
                        display("#" + tasks[i][8][j] + " ", 0)

                # for colored output...
                else:
                    display(COLOR_TAG, 0)
                    for j in range(len(tasks[i][8])):
                        display("#" + tasks[i][8][j] + " ", 0)
                    display(COLOR_RESET, 0)

            # print the due date, if it has one and in color, if desired
            if tasks[i][4] != "":

                # get the due date as a string
                date = str(tasks[i][4])

                # convert the date into a datetime object
                date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc).astimezone(Local)

                # for plain output...
                if PLAIN == 1:
                    display("| " + weekdays[date.weekday()] + " " + str(date)[5:10])

                # for colored output...
                else:
                    display(COLOR_DUE + '| ' + weekdays[date.weekday()] + " " + str(date)[5:10] + COLOR_RESET)

            # print a newline if there's no due date
            else:
                display("")

    display("")
# END lsp()
# ========================================================================================================= #



# ========================================================================================================= #
# lsd <filterString>                                                                                        #
#    Print a list of all of the tasks sorted first by date, then priority and then by task name.  The tasks #
#    can be optionally filtered using RTM's built in filter.                                                #
# ========================================================================================================= #
def lsd(filterString=""):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # filter out completed tasks, if requested
    if DISP_COMP == 0:
        filterString = filterString + " status:incomplete"

    # get the tasks
    getTasks(filterString=filterString)

    # sort tasks by task due date, then completed, priority, and task name
    global tasks
    tasks = sorted(tasks, key=itemgetter(4,7,3,2))

    # initial list heading
    current_due_date = ""

    # cycle through each task item
    for i in range(len(tasks)):

        # if the task due date is new...print the new due date
        if tasks[i][4] != current_due_date:
            current_due_date = tasks[i][4]

            # get the due date as a string
            date = str(tasks[i][4])

            # convert the date into a datetime object
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc).astimezone(Local)

            # for plain output...
            if PLAIN == 1:
                display("")
                display("   " + weekdays[date.weekday()] + " " + str(date)[5:10])

            # for colored output...
            else:
                display("")
                display(COLOR_DUE + '   ' + weekdays[date.weekday()] + " " + str(date)[5:10] + COLOR_RESET)


        # print task index value, padded with zeros (depending on # of tasks)
        if len(tasks) < 100:
            display("%02d" % getLookupTable(id=tasks[i][1]), 0)
        elif len(tasks) < 1000:
            display("%03d" % getLookupTable(id=tasks[i][1]), 0)
        elif len(tasks) < 10000:
            display("%04d" % getLookupTable(id=tasks[i][1]), 0)
        else:
            display("%02d" % getLookupTable(id=tasks[i][1]), 0)


        # if task is completed...
        if tasks[i][7] != "":
            # print an 'x' instead of priority and then the list name and task
            display("  x  " + tasks[i][5] + ": " + tasks[i][2], 0)

            # print task url, if any
            if tasks[i][10]:
                display(" [" + tasks[i][10] + "]", 0)

            # print the notes indicator, if requested
            if DISP_NOTES == 1:
                for j in range(tasks[i][9]):
                    display("*", 0)

            # print the tags, if any
            if (len(tasks[i][8]) != 0) and (DISP_TAGS == 1):
                for j in range(len(tasks[i][8])):
                    display(" #" + tasks[i][8][j], 0)

            # get the completed date as a string
            date = str(tasks[i][7])

            # convert the date into a datetime object
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc).astimezone(Local)

            # print the completed date
            display(" x " + weekdays[date.weekday()] + " " + str(date)[5:10])


        # for uncompleted tasks...
        else:

            # print the priority, if present, and the task list and name in color, if desired
            if tasks[i][3] != "N":

                # for plain output..
                if PLAIN == 1:
                    display(" (" + tasks[i][3] + ") " + tasks[i][5] + ": " + tasks[i][2], 0)


                # for colored output...
                else:
                    if tasks[i][3] == "1":
                        display(COLOR_PRI1 + ' (' + tasks[i][3] + ') ' + COLOR_LIST + tasks[i][5] + ":" + COLOR_PRI1 + " " + tasks[i][2], 0)
                    elif tasks[i][3] == "2":
                        display(COLOR_PRI2 + ' (' + tasks[i][3] + ') ' + COLOR_LIST + tasks[i][5] + ":" + COLOR_PRI2 + " " + tasks[i][2], 0)
                    elif tasks[i][3] == "3":
                        display(COLOR_PRI3 + ' (' + tasks[i][3] + ') ' + COLOR_LIST + tasks[i][5] + ":" + COLOR_PRI3 + " " + tasks[i][2], 0)


            # indent non-prioritized tasks further
            else:
                display("     " + COLOR_LIST + tasks[i][5] + ":" + COLOR_RESET + " " + tasks[i][2], 0)


            # print task url, if any
            if tasks[i][10]:
                display(" [" + tasks[i][10] + "]", 0)

            # print the notes indicator, if requested
            if DISP_NOTES == 1:
                for j in range(tasks[i][9]):
                     display("*", 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            # print the tags, if any
            if (len(tasks[i][8]) != 0) and (DISP_TAGS == 1):

                # for plain output...
                if PLAIN == 1:
                    for j in range(len(tasks[i][8])):
                        display(" #" + tasks[i][8][j], 0)

                # for colored output...
                else:
                    display(COLOR_TAG, 0)
                    for j in range(len(tasks[i][8])):
                        display(" #" + tasks[i][8][j], 0)
                    display(COLOR_RESET, 0)

            display("")

    display("")

# END lsd()
# ========================================================================================================= #



# ========================================================================================================= #
# add <task>                                                                                                #
#    Add a task given the optional task info as an argument.  If no argument is given, the user will be     #
#   prompted to enter each item separately.                                                                 #
# ========================================================================================================= #
def add(task):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # replace 'p:' with '!' for the priority
    task = re.sub(r'(p:)([0-3])', r'!\2', task)

    # replace 'l:' with '#" for the list
    task = task.replace("l:","#")

    # replace 't:' with '#" for the tags
    task = task.replace("t:","#")

    display("adding task: " + task + "...")

    # get a timeline id
    timeline = getTimeline()

    # add the task
    added_task = my_rtm.tasks.add(timeline=timeline, name=task, parse=1)

    # write the transaction ID if it is undoable
    if added_task.transaction.undoable == "1":
        writeTransID(added_task.transaction.id)
    else:
        writeTransID("NA")

# END add()
# ========================================================================================================= #



# ========================================================================================================= #
# madd                                                                                                      #
#    Have the user enter multiple tasks at a prompt before submitting them to RTM.  Enter a blank line to   #
#    end the prompt.                                                                                        #
# ========================================================================================================= #
def madd():

    # Give instructions
    display("Enter each task in the format: task name due date p:priority l:list t:tag")
    display("Enter a blank line when finished.")
    display("")

    # The task stack
    stack=[]
    done=0

    while done == 0:
        new_task = get_input("New Task: ")

        # if a blank line was entered, signal end of input
        if new_task == "":
            done = 1

        # otherwise parse and append the new task to the stack
        else:
            # replace 'p:' with '!' for the priority and 'l:' with '#' for the list
            new_task = re.sub(r'(p:)([0-3])', r'!\2', new_task)
            new_task = new_task.replace("l:","#")
            new_task = new_task.replace("t:","#")

            # append to the task stack
            stack.append(new_task)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting tasks to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # signal start of multi-tasks for transaction IDs
    writeTransID("startMulti")

    # submit the tasks to RTM
    while len(stack) != 0:
        task=stack.pop()
        display("adding task: " + task + "...")
        added_task = my_rtm.tasks.add(timeline=timeline, name=task, parse=1)

        # write the transaction ID if it is undoable
        if added_task.transaction.undoable == "1":
            writeTransID(added_task.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END madd()
# ========================================================================================================= #



# ========================================================================================================= #
# edit                                                                                                      #
#    This method will change the name of the task specified by its index number                             #
# ========================================================================================================= #
def edit(index, newTaskName):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # if newTaskName is a list, convert to a single string
    if type(newTaskName) == list:
        # print(len(newTaskName))
        temp = ""
        for i in range(len(newTaskName)):
            temp = temp + newTaskName[i]
            if i < len(newTaskName)-1:
                temp = temp + " "
        newTaskName = temp

    # use the lookuptable to get the task id
    task_id = getLookupTable(index=index)

    # get the previous task information
    getTasks()

    # find the proper task
    for i in range(len(tasks)):

        # when we find our task id, save its taskseries id and list id
        if tasks[i][1] == task_id:
            old_task_name = tasks[i][2]
            taskseries_id = tasks[i][0]
            list_id = tasks[i][6]

    display("renaming task #" + index + " from '" + str(old_task_name) + "' to '" + str(newTaskName) + "'...")

    # get the timeline
    timeline = getTimeline()

    # edit the task
    edit_task = my_rtm.tasks.setName(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id, name=newTaskName)

    # write the transaction ID if it is undoable
    if edit_task.transaction.undoable == "1":
        writeTransID(edit_task.transaction.id)
    else:
        writeTransID("NA")

# END edit()
# ========================================================================================================= #



# ========================================================================================================= #
# mdit                                                                                                      #
#    This method will prompt the user for task indices and new names to rename tasks                        #
# ========================================================================================================= #
def medit():

    # Give instructions
    display("Enter each task index number and new task name (separately) at the prompts below to rename the tasks.")

    if ENABLE_READLINE == 1:
        import readline
        display("Press the up arrow to load the old task name")

    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The entered arguments
    list_args=[]
    done=0

    # Get the task properties, if readline is enabled, to add to readline history
    if ENABLE_READLINE == 1:
        if MODE != "interactive":
            login()
        getTasks()

    # prompt user for task #
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # otherwise append the task index number to the list
        else:

            if ENABLE_READLINE == 1:
                # get the old task name
                task_id = getLookupTable(index=index)

                # find the proper task
                for i in range(len(tasks)):

                    # when we find our task id, save its taskseries id and list id
                    if tasks[i][1] == task_id:
                        task_id = tasks[i][1]
                        taskseries_id = tasks[i][0]
                        list_id = tasks[i][6]
                        old_task_name = tasks[i][2]
                        readline.add_history(old_task_name)

            new_name = get_input("New Name: ")

            task = [task_id, taskseries_id, list_id, old_task_name, new_name]
            list_args.append(task)


    # login to RTM and authenticate the user, if not done already
    if ENABLE_READLINE == 0:
        if MODE != "interactive":
            login()

    display("")

    # get a timeline id
    timeline = getTimeline()

    # signal the start of a multi function
    writeTransID("startMulti")

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the task array from the list
        task = list_args.pop()

        task_id = task[0]
        taskseries_id = task[1]
        list_id = task[2]
        old_name = task[3]
        new_name = task[4]

        # now, submit the changes to RTM
        display("renaming task #" + index + " from '" + str(old_name) + "' to '" + str(new_name) + "'...")

        # submit the changes to RTM
        edit_task = my_rtm.tasks.setName(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id, name=new_name)

        # write the transaction ID if it is undoable
        if edit_task.transaction.undoable == "1":
            writeTransID(edit_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END medit()
# ========================================================================================================= #



# ========================================================================================================= #
# complete <task index>                                                                                     #
#    This method will mark the task specified by the task index as complete                                 #
# ========================================================================================================= #
def complete(index):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("marking task #" + index + " as complete...")

    # get the timeline
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # complete the task
    comp_task = my_rtm.tasks.complete(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id)

    # write the transaction ID if it is undoable
    if comp_task.transaction.undoable == "1":
        writeTransID(comp_task.transaction.id)
    else:
        writeTransID("NA")

# END complete()
# ========================================================================================================= #


# ========================================================================================================= #
# mcomplete                                                                                                 #
#    Have the user enter multiple tasks to mark as complete at a prompt before submitting them to RTM.      #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def mcomplete():

    # Give instructions
    display("Enter each task index number (separately) at the prompt below to mark these tasks as complete.")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0

    # prompt user for task #
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # otherwise append the task index number to the list
        else:
            list_args.append(index)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting completed tasks to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the task index from the list
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index))

    # signal the start of a multi-function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("marking task #" + props[3] + " as complete...")

        # submit the changes to RTM
        comp_task = my_rtm.tasks.complete(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2])

        # write the transaction ID if it is undoable
        if comp_task.transaction.undoable == "1":
            writeTransID(comp_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END mcomplete()
# ========================================================================================================= #



# ========================================================================================================= #
# delete <task index>                                                                                       #
#    This method will delete the task specified by the task index                                           #
# ========================================================================================================= #
def delete(index):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # when no task is given, prompt the user to enter the task index
    if index == "":
        index = get_input("Task #: ")

    display("deleting task #" + index + "...")

    # get the timeline
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # delete the task
    del_task = my_rtm.tasks.delete(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id)

    # write the transaction ID if it is undoable
    if del_task.transaction.undoable == "1":
        writeTransID(del_task.transaction.id)
    else:
        writeTransID("NA")

# END delete()
# ========================================================================================================= #



# ========================================================================================================= #
# mdelete                                                                                                   #
#    Have the user enter multiple tasks to delete at a prompt before submitting them to RTM.                #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def mdelete():

    # Give instructions
    display("Enter each task index number (separately) at the prompt below to delete these tasks.")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0


    # prompt user for task #
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # otherwise append the task index number to the list
        else:
            list_args.append(index)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting deleted tasks to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the task index from the list
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index))

    # signal the start of a multi-function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("deleting task #" + props[3] + "...")

        # set the priority of the task
        del_task = my_rtm.tasks.delete(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2])

        # write the transaction ID if it is undoable
        if del_task.transaction.undoable == "1":
            writeTransID(del_task.transaction.id, multi="true")
        else:
            writeTransID("NA")


# END mdelete()
# ========================================================================================================= #



# ========================================================================================================= #
# setPriority <task index> <pri>                                                                            #
#    This method will set the task specified by its task index to the specified priority    (1,2,3 or 0)    #
# ========================================================================================================= #
def setPriority(index, pri="1"):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("setting the priority of task #" + index + " to " + pri + "...")

    # get the timeline
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # set the priority of the task
    pri_task = my_rtm.tasks.setPriority(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id, priority=pri)

    # write the transaction ID if it is undoable
    if pri_task.transaction.undoable == "1":
        writeTransID(pri_task.transaction.id)
    else:
        writeTransID("NA")

# END setPriority()
# ========================================================================================================= #



# ========================================================================================================= #
# msetPriority                                                                                              #
#    Have the user enter multiple tasks and new priorities at a prompt before submitting them to RTM.       #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def msetPriority():

    # Give instructions
    display("Enter each task index number followed by its new priority (1,2,3 or 0 to remove).")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0


    # prompt user for task # and priorities
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # append arguments to the list
        else:
            new_pri = get_input("New Pri: ")
            list_args.append(index)
            list_args.append(new_pri)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting new priorities to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the new prioritiy and task index from the list
        new_pri = list_args.pop()
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, new_pri, task_index))

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("setting the priority of task #" + props[4] + " to " + props[3] + "...")

        # set the priority of the task
        pri_task = my_rtm.tasks.setPriority(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2], priority=props[3])

        # write the transaction ID if it is undoable
        if pri_task.transaction.undoable == "1":
            writeTransID(pri_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END msetPriority()
# ========================================================================================================= #



# ========================================================================================================= #
# move <task index> <new list name>                                                                         #
#    This method will move the task specified by its index to the specified new list                        #
# ========================================================================================================= #
def move(index, list):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("moving task #" + index + " to list " + list + "...")

    # get the timeline
    timeline = getTimeline()

    # get the new list id
    to_list_id = getList(name=list)

    # get the task id, taskseries id and old list id
    (task_id, taskseries_id, from_list_id) = getTask(index)

    # move the task
    moved_task = my_rtm.tasks.moveTo(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, from_list_id=from_list_id, to_list_id=to_list_id)

    # write the transaction ID if it is undoable
    if moved_task.transaction.undoable == "1":
        writeTransID(moved_task.transaction.id)
    else:
        writeTransID("NA")

# END move()
# ========================================================================================================= #



# ========================================================================================================= #
# mmove                                                                                                     #
#    Have the user enter multiple tasks and new lists at a prompt before submitting them to RTM.            #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def mmove():

    # Give instructions
    display("Enter each task index number followed by its new list at the following prompts.")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0

    # prompt user for task # and the new lists
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # append arguments to the list
        else:
            new_list = get_input("Move to: ")
            list_args.append(index)
            list_args.append(new_list)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting changes to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the new list name and task index from the list
        new_list_name = list_args.pop()
        task_index = list_args.pop()

        # get the new list id
        new_list_id = getList(name=new_list_name)

        # get the task id, taskseries id and old list id
        (task_id, taskseries_id, old_list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, old_list_id, new_list_id, task_index, new_list_name))

    # signal the start of a multi-function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("moving task #" + props[4] + " to list " + props[5] + "...")

        # move the task to the new list
        moved_task = my_rtm.tasks.moveTo(timeline=timeline, task_id=props[0], taskseries_id=props[1], from_list_id=props[2], to_list_id=props[3])

        # write the transaction ID if it is undoable
        if moved_task.transaction.undoable == "1":
            writeTransID(moved_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END mmove()
# ========================================================================================================= #



# ========================================================================================================= #
# setDueDate <task index> <due date>                                                                        #
#    This method will set the task specified by its task index to the RTM-parsed due date                   #
# ========================================================================================================= #
def setDueDate(index, due_date="today"):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("setting task #" + index + " as due: " + due_date + "...")

    # get the timeline
    timeline = getTimeline()

    # get the task id, taskseries id and old list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # move the task
    due_task = my_rtm.tasks.setDueDate(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id, due=due_date, parse=1)

    # write the transaction ID if it is undoable
    if due_task.transaction.undoable == "1":
        writeTransID(due_task.transaction.id)
    else:
        writeTransID("NA")

# END setDueDate()
# ========================================================================================================= #



# ========================================================================================================= #
# msetDueDate                                                                                               #
#    Have the user enter multiple tasks and new due dates at a prompt before submitting them to RTM.        #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def msetDueDate():

    # Give instructions
    display("Enter each task index number followed by its new due date at the following prompts.")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0

    # prompt user for task # and the new due date
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # append arguments to the list
        else:
            new_date = get_input("New Due Date: ")
            list_args.append(index)
            list_args.append(new_date)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting new due dates to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the new due date and task index from the list
        new_due_date = list_args.pop()
        task_index = list_args.pop()

        # get the task id, taskseries id and old list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, new_due_date, task_index))

    # signal the start of a multi-function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("setting the due date of task #" + props[4] + " to " + props[3] + "...")

        # move the task to the new list
        due_task = my_rtm.tasks.setDueDate(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2], due=props[3], parse=1)

        # write the transaction ID if it is undoable
        if due_task.transaction.undoable == "1":
            writeTransID(due_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END msetDueDate()
# ========================================================================================================= #



# ========================================================================================================= #
# uncomplete <task index>                                                                                   #
#    This method will uncomplete the task specified by its index                                            #
# ========================================================================================================= #
def uncomplete(index):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("uncompleting task #" + index + "...")

    # get the timeline
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # delete the task
    unc_task = my_rtm.tasks.uncomplete(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id)

    # write the transaction ID if it is undoable
    if unc_task.transaction.undoable == "1":
        writeTransID(unc_task.transaction.id)
    else:
        writeTransID("NA")

# END uncomplete()
# ========================================================================================================= #


# ========================================================================================================= #
# muncomplete                                                                                               #
#    Have the user enter multiple tasks to mark as uncomplete at a prompt before submitting them to RTM.    #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def muncomplete():

    # Give instructions
    display("Enter each task index number (separately) at the prompt below to mark these tasks as incomplete.")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0

    # prompt user for task #
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # otherwise append the task index number to the list
        else:
            list_args.append(index)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting incompleted tasks to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the task index from the list
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index))

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("marking task #" + props[3] + " as incomplete...")

        # submit the changes to RTM
        unc_task = my_rtm.tasks.uncomplete(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2])

        # write the transaction ID if it is undoable
        if unc_task.transaction.undoable == "1":
            writeTransID(unc_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END muncomplete()
# ========================================================================================================= #



# ========================================================================================================= #
# postpone <task index>                                                                                     #
#    This method will postpone the task specified by its index                                              #
# ========================================================================================================= #
def postpone(index):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("postponing task #" + index + "...")

    # get the timeline
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # delete the task
    post_task = my_rtm.tasks.postpone(timeline=timeline, task_id=task_id, taskseries_id=taskseries_id, list_id=list_id)

    # write the transaction ID if it is undoable
    if post_task.transaction.undoable == "1":
        writeTransID(post_task.transaction.id)
    else:
        writeTransID("NA")

# END postpone()
# ========================================================================================================= #



# ========================================================================================================= #
# mpostpone                                                                                                 #
#    Have the user enter multiple tasks to postpone at a prompt before submitting them to RTM.              #
#   Enter a blank line to end the prompt.                                                                   #
# ========================================================================================================= #
def mpostpone():

    # Give instructions
    display("Enter each task index number (separately) at the prompt below to postpone these tasks by one day.")
    display("Enter a blank line at the task prompt when finished.")
    display("")

    # The string of new priorities
    list_args=[]
    stack=[]
    done=0

    # prompt user for task #
    while done == 0:
        index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if index == "":
            done = 1

        # otherwise append the task index number to the list
        else:
            list_args.append(index)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting postponed tasks to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the task index from the list
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index))

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("postponing task #" + props[3] + "...")

        # submit the changes to RTM
        post_task = my_rtm.tasks.postpone(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2])

        # write the transaction ID if it is undoable
        if post_task.transaction.undoable == "1":
            writeTransID(post_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END mpostpone()
# ========================================================================================================= #



# ========================================================================================================= #
# addList <list name>                                                                                       #
#    Add a new list given the list name.                                                                    #
# ========================================================================================================= #
def addList(name):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("creating new list: " + name + "...")

    # get a timeline id
    timeline = getTimeline()

    # add the task
    new_list = my_rtm.lists.add(timeline=timeline, name=name)

    # write the transaction ID if it is undoable
    if new_list.transaction.undoable == "1":
        writeTransID(new_list.transaction.id)
    else:
        writeTransID("NA")

# END addList()
# ========================================================================================================= #



# ========================================================================================================= #
# maddList                                                                                                  #
#    Have the user enter multiple new lists a prompt before submitting them to RTM.  Enter a blank line to  #
#    end the prompt.                                                                                        #
# ========================================================================================================= #
def maddList():

    # Give instructions
    display("Enter each new list name at the prompt below.")
    display("Enter a blank line when finished.")
    display("")

    # The task stack
    stack=[]
    done=0

    while done == 0:
        new_list = get_input("New List Name: ")

        # if a blank line was entered, signal end of input
        if new_list == "":
            done = 1

        # otherwise parse and append the new task to the stack
        else:
            # append to the task stack
            stack.append(new_list)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting new lists to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # signal start of multi-tasks for transaction IDs
    writeTransID("startMulti")

    # submit the tasks to RTM
    while len(stack) != 0:
        list_name = stack.pop()
        display("creating new list: " + list_name + "...")
        created_list = my_rtm.lists.add(timeline=timeline, name=list_name)

        # write the transaction ID if it is undoable
        if created_list.transaction.undoable == "1":
            writeTransID(created_list.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END maddList()
# ========================================================================================================= #



# ========================================================================================================= #
# delList <list name>                                                                                       #
#    Delete the list specified by its name.                                                                 #
# ========================================================================================================= #
def delList(name):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("deleting list: " + name + "...")

    # get a timeline id
    timeline = getTimeline()

    # get the list id from the name
    list_id = getList(name=name)

    # add the task
    del_list = my_rtm.lists.delete(timeline=timeline, list_id=list_id)

    # write the transaction ID if it is undoable
    if del_list.transaction.undoable == "1":
        writeTransID(del_list.transaction.id)
    else:
        writeTransID("NA")

# END delList()
# ========================================================================================================= #



# ========================================================================================================= #
# mdelList                                                                                                  #
#    Have the user enter multiple lists to delete at a prompt before submitting them to RTM.  Enter a blank #
#    line to end the prompt.                                                                                #
# ========================================================================================================= #
def mdelList():

    # Give instructions
    display("Enter each list name to delete at the prompt below.")
    display("Enter a blank line when finished.")
    display("")

    # The task stack
    stack=[]
    done=0

    while done == 0:
        del_list = get_input("List Name: ")

        # if a blank line was entered, signal end of input
        if del_list == "":
            done = 1

        # otherwise parse and append the new task to the stack
        else:
            # append to the task stack
            stack.append(del_list)

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting lists to RTM for removal...")

    # get a timeline id
    timeline = getTimeline()

    # signal start of multi-tasks for transaction IDs
    writeTransID("startMulti")

    # submit the tasks to RTM
    while len(stack) != 0:

        # get the list name
        list_name = stack.pop()

        # get the list id
        list_id = getList(name=list_name)

        display("deleting list: " + list_name + "...")

        deleted_list = my_rtm.lists.delete(timeline=timeline, list_id=list_id)

        # write the transaction ID if it is undoable
        if deleted_list.transaction.undoable == "1":
            writeTransID(deleted_list.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END mdelList()
# ========================================================================================================= #



# ========================================================================================================= #
# renameList <old list name> <new list name>                                                                #
#    Renames the task list from <old list name> to <new list name>                                          #
# ========================================================================================================= #
def renameList(old_name, new_name):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("renaming list: " + old_name + " to " + new_name + "...")

    # get a timeline id
    timeline = getTimeline()

    # get the list id from the name
    old_list_id = getList(name=old_name)

    # add the task
    new_list = my_rtm.lists.setName(timeline=timeline, list_id=old_list_id, name=new_name)

    # write the transaction ID if it is undoable
    if new_list.transaction.undoable == "1":
        writeTransID(new_list.transaction.id)
    else:
        writeTransID("NA")

# END renameList()
# ========================================================================================================= #



# ========================================================================================================= #
# mrenameList                                                                                               #
#    Have the user enter multiple lists to rename at a prompt before submitting them to RTM.  Enter a blank #
#    line to end the prompt.                                                                                #
# ========================================================================================================= #
def mrenameList():

    # Give instructions
    display("Enter each old list name followed by its new name at the prompt below.")
    display("Enter a blank line when finished.")
    display("")

    # The task stack
    stack=[]
    done=0

    # prompt user for old and new list name
    while done == 0:
        old_name = get_input("Old List Name: ")

        # catch a blank line to signal the end of input
        if old_name == "":
            done = 1

        # append arguments to the list
        else:
            new_name = get_input("New List Name: ")
            stack.append(old_name)
            stack.append(new_name)


    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting list changes to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # signal start of multi-tasks for transaction IDs
    writeTransID("startMulti")

    # submit the tasks to RTM
    while len(stack) != 0:

        # get the new list name
        new_name = stack.pop()

        # get the old list name
        old_name = stack.pop()

        # get the old list id
        old_id = getList(name=old_name)

        display("renaming list: " + old_name + " to " + new_name + "...")

        new_list = my_rtm.lists.setName(timeline=timeline, list_id=old_id, name=new_name)

        # write the transaction ID if it is undoable
        if new_list.transaction.undoable == "1":
            writeTransID(new_list.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END mrenameList()
# ========================================================================================================= #



# ========================================================================================================= #
# addTags <task index> <comma separated list of tags>                                                       #
#    Adds the given tags to the specified task                                                              #
# ========================================================================================================= #
def addTags(index, tags):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("adding tags: " + tags + " to task #" + index + "...")

    # get a timeline id
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # add the new tags
    new_task = my_rtm.tasks.addTags(timeline=timeline, list_id=list_id, taskseries_id=taskseries_id, task_id=task_id, tags=tags)

    # write the transaction ID if it is undoable
    if new_task.transaction.undoable == "1":
        writeTransID(new_task.transaction.id)
    else:
        writeTransID("NA")

# END addTags()
# ========================================================================================================= #



# ========================================================================================================= #
# maddTags                                                                                                  #
#    Have the user enter multiple tasks and tags at a prompt before submitting them to RTM.  Enter a blank  #
#    line to end the prompt.                                                                                #
# ========================================================================================================= #
def maddTags():

    # Give instructions
    display("Enter each task followed by the tags to add to it at the prompt below.")
    display("Enter a blank line when finished.")
    display("")

    # The task stack
    list_args=[]
    stack=[]
    done=0

    # prompt user for old and new list name
    while done == 0:
        task_index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if task_index == "":
            done = 1

        # append arguments to the list
        else:
            tags = get_input("Tags: ")
            tags = tags.replace(" ",",")
            tags = tags.replace(",,",",")

            list_args.append(task_index)
            list_args.append(tags)


    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting new tags to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the new prioritiy and task index from the list
        new_tags = list_args.pop()
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index, new_tags))

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("adding tags: " + props[4] + " to task #" + props[3] + "...")

        # add new tags
        new_task = my_rtm.tasks.addTags(timeline=timeline, list_id=props[2], taskseries_id=props[1], task_id=props[0], tags=props[4])

        # write the transaction ID if it is undoable
        if new_task.transaction.undoable == "1":
            writeTransID(new_task.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END maddTags()
# ========================================================================================================= #



# ========================================================================================================= #
# delTags <task index> <comma separated list of tags>                                                       #
#    Removes the given tags from the specified task                                                         #
# ========================================================================================================= #
def delTags(index, tags):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("removing tags: " + tags + " from task #" + index + "...")

    # get a timeline id
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # remove the given tags
    new_task = my_rtm.tasks.removeTags(timeline=timeline, list_id=list_id, taskseries_id=taskseries_id, task_id=task_id, tags=tags)

    # write the transaction ID if it is undoable
    if new_task.transaction.undoable == "1":
        writeTransID(new_task.transaction.id)
    else:
        writeTransID("NA")

# END delTags()
# ========================================================================================================= #



# ========================================================================================================= #
# mdelTags                                                                                                  #
#    Have the user enter multiple tasks and tags to remove at a prompt before submitting them to RTM.       #
#    Enter a blank line to end the prompt.                                                                  #
# ========================================================================================================= #
def mdelTags():

    # Give instructions
    display("Enter each task followed by the tags to remove from it at the prompt below.")
    display("Enter a blank line when finished.")
    display("")

    # The task stack
    list_args=[]
    stack=[]
    done=0

    # prompt user for old and new list name
    while done == 0:
        task_index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if task_index == "":
            done = 1

        # append arguments to the list
        else:
            tags = get_input("Tags: ")
            tags = tags.replace(" ",",")
            tags = tags.replace(",,",",")

            list_args.append(task_index)
            list_args.append(tags)


    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting tags to remove to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the new prioritiy and task index from the list
        new_tags = list_args.pop()
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index, new_tags))

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("removing tags: " + props[4] + " to task #" + props[3] + "...")

        # remove tags
        new_task = my_rtm.tasks.removeTags(timeline=timeline, list_id=props[2], taskseries_id=props[1], task_id=props[0], tags=props[4])

        # write the transaction ID if it is undoable
        if new_task.transaction.undoable == "1":
            writeTransID(new_task.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END mdelTags()
# ========================================================================================================= #



# ========================================================================================================= #
# addNote <task index> <note title> <note body>                                                             #
#    Adds a note to the given task with the specified title and body                                        #
# ========================================================================================================= #
def addNote(index, title, body):

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("adding note to task # " + index + "...")

    # get a timeline id
    timeline = getTimeline()

    # get the task id, taskseries id and list id
    (task_id, taskseries_id, list_id) = getTask(index)

    # add the new tags
    rsp = my_rtm.tasksNotes.add(timeline=timeline, list_id=list_id, taskseries_id=taskseries_id, task_id=task_id, note_title=title, note_text=body)

    # write the transaction ID if it is undoable
    if rsp.transaction.undoable == "1":
        writeTransID(rsp.transaction.id)
    else:
        writeTransID("NA")

# END addNote()
# ========================================================================================================= #



# ========================================================================================================= #
# maddNote                                                                                                  #
#    Have the user enter multiple new notes before submitting them to RTM.  Enter a blank line to end the   #
#    prompt.                                                                                                #
# ========================================================================================================= #
def maddNote():

    # Give instructions
    display("Enter each task # followed by the note title and then the note body at the prompts below.")
    display("Enter a blank line for the task # when finished.")
    display("")

    # The task stack
    list_args=[]
    stack=[]
    done=0

    # prompt user for note titles and bodies
    while done == 0:
        task_index = get_input("Task #: ")

        # catch a blank line to signal the end of input
        if task_index == "":
            done = 1

        # append arguments to the list
        else:
            title = get_input("Title: ")
            display("Body: (Enter EOF/ctr-D to finish)")
            body = get_multi_input()

            list_args.append(task_index)
            list_args.append(title)
            list_args.append(body)


    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    display("")
    display("submitting new notes to RTM...")

    # get a timeline id
    timeline = getTimeline()

    # get task properties before submitting changes,
    # since the task index numbers may change after something is submitted to RTM
    while len(list_args) != 0:

        # get the each body, title and task index from the list
        note_body = list_args.pop()
        note_title = list_args.pop()
        task_index = list_args.pop()

        # get the task id, taskseries id and list id
        (task_id, taskseries_id, list_id) = getTask(task_index)

        # save all properties to the stack
        stack.append((task_id, taskseries_id, list_id, task_index, note_title, note_body))

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("adding note to task #" + props[3] + "...")

        # add new tags
        rsp = my_rtm.tasksNotes.add(timeline=timeline, list_id=props[2], taskseries_id=props[1], task_id=props[0], note_title=props[4], note_text=props[5])

        # write the transaction ID if it is undoable
        if rsp.transaction.undoable == "1":
            writeTransID(rsp.transaction.id, multi="true")
        else:
            writeTransID("NA", multi="true")

# END maddNote()
# ========================================================================================================= #



# ========================================================================================================= #
# delNote <task index>                                                                                      #
#    This method will display the title of the notes for the specified task, asking the user if it should   #
#    be deleted.                                                                                            #
# ========================================================================================================= #
def delNote(index=""):

    if MODE != "interactive":
        login()


    if index == "":
        index = get_input("Task #: ")


    display("Choose which notes to delete from the list below")
    display("")

    # get the task properties
    (task_id, taskseries_id, list_id) = getTask(index)

    # find the task
    root = my_rtm.tasks.getList()
    for lists in root.tasks.list:
        if hasattr(lists, "taskseries"):
            if isinstance(lists.taskseries, list):
                for series in lists.taskseries:
                    if series.id == taskseries_id:
                        series_elem = series
                        notes = series_elem.notes
            else:
                series = lists.taskseries
                if series.id == taskseries_id:
                    series_elem = series
                    notes = series_elem.notes


    if notes == []:
        display("This task has no notes")

    # Have the user choose which notes to delete
    else:
        stack=[]

        # get a timeline id
        timeline = getTimeline()

        # display the titles each note, prompt the user if it should be deleted
        if isinstance(notes.note, list):
            for note in notes.note:
                if ( note.title != "" ):
                    display("Title: " + note.title)
                else:
                    display("Body: " + getattr(note, "$t"))
                dn = get_input("Delete this note (y/n)? ")
                if (dn == "y" or dn == "Y" or dn == "yes" or dn == "Yes" or dn == "YES"):
                    stack.append(note.id)
                display("")

        else:
            note = notes.note

            if ( note.title != "" ):
                display("Title: " + note.title)
            else:
                display("Body: " + getattr(note, "$t"))
            dn = get_input("Delete this note (y/n)?")
            if (dn == "y" or dn == "Y" or dn == "yes" or dn == "Yes" or dn == "YES"):
                stack.append(note.id)
            display("")

        # loop through each note that was selected, and delete
        for i in range(len(stack)):
            display("Deleting note # " + stack[i] + "...")

            # delete the note
            rsp = my_rtm.tasksNotes.delete(timeline=timeline, note_id=stack[i])

            # write the transaction ID if it is undoable
            if rsp.transaction.undoable == "1":
                writeTransID(rsp.transaction.id, multi="true")
            else:
                writeTransID("NA", multi="true")

# END delNote()
# ========================================================================================================= #



# ========================================================================================================= #
# editNote <task index>                                                                                     #
#    This method will edit the note(s) (title and body) of the specified or entered task                    #
# ========================================================================================================= #
def editNote(index=""):

    # get a task index number, if not passed
    if index == "":
        index = get_input("Task #: ")

    if MODE != "interactive":
        login()

    if ENABLE_READLINE:
        import readline

    # get the task properties
    (task_id, taskseries_id, list_id) = getTask(index)

    # find the task
    root = my_rtm.tasks.getList()
    for lists in root.tasks.list:
        if hasattr(lists, "taskseries"):
            if isinstance(lists.taskseries, list):
                for series in lists.taskseries:
                    if series.id == taskseries_id:
                        series_elem = series
                        notes = series_elem.notes
            else:
                series = lists.taskseries
                if series.id == taskseries_id:
                    series_elem = series
                    notes = series_elem.notes


    if notes == []:
        display("This task has no notes")
    else:
        # Display Instructions
        display("Choose the notes for this task to edit:")
        display("")

        # convert notes.note to a list, if there's only a single note
        if isinstance(notes.note, list):
            notes_list = notes.note
        else:
            notes_list = [notes.note]

        # determine which note to edit
        args_list = []
        for note in notes_list:
            title = note.title
            body = getattr(note, "$t")

            display("** " + title + " **")
            display(body)
            display("")
            response = get_input("EDIT THIS NOTE (y/n)? ")
            display("")

            if response in ("y", "Y", "yes", "Yes", "YES"):
                readline.add_history(title)
                new_title = get_input("New title: ")

                display("You will now edit the body of the note in " + CLI_EDITOR + ".")
                display("Make your changes then use the editor to save your changes.")
                get_input("Press enter to continue...")

                temp = tempfile.NamedTemporaryFile(delete=False)
                filename = str(temp.name)
                temp.write(body.encode('utf-8'))
                temp.flush()
                temp.close()

                subprocess.call([CLI_EDITOR, filename])

                if CLI_EDITOR_PAUSE == 1:
                    get_input("Press enter when finished editing...")

                new_body = open(filename, 'r').read()
                os.remove(filename)

                # Make a list of arguments to passed to RTM
                note_args = []
                note_args.append(note.id)
                note_args.append(new_title)
                note_args.append(new_body)

                args_list.append(note_args)

                display("")

        # Save the changes
        display("Saving changes...")

        timeline = getTimeline()

        for i in range(len(args_list)):
            note_args = args_list[i]

            note_id = note_args[0]
            note_title = note_args[1]
            note_body = note_args[2]

            display("saving note #" + str(note_id) + "...")

            # save the note
            rsp = my_rtm.tasksNotes.edit(timeline=timeline, note_id=note_id, note_title=note_title, note_text=note_body)

            # write the transaction ID if it is undoable
            if rsp.transaction.undoable == "1":
                writeTransID(rsp.transaction.id, multi="true")
            else:
                writeTransID("NA", multi="true")


# END editNote()
# ========================================================================================================= #



# ========================================================================================================= #
# getNotes <task index>                                                                                     #
#    This method will display the notes, if any, for the specified task                                     #
# ========================================================================================================= #
def getNotes(index):

    if MODE != "interactive":
        login()

    # get the task properties
    (task_id, taskseries_id, list_id) = getTask(index)

    # find the task
    root = my_rtm.tasks.getList()
    for lists in root.tasks.list:
        if hasattr(lists, "taskseries"):
            if isinstance(lists.taskseries, list):
                for series in lists.taskseries:
                    if series.id == taskseries_id:
                        series_elem = series
                        notes = series_elem.notes
            else:
                series = lists.taskseries
                if series.id == taskseries_id:
                    series_elem = series
                    notes = series_elem.notes


    if notes == []:
        display("This task has no notes")
    else:
        # get the size of the console
        rows, columns = os.popen('stty size', 'r').read().split()


        # convert notes.note to a list, if there's only a single note
        if isinstance(notes.note, list):
            notes_list = notes.note
        else:
            notes_list = [notes.note]


        # DISPLAY THE NOTES
        for note in notes_list:
            title = note.title
            title_length = int(len(title))
            body = getattr(note, "$t")

            # Get the width of the note (either the max length of a line or the width of the console)
            index = 0;
            max_line_length = 0


            done = 0
            while body.find('\n', index) != -1 and done == 0:

                new_index = body.find('\n', index+1)
                length = new_index - index

                if length > max_line_length:
                    max_line_length = length

                if new_index > 0:
                    index = new_index+1
                else:
                    done = 1

            # last segment length or entire string if one line
            new_index = int(len(body))
            length = new_index - index

            if length > max_line_length:
                # print(str(length) + "*")
                max_line_length = length

            # if the max line length is greater than the console, we'll have to wrap it
            max_line_length = max_line_length + 4
            title_length = title_length + 4

            if title_length > max_line_length and title_length < int(columns):
                max_width = title_length
            elif int(max_line_length) > int(columns):
                max_width = int(columns)
            else:
                max_width = max_line_length


            # top line

            if PLAIN == 0:
                display(COLOR_NOTE_BORDER, 0)

            display("|", 0)
            for i in range(max_width-2):
                display("=", 0)
            display("|")

            if PLAIN == 0:
                display(COLOR_RESET, 0)



            # title row
            if len(title) > 0:
                if PLAIN == 0:
                    display(COLOR_NOTE_BORDER, 0)

                display("|", 0)

                if PLAIN == 0:
                    display(COLOR_RESET, 0)

                space_len = int((max_width-int(len(note.title))-2)/2)
                for i in range(space_len):
                    display(" ", 0)

                if PLAIN == 0:
                    display(COLOR_NOTE_TITLE, 0)

                display(title, 0)

                if PLAIN == 0:
                    display(COLOR_RESET, 0)

                title_length = 1+space_len+int(len(note.title))
                space_len = int(max_width-title_length-1)
                for i in range(space_len):
                    display(" ", 0)

                if PLAIN == 0:
                    display(COLOR_NOTE_BORDER, 0)

                display("|")

                if PLAIN == 0:
                    display(COLOR_RESET, 0)



                # title divider
                if PLAIN == 0:
                    display(COLOR_NOTE_BORDER, 0)

                display("|", 0)

                for i in range(max_width-2):
                    display("-", 0)

                display("|")

                if PLAIN == 0:
                    display(COLOR_RESET, 0)



            # body

            # turn the string into a list
            body = " \n ".join(body.split("\n"))
            body = re.split(' ', body)

            if PLAIN == 0:
                display(COLOR_NOTE_BORDER, 0)

            display("| ", 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            # parse each word
            line_length = 0
            for i in range(len(body)):

                # manually handle new lines
                if body[i] == "\n" or (line_length + int(len(body[i])) + 4) > max_width:

                    # pad with spaces
                    space_len = max_width - line_length - 3
                    for j in range(space_len):
                        display(" ", 0)

                    if PLAIN == 0:
                        display(COLOR_NOTE_BORDER, 0)

                    display("|")

                    display("| ", 0)

                    if PLAIN == 0:
                        display(COLOR_RESET, 0)

                    line_length = 0

                # display the word
                else:
                    display(body[i] + " ", 0)
                    line_length = line_length + int(len(body[i]))+1

            # pad with spaces
            space_len = max_width - line_length - 3
            for j in range(space_len):
                display(" ", 0)

            if PLAIN == 0:
                display(COLOR_NOTE_BORDER, 0)

            display("|")


            # Bottom Line
            display("|", 0)

            for i in range(max_width-2):
                display("=", 0)
            display("|")

            if PLAIN == 0:
                display(COLOR_RESET, 0)


            display("")


# END getNotes()
# ========================================================================================================= #



# ========================================================================================================= #
# clear                                                                                                     #
#    This method will delete all completed tasks (optionally from a specified filter)                       #
# ========================================================================================================= #
def clear(filterString=""):

    # login in to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # get all tasks
    getTasks(filterString=filterString)

    # the task stack
    stack=[]

    # check all tasks to see if its been completed
    for i in range(len(tasks)):

        # add completed tasks to the stack
        if tasks[i][7] != "":
            stack.append((tasks[i][1], tasks[i][0], tasks[i][6], tasks[i][2]))

    display("cleaning up RTM tasks...")

    # get a timeline id
    timeline = getTimeline()

    # signal the start of a multi function
    writeTransID("startMulti")

    # now, submit the changes to RTM
    while len(stack) != 0:
        # get the current tasks's saved properties
        props = stack.pop()

        display("deleting task: " + props[3] + "...")

        # set the priority of the task
        del_task = my_rtm.tasks.delete(timeline=timeline, task_id=props[0], taskseries_id=props[1], list_id=props[2])

        # write the transaction ID if it is undoable
        if del_task.transaction.undoable == "1":
            writeTransID(del_task.transaction.id, multi="true")
        else:
            writeTransID("NA")

# END clear()
# ========================================================================================================= #



# ========================================================================================================= #
# undo                                                                                                      #
#    This method will undo the transaction that is specified by the transaction ID saved to disk            #
# ========================================================================================================= #
def undo():

    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    transIDs = []

    # get the timeline and transIDs
    timeline = getTimeline()
    transIDs = getTransID()


    # when there is no transID found
    if transIDs == []:
        display("No action was found to undo...")

    # when the last action is not undoable
    elif transIDs[0] == "NA":
        display("What you just did cannot be undone...")

    # when there is only one action to undo
    elif len(transIDs) == 1:
        display("undoing the last action...")
        my_rtm.transactions.undo(transaction_id=transIDs[0], timeline=timeline)

    # when there are multiple actions to undo
    else:
        display("undoing the last multi-action...")

        for i in range(len(transIDs)):
            my_rtm.transactions.undo(transaction_id=transIDs[i], timeline=timeline)

    # once undone, remove the transID
    writeTransID("NA")

# END undo()
# ========================================================================================================= #



# ========================================================================================================= #
# planner <start>                                                                                           #
#    This method will print a weekly planner of all tasks due on the displayed date.                        #
#    THIS WILL PRINT VERY WIDE - especially if the task names are long                                      #
#    <start>: today, mon, sun --> determines what day to start the week                                     #
#                                                                                                           #
#   THIS REALLY NEEDS TO BE CLEANED UP                                                                      #
# ========================================================================================================= #
def planner(start="mon", filterString=""):
    col_buffer = 8

    # max substring length
    # PLANNER_LENGTH = 20 # old value
    rows, columns = os.popen('stty size', 'r').read().split()
    substring_length = int(((int(columns)-8)/7)-col_buffer)
    substring_remainder = int(int(columns) - (((int(substring_length)+col_buffer)*7)+8))



    # login to RTM and authenticate the user
    if MODE != "interactive":
        login()

    # get the tasks
    getTasks(filterString=filterString)

    # sort tasks by task due date, then completed, priority, and task name
    global tasks
    tasks = sorted(tasks, key=itemgetter(4,7,3,2))


    # SET UP DAYS OF WEEK

    # Get today's date and day of week
    today_obj = date.today()
    weekday_int = date.weekday(today_obj)
    today = weekdays[weekday_int] + " " + str(today_obj)[5:10]

    # Calculate the first day of this week (depending on what start day is specified)
    if start == "mon":
        first_day_obj = today_obj - timedelta(days = weekday_int)
    elif start == "sun":
        first_day_obj = today_obj - timedelta(days = (weekday_int+1))
    elif start == "today":
        first_day_obj = today_obj
    else:
        display("ERROR: start day " + start + " not recognized.")
        sys.exit(2)

    # create a list of date objects for this week
    date_objs=[]
    date_objs.append(first_day_obj)
    for i in range(1,7):
        date_objs.append(first_day_obj + timedelta(days = i))


    # SORT THROUGH AND GATHER TASKS DATA

    # initialize a list for each day of the week
    # a list of overdue tasks
    # a list for anytime tasks
    # a list for all others
    day_0=[]
    day_1=[]
    day_2=[]
    day_3=[]
    day_4=[]
    day_5=[]
    day_6=[]
    overdue=[]
    anytime=[]
    others=[]

    # sort the tasks into their respective lists
    for i in range(len(tasks)):

        # get the due date as a string
        temp_date_obj = str(tasks[i][4])

        # check for tasks with no due date
        if temp_date_obj == "":
            anytime.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))

        # for tasks with due dates
        else:
            # convert the date into a datetime object
            temp_date_obj = datetime.strptime(temp_date_obj, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc).astimezone(Local)

            # check the date against each day of the week
            # if it matches, append the task's pri, list, name, completed date, length of task name
            if temp_date_obj.date() == date_objs[0]:
                day_0.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() == date_objs[1]:
                day_1.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() == date_objs[2]:
                day_2.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() == date_objs[3]:
                day_3.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() == date_objs[4]:
                day_4.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() == date_objs[5]:
                day_5.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() == date_objs[6]:
                day_6.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            elif temp_date_obj.date() < date_objs[0]:
                if tasks[i][7] == "":
                    overdue.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))
            else:
                others.append((tasks[i][3], tasks[i][5], tasks[i][2], tasks[i][7], len(tasks[i][2])))


    # sort each day by list, completed, priority and then name
    day_0 = sorted(day_0, key=itemgetter(1,3,0,2))
    day_1 = sorted(day_1, key=itemgetter(1,3,0,2))
    day_2 = sorted(day_2, key=itemgetter(1,3,0,2))
    day_3 = sorted(day_3, key=itemgetter(1,3,0,2))
    day_4 = sorted(day_4, key=itemgetter(1,3,0,2))
    day_5 = sorted(day_5, key=itemgetter(1,3,0,2))
    day_6 = sorted(day_6, key=itemgetter(1,3,0,2))
    overdue = sorted(overdue, key=itemgetter(1,3,0,2))
    others = sorted(others, key=itemgetter(1,3,0,2))
    anytime = sorted(anytime, key=itemgetter(1,3,0,2))

    # create 3D array of all tasks within the 1 week range --> days[day of week][task][property]
    days = []
    days.append(day_0)
    days.append(day_1)
    days.append(day_2)
    days.append(day_3)
    days.append(day_4)
    days.append(day_5)
    days.append(day_6)


    # CALCULATE PROPERTIES FOR THE DISPLAY

    # find the max number of lists (across all days) from the number of unique list names
    # and the max number of tasks in each list
    # and the names of the lists
    max_lists = 0
    max_in_lists = {}
    list_names = []

    # this is a mess
    # cycle through each day's tasks
    for i in range(7):

        task_count = 1
        temp_list = ""

        # cycle through each task in day i
        for j in range(len(days[i])):
            if days[i][j][1] != temp_list:
                task_count = 1
                temp_list = days[i][j][1]

            else:
                task_count = task_count + 1


            if temp_list in max_in_lists:
                if task_count > max_in_lists[temp_list]:
                    max_in_lists[temp_list] = task_count


            else:
                max_in_lists[temp_list] = 1


    # get the number of lists
    max_lists = len(max_in_lists)

    # get the list names and sort
    list_names = list(max_in_lists.keys())
    list_names.sort()


    # find the max length of a list name (across all days)
    max_list_name = 0
    for i in range(len(list_names)):
        if len(list_names[i]) > max_list_name:
            max_list_name = len(list_names[i])


    # find the max length of the largest task name for each day
    max_length = []
    needs_extra = []
    extra_length = substring_remainder
    for i in range(7):

        # set initial max_length for day i
        temp_max_length = max_list_name

        # test the length of each task in day i against the temp max
        # if it is longer, set it as the new temp max
        for j in range(len(days[i])):
            if len(days[i][j][2]) > temp_max_length:
                temp_max_length = len(days[i][j][2])


        # add unused length to the extra
        if temp_max_length < substring_length:
            extra_length = extra_length + (substring_length - temp_max_length)

        # if the max length is greater than the preset max
        # use the preset instead
        if temp_max_length > substring_length:
            use_extra = temp_max_length - substring_length
            if extra_length < use_extra:
                needs_extra.append(use_extra - extra_length)
                use_extra = extra_length
            else:
                needs_extra.append(0)

            if use_extra > 0:
                temp_max_length = substring_length + use_extra
                extra_length = extra_length - use_extra
            else:
                temp_max_length = substring_length

        else:
            needs_extra.append(0)

        # after all j tasks have been tested,
        # set the temp max as the max for day i
        max_length.append(temp_max_length)

    # Add any remaining length
    if extra_length > 0:
        for i in range(6, 0, -1):
            needs = needs_extra[i]
            if needs > 0:
                if needs > extra_length:
                    add = extra_length
                else:
                    add = extra_length - needs
                max_length[i] = max_length[i] + add
                extra_length = extra_length - add


    # find the max number of tasks (across all days)
    max_tasks = 0
    for i in range(7):
        if len(days[i]) > max_tasks:
            max_tasks = len(days[i])


    # total number of lines = sum of the max number of tasks in each list
    max_lines = 0
    for i in range(len(list_names)):
        name=list_names[i]
        max_lines = max_lines + max_in_lists[name]



    # PRINT DATE HEADER

    # first line
    for i in range(7):
        if PLAIN == 0:
            display(COLOR_PLANNER_BORDER, 0)
        display('+', 0)

        total = max_length[i]+col_buffer

        for j in range(int(total)):
            display('-', 0)

    display("+")

    if PLAIN == 0:
        display(COLOR_RESET, 0)


    # second line
    for i in range(7):
        if PLAIN == 0:
            display(COLOR_PLANNER_BORDER,0)

        display('|', 0)


        current_date = weekdays[date_objs[i].weekday()] + " " + str(date_objs[i])[5:10]

        if current_date == today:
            buffer = (max_length[i]-1)/2

            for j in range(int(buffer)):
                display(' ', 0)

            if PLAIN == 0:
                display(COLOR_PLANNER_TODAY, 0)

            display('**TODAY**', 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            if ((max_length[i]-1)%2) != 0:
                buffer = buffer+1
            for j in range(int(buffer)):
                display(' ', 0)

        else:
            buffer = (max_length[i]-1)/2

            for j in range(int(buffer)):
                display(' ', 0)

            if PLAIN == 0:
                display(COLOR_PLANNER_DATE, 0)

            display(current_date, 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            if ((max_length[i]-1)%2) != 0:
                buffer = buffer+1
            for j in range(int(buffer)):
                display(' ', 0)

    if PLAIN == 0:
        display(COLOR_PLANNER_BORDER, 0)

    display("|")


    # third line
    for i in range(7):
        display('+', 0)

        total = max_length[i]+col_buffer

        for j in range(int(total)):
            display('-', 0)

    display("+")

    if PLAIN == 0:
        display(COLOR_RESET, 0)


    # PRINT TASK LISTS
    list_count = 0
    task_count = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

    # get row numbers for new lists
    row_nums={}
    for j in range(len(list_names)):

        name = list_names[j]

        if j == 0:
            row_nums[name] = 0
        else:
            prev_name = list_names[j-1]
            row_nums[name] = row_nums[prev_name] + max_in_lists[prev_name]


    # next_row: value of h to print the next list heading
    next_row = 0

    # h = row number
    for h in range(max_lines):

        # print a list heading, if needed
        if (h == next_row):
            for i in range(7):
                if PLAIN == 0:
                    display(COLOR_PLANNER_BORDER, 0)
                display('| ', 0)

                if PLAIN == 0:
                    display(COLOR_LIST, 0)
                display(list_names[list_count] + ':', 0)

                if PLAIN == 0:
                    display(COLOR_RESET, 0)

                buffer = max_length[i]-len(list_names[list_count])+6
                for j in range(int(buffer)):
                    display(' ', 0)

            if PLAIN == 0:
                display(COLOR_PLANNER_BORDER, 0)

            display("|")

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            list_count = list_count + 1

            if list_count < len(list_names):
                next_list = list_names[list_count]
                next_row = row_nums[next_list]

        # print the actual tasks
        for i in range(7):

            # the max length of the task string
            task_max_length = max_length[i]

            if PLAIN == 0:
                display(COLOR_PLANNER_BORDER, 0)

            display('|', 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            # number of tasks for day i
            days_task_count = task_count[i]

            # if there are tasks left...
            if days_task_count < len(days[i]):

                # list name for the current task
                temp_list_name = days[i][days_task_count][1]

                # Print the task, if it belongs in the current list
                if temp_list_name == list_names[list_count-1]:

                    # increase the task count for the current day
                    task_count[i] = task_count[i] + 1


                    # Parse pri of incomplete tasks, if displaying in color
                    if PLAIN == 0 and days[i][days_task_count][3] == "":
                        pri = days[i][days_task_count][0]
                        if pri == "1":
                            display(COLOR_PRI1, 0)
                        elif pri == "2":
                            display(COLOR_PRI2, 0)
                        elif pri == "3":
                            display(COLOR_PRI3, 0)


                    # for completed tasks
                    if days[i][days_task_count][3] != "":
                        display('    x  ', 0)

                    # for unprioritized tasks
                    elif days[i][days_task_count][0] == "N":
                        display('       ', 0)

                    # for incomplete tasks, print the priority
                    else:
                        display('   (' + days[i][days_task_count][0] + ') ', 0)

                    # print the task itself
                    display(days[i][days_task_count][2][:int(task_max_length)] + ' ', 0)

                    if PLAIN == 0:
                        display(COLOR_RESET, 0)

                    # print buffer space
                    buffer = max_length[i]-days[i][days_task_count][4]
                    for j in range(int(buffer)):
                        display(' ', 0)


                # Print a spacer when the task doens't match the list
                else:
                    buffer = max_length[i]+col_buffer
                    for j in range(int(buffer)):
                        display(' ', 0)


            # print a spacer when there is no task
            else:
                buffer = max_length[i]+col_buffer
                for j in range(int(buffer)):
                    display(' ', 0)

        if PLAIN == 0:
            display(COLOR_PLANNER_BORDER, 0)

        display("|")

    # bottom line
    for i in range(7):
        display('+', 0)

        total = max_length[i]+col_buffer


        for j in range(int(total)):
            display('-', 0)

    display("+")

    if PLAIN == 0:
        display(COLOR_RESET, 0)


    # Get the number of columns in console
    rows, columns = os.popen('stty size', 'r').read().split()
    line_length = 0;


    # get the max length of the anytime and overdue tasks
    max_task_length_o=0
    max_list_name_o=0
    for j in range(len(overdue)):
        if len(overdue[j][2]) > max_task_length_o:
            max_task_length_o = len(overdue[j][2])
        if len(overdue[j][1]) > max_list_name_o:
            max_list_name_o = len(overdue[j][1])

    max_task_length_a=0
    max_list_name_a=0
    for j in range(len(anytime)):
        if len(anytime[j][2]) > max_task_length_a:
            max_task_length_a = len(anytime[j][2])
        if len(anytime[j][1]) > max_list_name_a:
            max_list_name_a = len(anytime[j][1])

    if max_task_length_o > max_task_length_a:
        max_task_length = max_task_length_o
    else:
        max_task_length = max_task_length_a

    if max_list_name_o > max_list_name_a:
        max_list_name = max_list_name_o
    else:
        max_list_name = max_list_name_a



    # PRINT OVERDUE TASKS
    if len(overdue) > 0:
        display("")

        if PLAIN == 0:
            display(COLOR_PLANNER_OA_HEADER, 0)

        display("OVERDUE TASKS:", 0)

        if PLAIN == 0:
            display(COLOR_RESET, 0)

        # initial list heading
        current_list_name = ""

        # cycle through each task item
        for i in range(len(overdue)):

            # if the task item is in a new list...print the new list name
            if overdue[i][1] != current_list_name:
                current_list_name = overdue[i][1]

                display("")
                display('  ', 0)

                if PLAIN == 0:
                    display(COLOR_LIST, 0)

                display(current_list_name + ':', 0)

                if PLAIN == 0:
                    display(COLOR_RESET, 0)

                buffer = max_list_name - len(current_list_name)
                for k in range(int(buffer)):
                    display(' ', 0)

                line_length = max_list_name + 3

            # check to see if the task will wrap line
            if int(line_length + max_task_length + 6) > int(columns):
                display("")
                buffer = max_list_name + 3
                for k in range(int(buffer)):
                    display(' ', 0)
                line_length = max_list_name + max_task_length + 3
            else:
                line_length = line_length + max_task_length + 6


            # if task is completed...
            if overdue[i][3] != "":

                # print an 'x' instead of priority
                display('   x  ', 0)

            # for uncompleted tasks...
            else:

                # Parse the pri, if displaying color
                if PLAIN == 0:
                    pri = overdue[i][0]
                    if pri == "1":
                        display(COLOR_PRI1, 0)
                    elif pri == "2":
                        display(COLOR_PRI2, 0)
                    elif pri == "3":
                        display(COLOR_PRI3, 0)

                # print the priority, if present, and the task in color, if desired
                if overdue[i][0] != "N":
                    display('  (' + overdue[i][0] + ') ', 0)

                # indent non-prioritized tasks further
                else:
                    display('      ', 0)

            # print the actual task
            display(overdue[i][2], 0)
            buffer = max_task_length - len(overdue[i][2])
            for k in range(int(buffer)):
                display(' ', 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

        display("")


    # PRINT THE ANYTIME TASKS
    display("")
    if PLAIN == 0:
        display(COLOR_PLANNER_OA_HEADER, 0)

    display("Due Anytime:", 0)

    if PLAIN == 0:
        display(COLOR_RESET, 0)


    # initial list heading
    current_list_name = ""

    # cycle through each task item
    for i in range(len(anytime)):

        # if the task item is in a new list...print the new list name
        if anytime[i][1] != current_list_name:
            current_list_name = anytime[i][1]

            display("")
            display("  ", 0)

            if PLAIN == 0:
                display(COLOR_LIST, 0)

            display(current_list_name + ':', 0)

            if PLAIN == 0:
                display(COLOR_RESET, 0)

            buffer = max_list_name - len(current_list_name)
            for k in range(int(buffer)):
                display(' ', 0)

            line_length = max_list_name + 3

        # check to see if the task will wrap line
        if int(line_length + max_task_length + 6) > int(columns):
            display("")
            buffer = max_list_name + 3
            for k in range(int(buffer)):
                display(' ', 0)
            line_length = max_list_name + max_task_length + 3
        else:
            line_length = line_length + max_task_length + 6

        # if task is completed...
        if anytime[i][3] != "":

            # print an 'x' instead of priority
            display('   x  ', 0)

        # for uncompleted tasks...
        else:
            # Parse the pri, if displaying color
            if PLAIN == 0:
                pri = anytime[i][0]
                if pri == "1":
                    display(COLOR_PRI1, 0)
                elif pri == "2":
                    display(COLOR_PRI2, 0)
                elif pri == "3":
                    display(COLOR_PRI3, 0)

            # print the priority, if present, and the task in color, if desired
            if anytime[i][0] != "N":

                display('  (' + anytime[i][0] + ') ', 0)

            # indent non-prioritized tasks further
            else:
                display('      ', 0)

        # print the actual task
        display(anytime[i][2], 0)
        buffer = max_task_length - len(anytime[i][2])
        for k in range(int(buffer)):
            display(' ', 0)

        if PLAIN == 0:
            display(COLOR_RESET, 0)

    display("")

# END planner()
# ========================================================================================================= #



# ========================================================================================================= #
# status( msg )                                                                                             #
#     authentication progress bar                                                                           #
# ========================================================================================================= #
def status(msg):

    if DISP_STATUS == 1:

        if msg == None:
            sys.stdout.write("                                                            \r")
            sys.stdout.flush()
        else:
            sys.stdout.write(msg+"\r")
            sys.stdout.flush()

# END status()
# ========================================================================================================= #



# ========================================================================================================= #
# interactive()                                                                                             #
#     let the user enter commands in an interactive mode                                                    #
# ========================================================================================================= #
def interactive():
    global MODE
    MODE = "interactive"
    cmd = ""
    while (cmd != "exit"):
        cmd = get_input('>> ')
        cmd = cmd.split(' ')
        main(cmd, mode="interactive")
        genLookupTable()
# END give_input()
# ========================================================================================================= #



# ========================================================================================================= #
# help                                                                                                      #
#     print basic description of the program                                                                #
# ========================================================================================================= #
def help():

    # Get user credentials
    username = login()

    display("NAME")
    display("  rtm -- a command line interface for the Remember the Milk task manager")
    display("         see http://www.rememberthemilk.com/ for more information.")
    display("")
    display("DESCRIPTION")
    display("  This program gives full command line access to a user's rtm tasks and ")
    display("  can view, add and modify tasks.  The program utilizes the pyrtm Remember")
    display("  The Milk API interface for python.  Visit <https://bitbucket.org/srid/pyrtm/>")
    display("  for more information about the API interface.")
    display("")
    version()
    display("")
    display("RTM USER INFORMATION")
    display("  Username: " + username)
    display("")
    usage()

# END help()
# ========================================================================================================= #



# ========================================================================================================= #
# version                                                                                                   #
#     print author and version                                                                              #
# ========================================================================================================= #
def version():
    try:
        paths = rtm.__file__.split(os.sep)
        pyrtm = paths[-3]
    except:
        pyrtm = "Unknown"

    display("AUTHOR")
    display("  David Waring -- dave@davidwaring.net")
    display("  http://www.davidwaring.net/projects/rtm.html")
    display("")
    display("VERSION")
    display("  SCRIPT: " + VERSION)
    display("  PYRTM: " + pyrtm)
    display("  PYTHON: " + sys.version.split(' ')[0])

# END version()
# ========================================================================================================= #



# ========================================================================================================= #
# usage                                                                                                     #
#     print the usage and define the options and commands                                                   #
# ========================================================================================================= #
def usage():

    display("USAGE")
    display("  rtm [options] ... [command] [command arguments]")
    display("")
    display("  Options:")
    display("    Note: To change the default display variables, edit the values in the beginning of this script")
    display("")
    display("    --comp, -c          : toggle the display of completed tasks - default " + str(DISP_COMP))
    display("    --help, -h          : display the help and usage")
    display("    --notes, -n         : toggle the display of notes indicators - default " + str(DISP_NOTES))
    display("    --plain, -p         : set output to plain (no color) - default " + str(PLAIN))
    display("    --readline, -r      : toggle readline support (disable to improve unicode support in interative mode) - default " + str(ENABLE_READLINE))
    display("    --status, -s        : toggle the display of status messages - default " + str(DISP_STATUS))
    display("    --tags, -t          : toggle the display of tags - default " + str(DISP_TAGS))
    display("    --usage, -u         : display the usage")
    display("    --version, -v       : display the author and version")
    display("")
    display("  Commands [arguments]:")
    display("    - Only 1 command can be used at a time")
    display("    - Leaving the command blank will start the interactive mode")
    display("    - Generally, leaving the arguments blank will allow the user to enter")
    display("      multiple arguments at a prompt (ie marking multiple tasks complete).")
    display("")
    display("    add [task]          : add a task using the following format::")
    display("      a [task]              task name due date p:priority l:list name t:tag")
    display("    addList [name]      : add a new list to RTM using the specified name")
    display("      al [name]")
    display("    addNote [index] [title] [body] : add a note to the specified task")
    display("      an [index] [title] [body]")
    display("    addTags [index] [tags] : add the given tags to the specified task")
    display("      at [index] [tags]")
    display("    comp [index]        : mark the task specified by its index number as complete")
    display("      c [index]")
    display("    delete [index]      : delete the task specified by its index number")
    display("      del [index]")
    display("      rm [index]")
    display("    delList [name]      : delete the list specified by its name")
    display("      dl [name]             (moves remaining tasks to the Inbox)")
    display("    delNote [index]     : delete a note from the specified task")
    display("      dn [index]")
    display("    delTags [index] [tags] : delete the given tags from the specified task")
    display("      dt [index] [tags]")
    display("    due [index] [date]  : set the due date of the task specified by its index number")
    display("    edit [index] [name] : edit the name of the task specified by its index number")
    display("      e [index] [name]")
    display("    editNote [index]    : edit one of the notes for the specified task")
    display("      en [index]")
    display("    exit                : exit interactive mode")
    display("    help                : display this help information")
    display("    logout              : remove login credentials used by RTM-CLI")
    display("    ls [filter]         : list all tasks sorted first by list then priority")
    display("    lsd [filter]        : list all tasks sorted first by due date then priority")
    display("    lsp [filter]        : list all tasks sorted first by priority then list")
    display("        [filter]        : filter options based on RTM's advanced search filters, ie::")
    display("                            list:<task list>")
    display("                            priority:<priority>")
    display("                            tag:<tag>")
    display("                            status:<completed | incomplete>")
    display("                            due:<due date>")
    display("    move [index] [list] : move the task specified by its index number to the specified list")
    display("      mv [index] [list]")
    display("      m [index] [list]")
    display("    notes [index]       : display the notes for the task specified by its index number")
    display("    open [page]         : open RTM <page> (home by default) in a web browser")
    display("      o [page]              <page> = filters, help, home, planner, tasks, search, settings")
    display("    postpone [index]    : postpone the due date of the specified task by 1 day")
    display("      pp [index]")
    display("    pri [index] [pri]   : set the priority of task specified by its index number to <pri>,")
    display("      p [index] [pri]       where <pri> can be priorities 1,2,3 or 0 to remove priority")
    display("    renameList [old name] [new name] : change the name of a list from <old name> to <new name>")
    display("      mvList [old name] [new name]")
    display("    uncomp [index]      : uncomplete the task specified by its index number")
    display("      unc [index]           set the status of a previously completed task to incomplete")
    display("      inc [index]")
    display("    undo                : undo the last function")
    display("")
    display("  Meta-Commands:")
    display("    clear [filter]      : delete all completed tasks (that match the optional filter)")
    display("    planner [start] [filter] : print a weekly planner for tasks with due dates for this week")
    display("      week [start] [filter]      <start> = mon (default), sun or today")
    display("                               NOTE: this will print a very wide display and task names will")
    display("                                  be cut at 20 characters.")
    display("    today               : display prioritized tasks and tasks completed today")
    display("    overdue             : display all tasks that are overdue")

# END usage()
# ========================================================================================================= #



# ========================================================================================================= #
# get_input( prompt )                                                                                       #
#     get user input and return the result                                                                  #
# ========================================================================================================= #
def get_input(prompt=">> "):
    try:
        res = raw_input(prompt)
    except NameError:
        res = input(prompt)

    return res
# END get_input()
# ========================================================================================================= #



# ========================================================================================================= #
# get_multi_input( prompt )                                                                                 #
#     get multi-line user input, send EOF to end                                                            #
# ========================================================================================================= #
def get_multi_input():
    result = sys.stdin.readlines()
    result_str = ""
    for i in range(len(result)):
        result_str = result_str + str(result[i])
    return result_str
# END get_input()
# ========================================================================================================= #



# ========================================================================================================= #
# display( text, newline )                                                                                  #
#     get user input and return the result                                                                  #
#     newline=1: adds newline at end of text                                                                #
#     newline=0: does not add newline at end of text                                                        #
# ========================================================================================================= #
def display(text, newline=1):
    # Python 2
    if sys.version_info < (3, 0):
        if type(text) == unicode:
            text = text.encode('utf-8')

        if (newline == 1):
            sys.stdout.write(text)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(text)

    # Python 3
    else:
        if (newline == 1):
            sys.stdout.write(text)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(text)
# END display()
# ========================================================================================================= #



# ========================================================================================================= #
# main( argv )                                                                                              #
#     login in to RTM and process the command line arguments                                                #
# ========================================================================================================= #
def main(argv, mode=""):

    # PROCESS COMMAND LINE ARGUMENTS

    # define command line options
    try:
        opts, args = getopt.getopt(argv, "chnprstuv", ["comp", "help", "notes", "plain", "readline", "status", "tags", "usage", "version"])
    except getopt.GetoptError as err:
        display("ERROR: " + str(err))
        display("")
        usage()
        sys.exit(2)


    # Process options
    for opt, arg in opts:
        if opt in ("--comp", "-c"):
           global DISP_COMP
           DISP_COMP = abs(DISP_COMP-1)
        elif opt in ("--help", "-h"):
            help()
            sys.exit(0)
        elif opt in ("--notes", "-n"):
           global DISP_NOTES
           DISP_NOTES = abs(DISP_NOTES-1)
        elif opt in ("--plain", "-p"):
            global PLAIN
            PLAIN=1
        elif opt in ("--readline", "-r"):
            global ENABLE_READLINE
            ENABLE_READLINE = abs(ENABLE_READLINE-1)
        elif opt in ("--status", "-s"):
            global DISP_STATUS
            DISP_STATUS = abs(DISP_STATUS-1)
        elif opt in ("--tags", "-t"):
            global DISP_TAGS
            DISP_TAGS = abs(DISP_TAGS-1)
        elif opt in ("--usage", "-u"):
            usage()
            sys.exit(0)
        elif opt in ("--version", "-v"):
            version()
            sys.exit(0)


    # conditional import statements
    if ENABLE_READLINE == 1:
        import readline


    # parse command from the command line arguments
    if len(args) == 0:
        login()
        interactive()

    command = args[0]

    # Process commands (only one can be given at a time)
    if command == "ls":
        filename = str(args[1:][0]) + ".txt"
        if os.path.exists(filename):
            prevread = open(filename, "r").read()

        try:
            sys.stdout = Logger(filename)
            ls(filterString=" ".join(args[1:]))
        except:
            sys.stdout.write("<tr><td>file</td><td></td></tr>")
            sys.stdout.write(prevread)

    elif command == "lsp":
        lsp(filterString=" ".join(args[1:]))

    elif command == "lsd":
        lsd(filterString=" ".join(args[1:]))

    elif command in ("add", "a"):
        if len(args) == 1:
            madd()
        else:
            add(" ".join(args[1:]))

    elif command in ("addList", "addlist", "al", "aL"):
        if len(args) == 1:
            maddList()
        else:
            addList(" ".join(args[1:]))

    elif command in ("addTags", "addtags", "at", "aT"):
        if len(args) < 3:
            maddTags()
        else:
            addTags(args[1], ",".join(args[2:]))

    elif command in ("addNote", "addnote", "an", "aN"):
        if len(args) < 4:
            maddNote()
        else:
            addNote(args[1], args[2], " ".join(args[3:]))

    elif command in ("complete", "comp", "com", "c", "fin", "f"):
        if len(args) == 2:
            complete(args[1])
        else:
            mcomplete()

    elif command in ("delete", "dele", "del", "rm"):
        if len(args) == 2:
            delete(args[1])
        else:
            mdelete()

    elif command in ("delList", "dellist", "dl", "dL", "deleteList", "deletelist"):
        if len(args) == 1:
            mdelList()
        else:
            delList(" ".join(args[1:]))

    elif command in ("delTags", "deltags", "dt", "dT", "deletetags", "deleteTags"):
        if len(args) < 3:
            mdelTags()
        else:
            delTags(args[1], ",".join(args[2:]))

    elif command in ("delNote", "delnote", "dn", "dN", "deletenote", "deleteNote"):
        if len(args) == 1:
            delNote()
        elif len(args) == 2:
            delNote(args[1])
        else:
            delNote()

    elif command in ("edit", "rename", "e", "rn"):
        if len(args) < 3:
            medit()
        elif len(args) == 3:
            edit(args[1], args[2])
        else:
            edit(args[1], args[2:])

    elif command in ("editNote", "editnote", "editNotes", "editnotes", "en", "eN"):
        if len(args) == 1:
            editNote()
        elif len(args) == 2:
            editNote(args[1])
        else:
            editNote()

    elif command in ("exit"):
        sys.exit(0)

    elif command in ("renameList", "renamelist", "rl", "rL", "mvList", "mvlist"):
        if len(args) == 3:
            renameList(args[1], args[2])
        else:
            mrenameList()

    elif command in ("priority", "pri", "p"):
        if len(args) == 3:
            setPriority(args[1], pri=args[2])
        else:
            msetPriority()

    elif command in ("move", "mv", "m"):
        if len(args) == 3:
            move(args[1], args[2])
        else:
            mmove()

    elif command in ("notes"):
        if len(args) == 2:
            getNotes(args[1])
        else:
            display("You must supply a task index number.")

    elif command in ("due"):
        if len(args) == 3:
            setDueDate(args[1], due_date=args[2])
        else:
            msetDueDate()

    elif command in ("uncomplete", "uncomp", "unc", "uc", "incomplete", "incomp", "inc"):
        if len(args) == 2:
            uncomplete(args[1])
        else:
            muncomplete()

    elif command in ("postpone", "post", "pp"):
        if len(args) == 2:
            postpone(args[1])
        else:
            mpostpone()

    elif command == "undo":
        undo()

    elif command == "logout":
        logout()

    elif command in ("planner", "week"):
        if len(args) == 1:
            planner()
        elif len(args) == 2:
            planner(start=args[1])
        else:
            planner(start=args[1], filterString=" ".join(args[2:]))

    elif command in ("open", "o"):
        username = login()
        if len(args) == 2:
            if args[1] == "planner":
                display("opening the RTM planner...")
                webbrowser.open("http://www.rememberthemilk.com/printplanner/"+username, True, True)
            elif args[1] == "tasks":
                display("opening the RTM tasks page...")
                webbrowser.open("http://www.rememberthemilk.com/home/"+username+"/#section.tasks", True, True)
            elif args[1] == "settings":
                display("opening the RTM settings page...")
                webbrowser.open("http://www.rememberthemilk.com/home/"+username+"/#section.settings", True, True)
            elif args[1] == "help":
                display("opening the RTM help page...")
                webbrowser.open("http://www.rememberthemilk.com/help/", True, True)
            elif args[1] == "search":
                display("opening RTM advanced serach filters...")
                webbrowser.open("http://www.rememberthemilk.com/help/answers/search/advanced.rtm", True, True)
            elif args[1] == "filters":
                display("opening RTM advanced serach filters...")
                webbrowser.open("http://www.rememberthemilk.com/help/answers/search/advanced.rtm", True, True)
            else:
                display("opening RTM...")
                webbrowser.open("http://www.rememberthemilk.com/home/"+username, True, True)
        else:
            display("opening RTM...")
            webbrowser.open("http://www.rememberthemilk.com/home/"+username, True, True)

    elif command in ("clean", "clear"):
        clear(filterString=" ".join(args[1:]))

    elif command == "today":
        lsp(filterString="(not priority:none and status:incomplete) or completed:today or (due:today and status:incomplete)")

    elif command == "overdue":
        lsp(filterString="(dueBefore:now and status:incomplete)")

    elif command == "":
        usage()
        if MODE != "interactive":
            sys.exit(2)

    elif command == "help":
        help()

    elif command == "rtm":
        main(args[1:])

    else:
        display("ERROR: command " + command + " not recognized")
        usage()
        if MODE != "interactive":
            sys.exit(2)


class Logger(object):
    def __init__(self, file):
        self.terminal = sys.stdout
        self.log = open(file, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass

# Call main with all args (excluding the command name)
if __name__ == "__main__":
    main(sys.argv[1:])

# END main()
# ========================================================================================================= #
