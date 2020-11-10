
import sys
import time
import signal
import socket
try:
    import urllib
    import httplib
except ImportError:
    import urllib.parse as urllib
    import http.client as httplib

from gratia.common.config import ConfigProxy
from gratia.common.debug import DebugPrint, DebugPrintTraceback

# Hopefully these import lines go away when we can do relative imports
import gratia.common.ProxyUtil as ProxyUtil
import gratia.common.sandbox_mgmt as sandbox_mgmt
import gratia.common.response as response
import gratia.common.utils as utils
import gratia.common.global_state as global_state

Config = ConfigProxy()

# Instantiate a global connection object so it can be reused for
# the lifetime of the server Instantiate a 'connected' flag as
# well, because at times we cannot interrogate a connection
# object to see if it has been connected yet or not

connection = None
connected = False
connectionError = False
connectionRetries = 0
certificateRejected = False
certrequestRejected = False
__maxConnectionRetries__ = 2
__last_retry_time = None
__maximumDelay = 900
__initialDelay = 30
__retryDelay = __initialDelay
__backoff_factor = 2
__resending = 0
timeout = 3600

# NOTE:
# I doubt this timeout mechanism works.
# signal.alarm is HIGHLY unreliable in the face of blocking C functions.
# Probably only works in a very limited number of cases. 
# -BB
class GratiaTimeout(Exception):
    """
    Exception class to mark a connection timeout caught via the signal.alarm.
    """

    __message = None

    def __init__(self, message = None):
        Exception.__init__()
        self.__message = message


def __handle_timeout__(signum, _):
    """
    Insure that we properly shutdown the connection in case of timeout
    """
    DebugPrint(3, 'Signal handler "handle_timeout" called with signal', signum)
    raise GratiaTimeout("Connection to Collector lasted more than: "+str(timeout)+" second")

