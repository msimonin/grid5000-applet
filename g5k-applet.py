#!/usr/bin/env python
#
import yaml
import base64
import sys
import gobject
import gtk
import appindicator
import httplib2 as http
import json
import threading
import argparse
from threading import Condition
import logging

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

logging.basicConfig(level = logging.DEBUG)
# Refresh periodically
REFRESH_INTERVAL = 600

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8',
}
uri = ''

def api(headers = headers, method = 'GET', url = '',  body = '', ):
    target = urlparse(url)
    h = http.Http(disable_ssl_certificate_validation=True)
    response, content = h.request(
              target.geturl(),
              method,
              body,
              headers
              )
    return response, content

gobject.threads_init()


class Updater(threading.Thread):
    def __init__(self, listener, site):
        super(Updater, self).__init__()
        self.listener = listener
        self.quit = False
        self.site = site
        self.uri = uri + '/sites/' + site['uid'] + '/status'
        self.cv = Condition()
        
    def run(self):
        counter = 0
        site_uid = self.site['uid']
        while not self.quit:
            gobject.idle_add(self.listener.start_refresh, site_uid)
            try:
                data = self.retrieve_status()
                nodes = data.get('nodes', [])
                length = len(nodes)
                free = []
                if (nodes):
                    free  = [i for i in nodes.keys() if nodes[i]['soft'] == 'free']

                gobject.idle_add(self.listener.update_item, site_uid, free)
            except:
              logging.error("Error while retrieving datas from %s ", site_uid)
            self.cv.acquire()
            self.cv.wait(REFRESH_INTERVAL)
            self.cv.release()

    def stop(self):
        self.quit = True
        self.cv.acquire()
        self.cv.notify() 
        self.cv.release()

    def refresh(self):
        self.cv.acquire()
        self.cv.notify() 
        self.cv.release()

    def retrieve_status(self):
        response, content = api(url = self.uri)
        if response['status'] != '200':
            logging.error("Error")
            raise Exception(response['status'])

        return json.loads(content)

class CheckStatus:
    def __init__(self, config):
        self.ind = appindicator.Indicator("g5k-status",
                "/home/msimonin/python/unity-applet/Logo.png",
                appindicator.CATEGORY_APPLICATION_STATUS)
        self.ind.set_status(appindicator.STATUS_ACTIVE)
        self.menu_setup()
        self.items = {}

        self.sites = self.retrieve_sites()
        self.t = {}
        for site in self.sites:
          site_uid = site['uid']
          self.t[site_uid] = Updater(self, site)
          logging.debug("Created updater for %s", site_uid)
          self.t[site_uid].start()


    def start_refresh(self, site_uid):
        item = self.items.get(site_uid, None)
        if (item is not None):
            label = item.get_label()
            item.set_label('*' + label)

    def update_label(self, counter):
        self.ind.set_label(str(counter))

    def update_item(self, site_uid, free):
        logging.debug("Updating item %s", site_uid)
        item = self.items.get(site_uid)
        if (item is None):
            self.items[site_uid] = gtk.MenuItem(site_uid)
            self.items[site_uid].connect("activate", self.show)
            self.items[site_uid].show()
            self.menu.append(self.items[site_uid])

        self.items[site_uid].set_label(site_uid + " : "  + str(len(free)))
        return False


    def menu_setup(self):
        self.menu = gtk.Menu()

        self.refresh_item = gtk.MenuItem("Refresh")
        self.refresh_item.connect("activate", self.refresh)
        self.refresh_item.show()
        self.menu.append(self.refresh_item)

        self.quit_item = gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)

        self.ind.set_menu(self.menu)

    def show(self):
        return True

    def quit(self, widget):
        for site in self.sites:
            site_uid = site['uid']
            self.t[site_uid].stop()
        sys.exit(0)

    def refresh(self, widget):
        logging.debug("Refreshing sites")
        for site in self.sites:
            site_uid = site['uid']
            self.t[site_uid].refresh()


    def main(self):
        #gtk.timeout_add(DISPLAY_INTERVAL*1000, self.display)
        gtk.main()

    def retrieve_sites(self):
        logging.debug("Retrievings sites status")
        url = uri + '/sites'
        response, content = api(
            headers = headers,
            url = uri + '/sites',
            )
        if response['status'] != '200':
            logging.error("Error")
            raise Exception(response['status'])
        sites = json.loads(content).get('items')
        logging.debug("Successfully retrieved %d sites", len(sites))

        return sites

if __name__ == "__main__":
    logging.info("Welcome to G5k applet")
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config" , help="the configuration file")
    arg = parser.parse_args()
    
    conf_file = open(arg.config, 'r')
    config = yaml.load(conf_file)
    headers['Authorization'] = 'Basic ' + base64.b64encode(config["username"] + ":" + config["password"])
    uri = config['base_uri']

    indicator = CheckStatus(config)
    indicator.main()
