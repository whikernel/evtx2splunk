# -*- coding: utf-8 -*-
# !/usr/bin/env python

"""
    Splunk HEC Helper, part of evtx2splunk
"""

__progname__ = "evtx2splunk"
__date__ = "2020-01-10"
__version__ = "0.1"
__author__ = "whitekernel - PAM"

from typing import Any

import requests
import urllib3
from requests.auth import HTTPBasicAuth
import logging as log
from xml.dom.minidom import parse, parseString

from requests.packages.urllib3.exceptions import InsecureRequestWarning


class SplunkHelper(object):
    def __init__(self, splunk_url: str, splunk_port: int, splunk_ssl_verify: bool, username: str, password: str
                 , proxies: dict):
        """
        Init class of the helper.
        :param splunk_url: URL of the Splunk instance
        :param splunk_port: port of the splunk instance
        :param splunk_ssl_verify: True to check ssl certificate
        :param username: Administrative account
        :param password: Password account
        :param proxies: Proxies to use to contact the Splunk server
        """
        self._surl = "https://{url}:{port}/".format(url=splunk_url,
                                                    port=splunk_port)
        self._suser = username
        self._spwd = password
        self._ssl_verify = splunk_ssl_verify
        self._proxies = proxies
        if not self._ssl_verify:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self.link_up = self.test_connection()
        self._hec_token = None

    def _uri(self, uri: str):
        """
        Return a complete URL from an URI
        :param uri: URI
        :return: A string with the complete URL
        """
        return self._surl + uri

    def _request(self, uri: str, method: str = "GET", data: Any = None):
        """
        Make a request and handle the errors
        :param uri: URI to request
        :param method: Method to index
        :param data: Data for post method
        :return: Tuple (Bool, Response)
        """
        ret = False
        response = None
        session = requests.Session()
        session.proxies.update(self._proxies)

        try:

            if method == "GET":
                response = session.get(url=self._uri(uri=uri),
                                       verify=self._ssl_verify,
                                       auth=HTTPBasicAuth(self._suser, self._spwd),
                                       timeout=2)
            elif method == "POST":
                response = session.post(url=self._uri(uri=uri),
                                        data=data,
                                        verify=self._ssl_verify,
                                        auth=HTTPBasicAuth(self._suser, self._spwd),
                                        timeout=2)
        except Exception as e:
            log.error(e)
            log.error("Unable to connect to Splunk. Please check URL and ports")
            return ret, None

        if response.status_code == 401:
            log.error("Unable to connect to Splunk. Please check administrative credentials")

        elif response.status_code == 200 or response.status_code == 201:
            ret = True

        else:
            log.error("Server error. See message below. Status {status}".format(status=response.status_code))

        return ret, response

    def test_connection(self):
        """
        Test connection to the Splunk instance
        :return: True if successful, else False
        """
        ret, _ = self._request(uri='services/data/inputs/http')
        return ret

    def create_index(self, index: str):
        """
        Create an index in the Splunk instance.
        :return: True if created successfully
        """
        if not self.link_up:
            return False

        # Check if we have one index with this name already
        ret, response = self._request(uri='services/data/indexes/{index}'.format(index=index))
        if ret:
            log.info("{index} already created. Continuing".format(index=index))
            return True

        data = {
            "name": index
        }

        ret, response = self._request(uri='services/data/indexes',
                                      method="POST",
                                      data=data)
        if ret:
            log.info("Index {index} created successfully".format(index=index))
            return True

        else:
            log.error("Unable to create index {index}".format(index=index))
            log.error("{message}".format(message=response.text))
            return False

    def get_or_create_hect(self):
        """
        Look for an HEC token or create one if none is available
        :return:
        """
        hect = None
        if not self.link_up:
            return hect

        if self._hec_token:
            return self._hec_token

        # Check if a token is already registered under the same name
        token_name = 'evtx2splunk'
        ret, response = self._request(uri='services/data/inputs/http/%s' % token_name)
        if ret:

            dom = parseString(response.text)

            for e in dom.getElementsByTagName("s:key"):

                if e.getAttribute("name") == "token":
                    # We have a key, return the node value which
                    # is the HEC token
                    log.info("HEC token found")
                    self._hec_token = e.firstChild.nodeValue
                    return self._hec_token

        # If we are here, we don't have a token yet, so create it
        data = {
            "name": token_name
        }

        ret, response = self._request(uri='services/data/inputs/http',
                                      method="POST",
                                      data=data)
        if ret:

            dom = parseString(response.text)

            for e in dom.getElementsByTagName("s:key"):

                if e.getAttribute("name") == "token":
                    # We have a key, return the node value which
                    # is the HEC token
                    log.info("HEC token created successfully")
                    self._hec_token = e.firstChild.nodeValue
                    return self._hec_token

        log.error("Unable to create HEC token")
        log.error("{message}".format(message=response.text))

        return hect

    def register_index_to_hec(self, index: str):
        """
        Register an index to the HEC listener
        :param index: Index to add
        :return: True if added successfully, else False
        """
        # Retrieve the HEC token
        if not self._hec_token:
            self._hec_token = self.get_or_create_hect()

        # Retrieve the list of indexes allowed to be pushed with the HEC token
        ret, response = self._request(uri='services/data/inputs/http/evtx2splunk')
        indexes = []
        if ret:

            dom = parseString(response.text)

            for e in dom.getElementsByTagName("s:key"):

                if e.getAttribute("name") == "indexes":
                    indexes = [item.firstChild.nodeValue for item in e.getElementsByTagName("s:item")]

        # Check if the index is already associated
        if index in indexes:
            log.info("Index already registered, continuing")
            return True

        # Add the index and push
        indexes.append(index)
        data = {
            "indexes": ",".join(indexes),
            "index": indexes[0]
        }
        ret, response = self._request(uri='services/data/inputs/http/evtx2splunk',
                                      method="POST",
                                      data=data)

        if ret:
            log.info("Index associated successfully")
            return True

        log.error("Unable to create associate index with the HEC token")
        log.error("{message}".format(message=response.text))
        return False
