# -*- coding: utf-8 -*-
# !/usr/bin/env python

"""
    Ingest EVTX file(s) into an Splunk
        Based on Blardy work (https://github.com/blardy/evtx2elk)
        Based on Dan Gunter work (https://dragos.com/blog/20180717EvtxToElk.html)

    Special thanks to Ektoplasma for its contribution
"""
__progname__ = "evtx2splunk"
__date__ = "2020-01-10"
__version__ = "0.1"
__author__ = "whitekernel - PAM"

import argparse
import json
import time
import os
import logging as log
import sys
import shutil
from datetime import datetime, timezone
from functools import partial
from glob import glob
from multiprocessing.dummy import Pool
from multiprocessing import cpu_count
from pathlib import Path
from typing import TextIO
import tqdm

from splunk_http_event_collector import http_event_collector
from dotenv import load_dotenv

from evtxdump.evtxdump import EvtxDump
from splunk_helper import SplunkHelper

LOG_FORMAT = '%(asctime)s %(levelname)s %(funcName)s: %(message)s'
LOG_VERBOSITY = {
    'DEBUG': log.DEBUG,
    'INFO': log.INFO,
    'WARNING': log.WARNING,
    'ERROR': log.ERROR,
    'CRITICAL': log.CRITICAL,
}
log.basicConfig(format=LOG_FORMAT, level=log.INFO, datefmt='%Y-%m-%d %I:%M:%S')