def connect():
##
## __connect
##
## Author - Tim Byrne
##
## Connect to the web service on the given server, sets the module-level object __connection__
##  equal to the new connection.  Will not reconnect if __connection__ is already connected.
##
    global connection
    global connected
    global connectionError
    global connectionRetries
    global __retryDelay
    global __last_retry_time

    # __connectionError__ = True
    # return connected

    if connectionError:
        disconnect()
        connectionError = False
        if connectionRetries > __maxConnectionRetries__:
            current_time = time.time()
            if not __last_retry_time:  # Set time but do not reset failures
                __last_retry_time = current_time
                return connected
            if current_time - __last_retry_time > __retryDelay:
                __last_retry_time = current_time
                DebugPrint(1, 'Retry connection after ', __retryDelay, 's')
                __retryDelay = __retryDelay * __backoff_factor
                if __retryDelay > __maximumDelay:
                    __retryDelay = __maximumDelay
                connectionRetries = 0
        connectionRetries += 1

    if not connected and connectionRetries <= __maxConnectionRetries__:
        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            DebugPrint(0, 'Error: SOAP connection is no longer supported.')
            __connectionError__ = True
            return connected
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:

            try:
                if ProxyUtil.findHTTPProxy():
                    DebugPrint(0, 'WARNING: http_proxy is set but not supported')

                # __connection__ = ProxyUtil.HTTPConnection(Config.get_SOAPHost(),
                #                                        http_proxy = ProxyUtil.findHTTPProxy())

                connection = httplib.HTTPConnection(Config.get_SOAPHost())
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                DebugPrint(0, 'ERROR: could not initialize HTTP connection')
                DebugPrintTraceback()
                connectionError = True
                return connected
            try:
                prev_handler = signal.signal(signal.SIGALRM, __handle_timeout__)
                signal.alarm(timeout)
                DebugPrint(4, 'DEBUG: Connect')
                connection.connect()
                DebugPrint(4, 'DEBUG: Connect: OK')
                signal.alarm(0)
                signal.signal(signal.SIGALRM, prev_handler)
            except socket.error as ex:
                DebugPrint(3, 'Socket connection error: '+str(ex))
                connectionError = True
                raise
            except GratiaTimeout:
                DebugPrint(3, 'Connection timeout (GratiaTimeout exception).')
                connectionError = True
                raise                
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                connectionError = True
                DebugPrint(4, 'DEBUG: Connect: FAILED')
                DebugPrint(0, 'Error: While trying to connect to HTTP, caught exception ' + str(ex))
                DebugPrintTraceback()
                return connected
            DebugPrint(1, 'Connection via HTTP to: ' + Config.get_SOAPHost())
        else:

            # print "Using POST protocol"
            # assert(Config.get_UseSSL() == 1)

            if Config.get_UseGratiaCertificates() == 0:
                pr_cert_file = Config.get_CertificateFile()
                pr_key_file = Config.get_KeyFile()
            else:
                pr_cert_file = Config.get_GratiaCertificateFile()
                pr_key_file = Config.get_GratiaKeyFile()

            if pr_cert_file == None:
                DebugPrint(0, 'Error: While trying to connect to HTTPS, no valid local certificate.')
                connectionError = True
                return connected

            DebugPrint(4, 'DEBUG: Attempting to connect to HTTPS')
            try:
                if ProxyUtil.findHTTPSProxy():
                    DebugPrint(0, 'WARNING: http_proxy is set but not supported')

                # __connection__ = ProxyUtil.HTTPSConnection(Config.get_SSLHost(),
                #                                        cert_file = pr_cert_file,
                #                                        key_file = pr_key_file,
                #                                        http_proxy = ProxyUtil.findHTTPSProxy())

                connection = httplib.HTTPSConnection(Config.get_SSLHost(), cert_file=pr_cert_file,
                                                       key_file=pr_key_file)
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                DebugPrint(0, 'ERROR: could not initialize HTTPS connection')
                DebugPrintTraceback()
                connectionError = True
                return connected
            try:
                prev_handler = signal.signal(signal.SIGALRM, __handle_timeout__)
                signal.alarm(timeout)
                DebugPrint(4, 'DEBUG: Connect')
                connection.connect()
                DebugPrint(4, 'DEBUG: Connect: OK')
                signal.alarm(0)
                signal.signal(signal.SIGALRM, prev_handler)
            except socket.error as ex:
                connectionError = True
                raise
            except GratiaTimeout:
                DebugPrint(3, 'Connection (GratiaTimeout exception).')
                connectionError = True
                raise                
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                DebugPrint(4, 'DEBUG: Connect: FAILED')
                DebugPrint(0, 'Error: While trying to connect to HTTPS, caught exception ' + str(ex))
                DebugPrintTraceback()
                connectionError = True
                return connected
            DebugPrint(1, 'Connected via HTTPS to: ' + Config.get_SSLHost())

            # print "Using SSL protocol"
        # Successful

        DebugPrint(4, 'DEBUG: Connection SUCCESS')
        connected = True

        # Reset connection retry count to 0 and the retry delay to its initial value

        connectionRetries = 0
        __retryDelay = __initialDelay
    return connected


def disconnect():
##
## __disconnect
##
## Author - Tim Byrne
##
## Disconnects the module-level object __connection__.
##

    global connected

    try:
        if connected and Config.get_UseSSL() != 0:
            connection.close()
            DebugPrint(1, 'Disconnected from ' + Config.get_SSLHost())
    except:
        if not connectionError:  # We've already complained, so shut up
            DebugPrint(
                0,
                'Failed to disconnect from ' + Config.get_SSLHost() + ': ',
                sys.exc_info(),
                '--',
                sys.exc_info()[0],
                '++',
                sys.exc_info()[1],
                )

    connected = False

