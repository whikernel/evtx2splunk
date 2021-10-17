# -*- coding: utf-8 -*-
# !/usr/bin/env python

"""
    Prepare resolver json file for evtx2splunk
        Based on Blardy work (https://github.com/blardy/evtx2elk)
"""

import logging as log
import argparse
import sqlite3
import re
import json


class Resolver(object):

    def __init__(self, database):
        self.database = database

        self.filename = database.split('/')[-1]
        self.basename = './'
        if len(database.split('/')[-1]) > 1:
            self.basename = '/'.join(database.split('/')[:-1])
            self.basename += '/'

        self.database_conn = sqlite3.connect(database)

        self.database_cache_connectors = {
            database: self.database_conn
        }
        self.cache = {}

    def __del__(self):
        for database, database_conn in self.database_cache_connectors.items():
            database_conn.close()

    def open_db(self, database):
        """ Get a connection to the db from cache, open it otherwise.
        """
        conn = self.database_cache_connectors.get(database, False)
        if not conn:
            conn = sqlite3.connect(database)
            self.database_cache_connectors[database] = conn

        return conn

    def get_message_string(self, lcid=0x409):
        try:

            main_db = self.open_db(self.database)

            QUERY_PROVIDER_DB = """
            SELECT database_filename, log_source FROM event_log_providers  
                INNER JOIN message_file_per_event_log_provider ON 
                    message_file_per_event_log_provider.event_log_provider_key = event_log_providers.event_log_provider_key
                INNER JOIN message_files ON 
                    message_files.message_file_key = message_file_per_event_log_provider.message_file_key 
            """
            database_filenames = main_db.execute(QUERY_PROVIDER_DB).fetchall()

            evtx_bind = {}
            for dfne in database_filenames:
                log_source = dfne[1]

                if log_source not in evtx_bind:
                    evtx_bind[log_source] = {}

                database_filename = self.basename + dfne[0]
                provider_db = self.open_db(database_filename)
                cursor = provider_db.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [table[0] for table in cursor.fetchall() if 'message_table_0x' in table[0]]

                for table in tables:
                    if not table.startswith('message_table_0x{:08x}'.format(lcid)):
                        continue
                    query_event_mess = "SELECT message_identifier,message_string FROM {}".format(table)
                    message = provider_db.execute(query_event_mess).fetchall()

                    for mess in message:
                        str_mess = mess[1]
                        str_eventid = mess[0]

                        me = str_mess.replace('\n', '').replace('%n', '. ').replace('%t', ' ').encode("utf-8").decode(
                            "utf-8").replace('\r', ' ').replace('\t', ' ').rstrip()
                        me = re.sub(r'%(\d+)', r'{\1}', me)

                        eventid = int(str_eventid, 0) & 0xFFFF

                        if eventid in evtx_bind.get(log_source):
                            if me != evtx_bind[log_source][eventid]:

                                evtx_bind[log_source][eventid] = evtx_bind[log_source][eventid] + me

                        else:
                            evtx_bind[log_source][eventid] = me

            with open('evtx_data.json', 'w', encoding='utf-8') as f:
                json.dump(evtx_bind, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(e)
            return ''


def run():
    # Handle arguments
    argparser = argparse.ArgumentParser()

    argparser.add_argument('-d', '--database', required=True, help='Main winevt-kb database')

    args = argparser.parse_args()

    # configure logging
    resolver = Resolver(args.database)
    resolver.get_message_string()
    print("Done")

if __name__ == '__main__':
    run()