class Evtx2Splunk(object):
    """
    Convert EVTX to JSON and index the data in Splunk
    Features auto create of index and HEC token
    """

    def __init__(self):
        """
        Init functton of the Evtx2Splunk class
        """
        self._sh = None
        self._hec_server = None
        self._nb_ingestors = 1
        self._is_test = False
        self._resolve = True
        self._evtxdump = None
        self._resolver = {}
        self.myevent = []

    def configure(self, config: dict, index: str, nb_ingestors: int, testing: bool, no_resolve: bool, proxies: dict):
        """
        Configure the instance of SplunkHelper
        :param config: The configuration of evtx2splunk
        :param nb_ingestors: NB of ingestors to use
        :param testing: If yes, no file would be injected into splunk to preserve licenses
        :param index: Index where to push the files
        :param no_resolve: Disable Event ids resolution
        :return: True if successfully configured else False
        """
        # Load the environment variables for .env
        load_dotenv()

        self._nb_ingestors = nb_ingestors

        ret = self._get_bind_conf(config.get("evtxdump_config_file"))
        if ret is False:
            log.error("Something went wrong while parsing evtxdump config file")

        if no_resolve:
            log.info("Event ID resolution disabled")
            self._resolve = False

        elif not Path("evtx_data.json").exists():
            log.error("Event ID data file not found")
            log.error("Will without resolution")
            self._resolve = False

        if self._resolve:
            with open("evtx_data.json", "r") as fdata:
                try:
                    self._resolver = json.load(fdata)
                except Exception as e:
                    log.error("Unable to read event data file. Error {e}".format(e=e))
                    return False

        self._is_test = testing
        if self._is_test:
            log.warning("Testing mode enabled. NO data will be injected into Splunk")

        log.info("Init SplunkHelper")
        self._sh = SplunkHelper(splunk_url=config.get('splunk_url'),
                                splunk_port=config.get('splunk_mport'),
                                splunk_ssl_verify=config.get('splunk_ssl_verify'),
                                username=config.get('splunk_user'),
                                password=config.get('splunk_pass'),
                                proxies=proxies)

        # The SplunkHelper instantiation holds a link_up
        # flag that indicated whether it could successfully reach
        # the specified SPlunk instance
        if self._sh.link_up:

            # Fetch or create the HEC token from Splunk
            hect = self._sh.get_or_create_hect()

            # Create a new index
            if self._sh.create_index(index=index):
                # Associate the index to the HEC token so the script can send
                # the logs to it
                self._sh.register_index_to_hec(index=index)

                # Instantiate HEC class and configure
                self._hec_server = http_event_collector(token=hect,
                                                        http_event_server=config.get('splunk_url'))
                self._hec_server.http_event_server_ssl = config.get('splunk_ssl')
                self._hec_server.index = index
                self._hec_server.input_type = "json"
                self._hec_server.popNullFields = True

                return True

        return False

    def send_jevtx_file_to_splunk(self, records_stream: TextIO, source: str, sourcetype: str):
        """
        From a record stream - aka file json stream - read and update the stream with enhanced data
        then push to splunk
        :param records_stream: TextIO - Input JSON stream to index
        :param source: Str representing the source indexed as in the Splunk sense
        :param sourcetype: Str representing the source type to index - always JSON here
        :param source_size: Size of the input file
        :return: True if the indexing was successfully else False
        """

        try:
            if records_stream is not None:

                is_host_set = False

                # Prepare Splunk payload to send
                payload = {}
                payload.update({"source": source})
                payload.update({"sourcetype": sourcetype})

                # Send batch of events it will be handled consecutively
                # and sent to the Splunk HEC endpoint

                for record_line in records_stream:

                    try:
                        record = json.loads(record_line)
                    except ValueError:
                        continue

                    if is_host_set is False:
                        payload.update({"host": record["Event"]["System"]["Computer"]})
                        is_host_set = True

                    # Must convert the timestamp in epoch format... seconds.milliseconds
                    # examples evtx time "2020-06-16T12:54:38.766579Z" "'%Y-%m-%dT%H:%M:%S.%fZ'
                    # But sometimes, milliseconds are not present
                    try:
                        dt_obj = datetime.strptime(
                            record["Event"]["System"]["TimeCreated"]["#attributes"]["SystemTime"],
                            '%Y-%m-%dT%H:%M:%S.%fZ')
                    except:
                        dt_obj = datetime.strptime(
                            record["Event"]["System"]["TimeCreated"]["#attributes"]["SystemTime"],
                            '%Y-%m-%dT%H:%M:%SZ')

                    try:

                        # Splunk does not want microseconds but it can be sent anyway
                        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                        epoch = dt_obj.timestamp()

                    except Exception as e:
                        log.warning("Timestamp warning. {error}".format(error=e))
                        log.warning("Falling back to default")
                        # Use case for NTFS : 1601-01-01 00:00:00.000
                        dt_obj = datetime.now()
                        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                        epoch = dt_obj.timestamp()

                    record["module"] = record["Event"]["System"]["Channel"]

                    if self._resolve:
                        message = self.format_resolve(record)
                        if message:
                            record["message"] = message

                    payload.update({"time": epoch})
                    payload.update({"event": record})

                    # Finally send the stream
                    if not self._is_test:
                        self._hec_server.batchEvent(payload)
                    else:
                        log.debug("Test mode. Would have injected : {payload}".format(payload=payload))

                return True

            else:
                return False

        except Exception as e:
            log.warning(e)
            return False

    def format_resolve(self, record):
        """
        Return a formatted string of the record if formatting is available
        :param record: Record to format
        :return: Formatted string of the record
        """
        try:
            provider = record["Event"]["System"]["Provider"]["#attributes"]["Name"]
            event_id = record["Event"]["System"]["EventID"]

            if type(event_id) == dict:
                event_id = record["Event"]["System"]["EventID"]["#text"]

            if provider in self._resolver:

                if self._resolver[provider].get(str(event_id)):
                    message = self._resolver[provider].get(str(event_id))
                    return message

        except Exception as e:
            log.error(e)

        return ""

    def ingest(self, input_files: str, keep_cache: bool, use_cache: bool):
        """
        Main function of the class. List the files, call the converter
        and then multiprocess the input.
        :param input_files: Path to a file or a folder to ingest
        :param keep_cache: Set to true to keep json temporary folder at the end of the process
        :return: Nothing
        """
        # Get the folder to index
        input_folder = Path(input_files)

        # Temporary files are placed in the same directory, not in tmp as there is a
        # a risk over overloading tmp dir depending on the partitioning
        if input_folder.is_file():
            output_folder = input_folder.parents[0] / "json_evtx"
            self._nb_ingestors = 1

        elif input_folder.is_dir():
            output_folder = input_folder / "json_evtx"

        else:
            log.error("Input is neither a file or a directory")
            return

        if not use_cache:
            log.info("Starting EVTX conversion. Nothing will be output until the end of conversion")
            if sys.platform == "win32":
                evtxdump = EvtxDump(output_folder, Path(self._evtxdump["configuration"]["evtx_dump"]["windows"]),
                                    fdfind=self._evtxdump["configuration"]["fdfind"]["windows"])
            else:
                evtxdump = EvtxDump(output_folder, Path(self._evtxdump["configuration"]["evtx_dump"]["linux"]),
                                    fdfind=self._evtxdump["configuration"]["fdfind"]["linux"])

            evtxdump.run(input_folder)

        else:
            log.warning("Using cached files")

        # Files are converted, now build a list of the files to index
        # dispatch by size
        evtx_files = [files for files in output_folder.rglob('*.json')]

        sublists = self.dispatch_files_bysize(self._nb_ingestors, evtx_files)
        self.desc = ""

        # Create pool of processes and partial the input
        master_pool = Pool(self._nb_ingestors)
        master_partial = partial(self.ingest_worker, sublists)

        master_pool.map(master_partial, range(self._nb_ingestors))
        master_pool.close()

        # Assure to flush all the threads before we end the function
        self._hec_server.flushBatch()

        # Clean the temporary folder if not indicated not to do so
        if not keep_cache:
            shutil.rmtree(output_folder, ignore_errors=True)

    def ingest_worker(self, sublist: list, index: int):
        """
        Ingestor worker that actually index a set of JSON files into Splunk
        Meant to be Pool-ed
        :param sublist: list - List of sublist of files to index
        :param index: int - index of the sublist ot index
        :return: Tuple CountSuccess,TotalCount
        """
        count = 0
        sum = 0
        desc = ""
        file_log = tqdm.tqdm(total=0, position=index * 2, bar_format='{desc}')
        with tqdm.tqdm(total=len(sublist[index]), position=(index * 2) + 1, desc=desc, unit="files") as progress:
            for jevtx_file in sublist[index]:

                sum += 1
                with open(jevtx_file, "r") as jevtx_stream:

                    if not self._is_test:
                        desc = "[Worker {index}] Processing {evtx}".format(index=index, evtx=jevtx_file.name)
                    else:
                        desc = "[Worker {index}] [TEST] Processing {evtx}".format(index=index, evtx=jevtx_file.name)

                    ret_t = self.send_jevtx_file_to_splunk(records_stream=jevtx_stream,
                                                           source="event_" + jevtx_file.name,
                                                           sourcetype="json"
                                                           )
                    count += 1 if ret_t else 0
                    file_log.set_description_str(desc)
                    progress.update(1)

        return count, sum

    @staticmethod
    def list_files(file: Path, folder: Path, extension='*.evtx'):
        """
        It returns a list of files based on teh given input path and filter on extension
        :param file: Unitary file to index
        :param folder: Folder to index
        :param extension: Extensions of the files to index - evtx by default
        :return: A list of files to index
        """
        if file:
            return [file]
        elif folder:
            return [y for x in os.walk(folder) for y in glob(os.path.join(x[0], extension))]
        else:
            return []

    @staticmethod
    def dispatch_files_bysize(nb_list: int, files: list):
        """
        It creates N list of files based on filesize to average the size between lists.
        :param nb_list: Number of lists to create
        :param files: List of files to dispatch
        :return: List of list
        """

        log.info('Having {} files to dispatch in {} lists'.format(len(files), nb_list))

        sublists = {}
        for list_id in range(0, nb_list):
            sublists[list_id] = {
                'files': [],
                'size': 0
            }

        def _get_smallest_sublist(sublists):
            """
            get the smallest sublist
            """
            smallest_list_id = 0
            for list_id, sublist in sublists.items():
                if sublist['size'] < sublists[smallest_list_id]['size']:
                    smallest_list_id = list_id

            return smallest_list_id

        for file in files:
            log.debug('dispatching {}'.format(file))
            list_id = _get_smallest_sublist(sublists)
            sublists[list_id]['files'].append(file)
            sublists[list_id]['size'] += os.stat(file).st_size

        for list_id, sublist in sublists.items():
            log.info(
                ' List [{}] Having {} files for a size of {}'.format(list_id, len(sublist['files']), sublist['size']))

        return [sublist['files'] for list_id, sublist in sublists.items()]

    def _get_bind_conf(self, bind_file):

        try:
            with open(bind_file, "r") as f_input:
                self._evtxdump = json.load(f_input)
                return True
        except Exception as e:
            log.warning(e)
            return False