def postRequest(myconnection, to, what, headers):
    """
    postRequest calls requests on the connection to the destination 'to'
    and containing the header 'headers' and the content 'what'.
    
    The resulting information is returned as as string object.
    In case of connection time, the excetion GratiaTimeout is raised.
    """
    
    prev_handler = signal.signal(signal.SIGALRM, __handle_timeout__)
    signal.alarm(timeout)
    
    DebugPrint(4, 'DEBUG: POST')
    myconnection.request('POST', to, what, headers)
    DebugPrint(4, 'DEBUG: POST: OK')
    DebugPrint(4, 'DEBUG: Read response')
    responseString = utils.bytes2str(myconnection.getresponse().read())
    DebugPrint(4, 'DEBUG: Read response: OK')
    
    signal.alarm(0)
    signal.signal(signal.SIGALRM, prev_handler)
    
    return responseString


def sendUsageXML(meterId, recordXml, messageType='URLEncodedUpdate'):
    """
    sendUsageXML
   
    Author - Tim Byrne

    Contacts the 'GratiaCollector' web service, sending it an xml representation of Usage data
 
    param - meterId:  A unique Id for this meter, something the web service can use to identify 
          communication from this meter
    param - xmlData:  A string representation of usage xml
    """

    global connectionError
    global certificateRejected
    global __resending

    # Backward compatibility with old collectors

    if global_state.collector__wantsUrlencodeRecords == 0:
        messageType = 'update'

    try:

        # Connect to the web service, in case we aren't already
        # connected.  If we are already connected, this call will do
        # nothing

        if not connect():  # Failed to connect
            raise IOError  # Kick out to except: clause

        # Generate a unique Id for this transaction

        transactionId = meterId + utils.TimeToString().replace(':', r'')
        DebugPrint(3, 'TransactionId:  ' + transactionId)

        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:

            DebugPrint(0, 'Error: SOAP connection is no longer supported.')
            connectionError = True

            response_obj = response.Response(response.Response.Failed, 'Error: SOAP connection is no longer supported.')
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            queryString = encodeData(messageType, recordXml)

            # Attempt to make sure Collector can actually read the post.

            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            
            responseString = postRequest(connection, Config.get_CollectorService(), queryString, headers)
            
            response_obj = response.Response(response.Response.AutoSet, responseString)
            if response_obj.getCode() == response.Response.UnknownCommand:

                # We're talking to an old collector

                DebugPrint(0,
                           'Unable to send new record to old collector -- engaging backwards-compatible mode for remainder of connection'
                           )
                global_state.collector__wantsUrlencodeRecords = 0

                # Try again with the same record before returning to the
                # caller. There will be no infinite recursion because
                # __url_records has been reset

                response_obj = sendUsageXML(meterId, recordXml, messageType)
        else:

              # SSL

            DebugPrint(4, 'DEBUG: Encoding data for SSL transmission')
            queryString = encodeData(messageType, recordXml)
            DebugPrint(4, 'DEBUG: Encoding data for SSL transmission: OK')

            # Attempt to make sure Collector can actually read the post.

            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            responseString = postRequest(connection, Config.get_SSLCollectorService(), queryString, headers)
            response_obj = response.Response(response.Response.AutoSet, responseString)

            if response_obj.getCode() == response.Response.UnknownCommand:

                # We're talking to an old collector

                DebugPrint(0,
                           'Unable to send new record to old collector -- engaging backwards-compatible mode for remainder of connection'
                           )
                global_state.collector__wantsUrlencodeRecords = 0

                # Try again with the same record before returning to the
                # caller. There will be no infinite recursion because
                # __url_records has been reset

                response_obj = sendUsageXML(meterId, recordXml, messageType)
            elif response_obj.getCode() == response.Response.BadCertificate:
                connectionError = True
                certificateRejected = True
                response_obj = response.Response(response.Response.AutoSet, responseString)

        if response_obj.getCode == response.Response.ConnectionError or response_obj.getCode == response.Response.CollectorError:

            # Server threw an error - 503, maybe?

            connectionError = True
            response_obj = response.Response(response.Response.Failed, r'Server unable to receive data: save for reprocessing')
    except SystemExit:

        raise
    except socket.error as ex:
        if ex.args[0] == 111:
            DebugPrint(0, 'Connection refused while attempting to send xml to web service')
        else:
            DebugPrint(0, 'Failed to send xml to web service due to an error of type "', sys.exc_info()[0],
                       '": ', sys.exc_info()[1])
            DebugPrintTraceback(1)
        response_obj = response.Response(response.Response.Failed, r'Server unable to receive data: save for reprocessing')
    except GratiaTimeout as ex:
        connectionError = True
        if not __resending:
            DebugPrint(0, 'Connection timeout.  Will now attempt to re-establish connection and send record.')
            DebugPrint(2, 'Timeout seen as a GratiaTimeout.')
            __resending = 1
            response_obj = sendUsageXML(meterId, recordXml, messageType)
        else:
            DebugPrint(0, 'Received GratiaTimeout exception:')
            DebugPrintTraceback(1)
            response_obj = response.Response(response.Response.Failed, 'Failed to send xml to web service')
    except httplib.BadStatusLine as ex:
        connectionError = True
        if ex.args[0] == r'' and not __resending:
            DebugPrint(0, 'Possible connection timeout.  Will now attempt to re-establish connection and send record.')
            DebugPrint(2, 'Timeout seen as a BadStatusLine exception with the following argument:', ex.args)
            __resending = 1
            response_obj = sendUsageXML(meterId, recordXml, messageType)
        else:
            DebugPrint(0, 'Received BadStatusLine exception:', ex.args)
            DebugPrintTraceback(1)
            response_obj = response.Response(response.Response.Failed, 'Failed to send xml to web service')
    except:
        DebugPrint(0, 'Failed to send xml to web service due to an error of type "', sys.exc_info()[0], '": ',
                   sys.exc_info()[1])
        DebugPrintTraceback(1)

        # Upon a connection error, we will stop to try to reprocess but will continue to
        # try sending

        connectionError = True
        response_obj = response.Response(response.Response.Failed, 'Failed to send xml to web service')

    __resending = 0
    DebugPrint(2, 'Response: ' + str(response_obj))
    return response_obj


