#!/usr/bin/env python

import argparse
import json
import time
import systemd.daemon
from indico2org.utils import *
from indico2org.indiconodes import IndicoCategory

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Fetch events from selected indico categories and add them to org-agenda')
    parser.add_argument('output', metavar='output', type=str, help='path to the output org-agenda file')
    parser.add_argument('-c', '--config', dest='config', type=str, required=True, help='categories configuration file')
    parser.add_argument('-o', '--orgfile', dest='orgfile', type=str, help='path to an existing org-agenda file to merge')
    parser.add_argument('-f', '--from', dest='fromt', type=str, default='today', help='Fetch events from')
    parser.add_argument('-t', '--to', dest='to', type=str, default='+30d', help='Fetch events till')
    parser.add_argument('-a', '--archive', dest='archive', type=int, default=7,
                        help='Number (positive) of days in the past after which an event is marked for archival')
    parser.add_argument('-u', '--update', dest='update', action='store_true', default=False,
                        help='Update output file. Equivalent to setting -o equal to <output>')
    parser.add_argument('-d', '--daemon', dest='daemon', type=int, default=-1,
                        help='Run as a deamon. Positive integers denote hour intervals, negative = no deamon')

    options = parser.parse_args()

    if options.update:
        options.orgfile = options.output

    if options.daemon > 0:
        systemd.daemon.notify('READY=1')
    
    while True:    
        ### Load categories config file
        with open(options.config, 'r') as cats:
            options.config = json.load(cats)

        ### Get the existing agenda and create a map of ID -> node
        my_events = load_org_file(options.orgfile)
            
        indico_events = {}
        for cat in options.config['categories']:
            for k in ['person_id', 'api_key', 'secret_key']:
                cat[k] = options.config[k]

            cat['query_params'] = {
                'from'   : options.fromt,
                'to'     : options.to,
                'order'  : 'start',
                'pretty' : 'yes'
            }
            indico_events[cat['id']] = IndicoCategory(**cat)
            indico_events[cat['id']](my_events[cat['id']]['children'] if cat['id'] in my_events.keys() else {})

            my_events.pop(cat['id'], None)

        ### Write output with backup
        write_org_file(options.output, my_events=my_events, indico_events=indico_events)
        
        ### Zero is not really defined
        if options.daemon > 0:
            time.sleep(options.daemon*60*60)            
        else:
            exit()
