import os
import requests
import indico2org.inorganic as inorganic
from indico2org.utils import build_indico_request
import orgparse
from dataclasses import dataclass, asdict
from typing import Mapping, Any, Optional
from collections import OrderedDict
from datetime import datetime, date

@dataclass
class IndicoEvent(inorganic.OrgNode):
    id                  : str = None
    person_id           : str = None
    api_key             : str = None
    secret_key          : str = None
    detail              : str = 'contributions'
    sessions_filter     : str = ''
    archive             : int = 7
    tags_map            : Optional[Mapping[str, Any]]=None

    def __call__(self, indico_data={}, orig_event=None):
        """
        Convert indico event in org mode node
        """
        
        contributions_data, session_data = self.fetch_contributions()
        
        ### Change event data to selected session
        if session_data:
            for k, v in session_data.items():
                indico_data[k] = v

        ### Check if the event has yet to happen or has happened in the past N days, if not mark it for archival
        is_current = (datetime.strptime(indico_data['endDate']['date'], '%Y-%m-%d').date()-date.today()).days > -self.archive

        ### Sort the contributions
        indico_contributions = []
        children = []
        for contrib in contributions_data:
            indico_contributions.insert(0, { 'heading' : contrib['title'],
                                             'body' : contrib['description'],
                                             'todo' : 'TODO' if any([s['db_id']==self.person_id for s in contrib['speakers']]) and is_current else None,
                                             'properties' : { 'INDICO-ID' : contrib['id'],
                                                              'SPEAKER' : ', '.join([s['fullName'].replace(',', '') for s in contrib['speakers']])}
                                            } )

        ### Prepare the event adding per category tags
        self.heading = '[[%s][%s]]' % (indico_data['url'], indico_data['title'])
        self.timestamps = [(datetime.strptime(indico_data['startDate']['date']+' '+indico_data['startDate']['time'], '%Y-%m-%d %H:%M:%S'),
                             datetime.strptime(indico_data['endDate']['date']+' '+indico_data['endDate']['time'], '%Y-%m-%d %H:%M:%S'))]
        self.properties = { 'INDICO-ID' : indico_data['id'] }

        ### Set archival status
        if not is_current:
            self.tags = set(['ARCHIVE'])

        ### Add tags
        for tag, match in self.tags_map.items():
            if not match or match in indico_data['title']:
                self.tags.update([tag])
                
        ### Check if the event is already in the agenda and copy the relevant parts
        if orig_event:
            self.body = orig_event.get_body('raw')
            self.todo = orig_event.todo
            self.tags.update(orig_event.tags)
            self.properties.update(orig_event.properties)

            for contrib in orig_event.children:
                if not contrib.get_property('INDICO-ID', None):
                    children.append(inorganic.OrgNode.from_orgparse(contrib))
                else:
                    for from_indico in indico_contributions:
                        if contrib.properties['INDICO-ID'] == from_indico['properties']['INDICO-ID']:
                            from_indico['body'] = contrib.get_body('raw') if contrib.body != '' else from_indico['body']
                            from_indico['todo'] = contrib.todo if contrib.todo else from_indico['todo']
                            from_indico['tags'] = contrib.tags
                            from_indico['timestamps'] = [(ts.start, ts.end) for ts in contrib.datelist]
                            from_indico['properties'].update(contrib.properties)
                            from_indico['children'] = [inorganic.OrgNode.from_orgparse(child) for child in contrib.children]

                            break

        ### Create the node with contributions as subnodes
        self.children = [inorganic.OrgNode(**contrib) for contrib in indico_contributions]
        self.children.extend(children)
    
    def fetch_contributions(self, params={'order' : 'start'}):
        """
        Get list of contributions for given event or filtered session in the event
    
        :param params: str, optional default to {'order' : 'start'}, query params
        """

        path = '/export/event/%s.json' % self.id
        params['detail'] = self.detail
        api_call = 'https://indico.cern.ch'+build_indico_request(path, params, self.api_key, self.secret_key)
        api_data = requests.get(api_call).json()['results'][-1][self.detail]

        contributions_data = {}
        session_data = None
        if self.detail == 'sessions':
            session_data = {}
            for session in api_data:
                if self.sessions_filter and self.sessions_filter in session['title']:
                    session_data['url'] = session['url']
                    session_data['title'] = session['title']
                    session_data['startDate'] = session['startDate']
                    session_data['endDate'] = session['endDate']
                    contributions_data = session['contributions']
        else:
            contributions_data = api_data

        return contributions_data, session_data
                
@dataclass
class IndicoCategory(IndicoEvent):
    events_filter : str = ''
    query_params : Optional[Mapping[str, str]] = None

    def __call__(self, orig_nodes={}):
        updated_events = {}
            
        api_call = 'https://indico.cern.ch'+build_indico_request('/export/categ/%s.json'%self.id, self.query_params, self.api_key, self.secret_key)
        print(api_call)

        resp = requests.get(api_call)

        cat_info = None
        if len(resp.json()['results']):
            cat_info = resp.json()['additionalInfo']['eventCategories'][-1]['path'][-2]
            assert(str(cat_info['id']) == self.id)
        
        updated_events = OrderedDict()

        ### create event nodes 
        for event in resp.json()['results']:

            if not self.events_filter or self.events_filter in event['title']:
                args = asdict(self)
                args.pop('events_filter')
                args.pop('query_params')
                args['id'] = event['id']            
                event_node = IndicoEvent(**args)
                event_node(event, orig_nodes.get(event['id'], None))
                self.children.append(event_node)

                ### remove previous org node related to this event
                orig_nodes.pop(event['id'], None)
                
        ### cleanup local events (from indico) and preserve local nodes
        for id, event in orig_nodes.items():
            ### To be improved            
            fetch_range = (datetime.fromordinal(datetime.today().toordinal()-int(self.query_params['from'][1:-1])),
                           datetime.fromordinal(datetime.today().toordinal()+int(self.query_params['to'][1:-1])))
            event_start = event.rangelist[-1].start if len(event.rangelist) else None
            if not event.get_property('INDICO-ID', None) or not event_start or event_start<fetch_range[0] or event_start>fetch_range[1]:
                self.children.append(inorganic.OrgNode.from_orgparse(event))

        ### fill in category node properties
        self.heading = cat_info['name'] if cat_info else self.heading
        self.properties = { 'INDICO-ID' : cat_info['id'] } if cat_info else self.properties
        