def encodeData(messageType, xmlData):
    """
     To the payload, we add the meta information:
        from: the name of the sender
        xmlfiles: number of records already passed to GratiaCore, still to be sent and still in individual xml files (i.e. number of gratia record in the outbox)
        tarfiles: number of outstanding tar files
        maxpendingfiles: 'current' number of files in a new tar file (i.e. an estimate of the number of individual records per tar file).
        backlog: estimated amount of data to be processed by the probe
    """
    probename = Config.get_ProbeName()
    maxpending = Config.get_MaxPendingFiles()
    xmlfiles = sandbox_mgmt.outstandingRecordCount + sandbox_mgmt.outstandingStagedRecordCount
    # Remove from the backlog number, the number of record we are about to upload
    if global_state.bundle_size> 0:
        xmlfiles -= (global_state.CurrentBundle.nItems - global_state.CurrentBundle.nHandshakes)
    else:
        xmlfiles -= 1
    if messageType[0:3] == 'URL' or messageType == 'multiupdate':
        result =  urllib.urlencode([
               ('command', messageType), ('arg1', xmlData), ('from', probename),
               ('xmlfiles', xmlfiles),  ('tarfiles', sandbox_mgmt.outstandingStagedTarCount),  ('maxpendingfiles', maxpending),  ('backlog', global_state.getEstimatedServiceBacklog()),
               ('bundlesize', global_state.bundle_size),
               ])
#        print >> sys.stderr,  "xmlfiles: "+str(xmlfiles)+" bundle:"+str(global_state.CurrentBundle.nItems - global_state.CurrentBundle.nHandshakes)
        return result
    else:
        return 'command=' + messageType + '&arg1=' + xmlData + '&from=' + probename + \
               '&xmlfiles=' + str(xmlfiles) + \
               '&tarfiles=' + str(sandbox_mgmt.outstandingStagedTarCount) + \
               '&maxpendingfiles=' + str(maxpending) + \
               '&backlog=' + str(global_state.getEstimatedServiceBacklog()) + \
               '&bundlesize=' + str(global_state.bundle_size)

