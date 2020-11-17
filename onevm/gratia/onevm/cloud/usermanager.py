#!/usr/bin/python

import os
import sys
import time
import socket

from gratia.onevm.process_utils import isList

class UserNotFound(Exception): pass

class UserManager:

    def __init__(self, hostname=socket.gethostname()):
        self.hostname = hostname
        self.users = {}
        self.getAllUsers()


    def getAllUsers(self):
        """
        Query to get map of Ids to user jobs
        """

        raise NotImplementedError


    def getUsername(self, id):
        """
        Given the user id return the username
        """

        if id in self.users:
            return self.users[id]

        raise UserNotFound('User with id % not found' % id)


    def getUserId(self, username):
        """
        Given the username return the user id
        """

        if user in self.users.values():
            for id in self.users.keys():
                if self.users[id] == username:
                    return id

        raise UserNotFound('User with username % not found' % username)
