# -*- coding: utf-8 -*-
# !/usr/bin/env python

"""
    Splunk HEC Helper, part of evtx2splunk

    Thanks to Ektoplasma for its contribution

"""
__progname__ = "evtx2splunk"
__date__ = "2020-01-10"
__version__ = "0.1"
__author__ = "Ektoplasma"

import logging as log
import subprocess
from pathlib import Path


class EvtxDump(object):
    """
    Wrapper around evtx_dump, a tool writen in go for speed conversion of evtx
    """
    def __init__(self, output_path: Path=None, path_evtx_dump: Path=None, fdfind: str ="fdfind"):
        """
        Init method of the EvtxDump class. Just saves some input args
        :param output_path: Path - Output path of the files
        :param path_evtx_dump: Path - Path of the evtx path binary
        :param fdfind: Path - ffind
        """
        self._output_path = output_path
        self._evtx_dump = path_evtx_dump
        self._fdfind = fdfind

    def run(self, evtxdata: Path):
        """
        Dispatch depending whether it's a file or a directory
        :param evtxdata:
        :return:
        """
        if evtxdata.is_file():
            return self._convert_file(evtxdata)

        elif evtxdata.is_dir():
            return self._convert_files(evtxdata)

        else:
            log.error("Data is neither a file nor a folder, not supported")
            return False

    def _convert_file(self, evtxdata: Path):
        """
        Convert a file to json thanks to evtx_dump
        :param evtxdata: Path - Path to the evtx file
        :return: True if successful, else False
        """

        completed = False
        filename = evtxdata.name + ".json"

        out_file = Path(self._output_path, filename)

        if out_file.exists():
            log.error("Destination file already exists")
            return completed

        try:
            command = (self._evtx_dump, evtxdata, "-o", "jsonl", "-f", out_file, "--no-confirm-overwrite")
            completed = subprocess.check_call(command)
        except Exception as e:
            log.error(e)

        return completed

    def _convert_files(self, evtxdata: Path):
        """
        Convert a set of files to json thanks to evtx_dump and ffind
        :param evtxdata: Path - Path to a folder containing EVTX
        :return: True if successful, else False
        """

        completed = False
        list_evtx = evtxdata.rglob("*.evtx*")

        for evtx in list_evtx:

            filename = evtx.name + ".json"

            out_file = Path(self._output_path, filename)

            if out_file.exists():
                log.error("Destination file already exists")
                return 1

        try:
            command = (self._fdfind, r".*\.evtx\w*", evtxdata, "-x",
                       self._evtx_dump, "-o", "jsonl", "{}", "--no-confirm-overwrite",
                       "-f", Path(self._output_path, "{/.}.json"))
            completed = subprocess.check_call(command)
        except Exception as e:
            log.error(e)

        return completed

