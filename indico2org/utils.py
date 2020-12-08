import os
import shutil
import hashlib
import hmac
import time
import orgparse
import functools
from datetime import datetime
from indico2org.inorganic import OrgNode

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

def build_indico_request(path, params, api_key=None, secret_key=None, persistent=False):
    """
    Build Indico HHTP API signed request.

    :param path: export base request (e.g. "/export/categ/XXX.json")
    :param params: query options.
    :param api_key: API key from indico personal page
    :param secret_key: secret key from indico personal page
    :param persistent: re-use persistent keys.
    """
    items = list(params.items()) if hasattr(params, 'items') else list(params)
    if api_key:
        items.append(('apikey', api_key))
    if secret_key:
        if not persistent:
            items.append(('timestamp', str(int(time.time()))))
        items = sorted(items, key=lambda x: x[0].lower())
        url = '%s?%s' % (path, urlencode(items))
        signature = hmac.new(secret_key.encode('utf-8'), url.encode('utf-8'),
                             hashlib.sha1).hexdigest()
        items.append(('signature', signature))
    if not items:
        return path
    return '%s?%s' % (path, urlencode(items))

def load_org_file(orgfile):
    """
    Helper function to load existing org files
    """
    
    my_events = {}

    if os.path.exists(orgfile):
        org_agenda = orgparse.load(orgfile)
        for cat in org_agenda.children:
            my_events[cat.get_property('INDICO-ID', cat.heading)] = { 'node' : cat, 'children' : {} }
            for event in cat.children:
                my_events[cat.get_property('INDICO-ID', cat.heading)]['children'][event.get_property('INDICO-ID', event.heading)] = event

    return my_events

def write_org_file(output, my_events={}, indico_events={}):
    """
    Write updated org file with backup if file exists
    """

    os.makedirs('/tmp/indico-to-org/', exist_ok=True)
    safe_write = '/tmp/indico-to-org/'+os.path.basename(output)+'.'+str(datetime.today().timestamp())
    with open(safe_write, 'w') as outfile:
        for id, node in my_events.items():
            outfile.write(OrgNode.from_orgparse(node['node']).render()+'\n')
        for id, node in indico_events.items():
            outfile.write(node.render()+'\n')

    if os.path.exists(output):
        shutil.copyfile(output, output+'.bak')

    shutil.copyfile(safe_write, output)
