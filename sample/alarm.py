# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.
#
# Author:  Gregory J. Sharp
# Version: $Id: Alarm.py,v 1.2 2008/03/17 17:16:49 greenc Exp $
#
# This program accepts alarms about error conditions. If the error has
# occured too frequently in the recent past, it will send a warning email
# to the list of administrators provided for that alarm condition.
# TODO: revise the code

import sys
import time
import os
import socket
import smtplib


class Alarm:
    """
    This class tracks a single alarm condition's status, sending messages
    to the administrator list when alarm events occur more frequently than
    the specified threshold. The code that uses this should call event()
    each time an alarm event occurs. It should call reset() if the alarm
    condition goes away.
    """

    # Alarm Constructor
    #
    # @param smtpServer is the name of the SMTP server host via which emails
    #        are sent. 'localhost' is frequently adequate.
    # @param fromAddress is the email address that will appear in the From:
    #        line of the email messages.
    # @param toAddressList is a list of email addresses to which an email
    #        will be sent if a warning is triggered.
    # @param subject is the subject line of the email message that will be
    #        sent if a warning is triggered.
    # @param messageText is the message that will be sent to the email list
    #        if the alarm event occurs too frequently.
    # @param threshold is the number of times the alarm can be reported,
    #        without an intervening reset, before a warning email should be
    #        sent. If set to zero, it will send an email for each event, except
    #        that it won't send emails for events that occur within the
    #        repeatTimeLimit.
    # @param repeatTimeLimit is the time in seconds within which a second
    #        email warning will not be sent. I.e., if an alarm event occurs that
    #        triggers an email, then no new email will be sent if the alarm
    #        event recurs during the next repeatTimeLimit seconds. If sset to
    #        zero, it will send an email every time the threshold is exceeded.
    # @param resetAfterWarning is a boolean value. If true, then the event
    #        count will be set back to zero after a warning is issued. 

    def __init__( self,
                  smtpServer,
                  fromAddress,
                  toAddressList,
                  subject,
                  messageText,
                  threshold,
                  repeatTimeLimit,
                  resetAfterWarning = True ):
        # Save the parameters for later.
        self._repeatTimeLimit = repeatTimeLimit
        self._threshold = threshold
        self._resetAfterWarning = resetAfterWarning
        self._smtpServer = smtpServer
        self._fromAddress = fromAddress
        self._emailList = toAddressList
        # We take the subject and message text and embed them into an email
        # message # suitable for passing to the python smtplib interface.
        self._message = "From: " + fromAddress + \
                        "\r\nTo: " + ", ".join( toAddressList ) + \
                        "\r\nSubject: " + subject + \
                        "\r\n\r\nThis message was generated from host " + \
                        socket.gethostname() + \
                        "\r\n\r\n" + messageText

        # The count is the number of times this alarm has been reported
        # since the last reset of the alarm.
        self._count = 0
        # The timeOfLastEmail is the timestamp of when event() last sent
        # and email to the email list. Initially it is 0 (the epoch), since
        # event() has not been called.
        self._timeOfLastEmail = 0;


    # This is a hopefully generic way of sending an email message.
    def sendEmail( self ):
        if self._emailList[0] != '':
            server = smtplib.SMTP( self._smtpServer )
            server.sendmail( self._fromAddress, self._emailList, self._message )
            server.quit()
        else:
            # There is no email list, so we write it to stdout and hope
            # somebody remembers to look in the stdout log.
            print self._message


    def reset( self ):
        self._count = 0
        # Note that we don't reset the timeOfLastEmail. We don't want to
        # mail-bomb the list because an alarm is continually resetting.


    def event( self ):
        # Increment the event count. If it exceeds the threshold and we
        # have not warned in the last _repeatTimeLimit seconds, then send
        # an email warning about the alarm condition.
        self._count = self._count + 1
        now = time.time()
        diff = now - self._timeOfLastEmail
        if ( self._count >= self._threshold and diff > self._repeatTimeLimit ):
            self.sendEmail()
            self._timeOfLastEmail = now
            if self._resetAfterWarning:
                self._count = 0

# end class Alarm