"""
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", help="increase output verbosity", choices=LOG_VERBOSITY, default='INFO')

    parser.add_argument('--input', help="Evtx file to parse")

    parser.add_argument('--nb_process', type=int, default=cpu_count(),
                        help="Number of ingest processes to spawn, only useful for more than 1 file")

    parser.add_argument('--index', default="winevt", help="index to use for ingest process")

    parser.add_argument('--keep_cache', action="store_true",
                        help="Keep JSON cache for future use - Might take a lot of space")

    parser.add_argument('--use_cache', action="store_true",
                        help="Use the cached files")

    parser.add_argument('--test', action="store_true",
                        help="Testing mode. No data is sent to Splunk but index and HEC token are created.")

    parser.add_argument('--no_resolve', action="store_true",
                        help="Disable the event id resolution. If the data file is not found, will be disabled automatically")

    args = parser.parse_args()
    log.basicConfig(format=LOG_FORMAT, level=LOG_VERBOSITY[args.verbosity], datefmt='%Y-%m-%d %I:%M:%S')

    start_time = time.time()

    e2s = Evtx2Splunk()

    if e2s.configure(index=args.index, nb_ingestors=args.nb_process, testing=args.test, no_resolve=args.no_resolve):
        e2s.ingest(input_files=args.input, keep_cache=args.keep_cache, use_cache=args.use_cache)

    end_time = time.time()

    log.info("Finished in {time}".format(time=end_time-start_time))
"""
