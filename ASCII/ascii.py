import os
import re
import sys
import urllib2
from xml.dom import minidom
from string import letters

import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

art_key = db.Key.from_path('ASCIIChan', 'arts')

def console(s):
    sys.stderr.write("%s\n" % s)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params) 

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&"
def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' % (p.lat, p.lon) for p in points)
    return GMAPS_URL + markers    



IP_URL = "http://api.hostip.info/?ip="
def get_coords(ip):
    ip = "4.2.2.2"
    ip = "23.24.209.141"
    url = IP_URL + ip
    content = None
    #content = urllib2.urlopen(url).read()
    try:
        content =  urllib2.urlopen(url).read()
    except urllib2.URLError:
        return

    if content:
        #parse xml and find co-ordinates#
        d = minidom.parseString(content)
        coords = d.getElementsByTagName("gml:coordinates")
        if coords and coords[0].childNodes[0].nodeValue:
            lon,lat = coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(lat, lon)


class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add = True)
    coords = db.GeoPtProperty()

class MainPage(Handler):
    def render_front(self, error='', title='', art=''):
        arts = db.GqlQuery("SELECT * "
                           "FROM Art "
                           "WHERE ANCESTOR IS :1 "
                           "ORDER BY CREATED DESC "
                           "LIMIT 10",
                           art_key)
        
        #prevent the running of multiple queries
        arts = list(arts)
        #find which arts have coords
        img_url = None
        points = filter(None, (a.coords for a in arts))
        self.write(repr(points))
        if points:
            img_url = gmaps_img(points)
            #display the image URL

	self.render('front_html.html', title = title, art = art, error = error, arts = arts, img_url = img_url)

    def get(self):
        self.write(repr(get_coords(self.request.remote_addr)))
        self.write(self.request.remote_addr)
        return self.render_front()

    def post(self):
        title = self.request.get('title')
	art = self.request.get('art')

	if title and art:
	    p = Art(parent=art_key, title = title, art = art)
            coords = get_coords(self.request.remote_addr)
	    #lookup the user's co-ordinates from the IP
            #if v have coordinates , add them to art
            if coords:
                p.coords = coords
	    p.put()

	    self.redirect('/')
	else:
	    error = "we need both title and artwork"        
	    self.render_front(error = error, title= title, art = art)

app = webapp2.WSGIApplication([('/', MainPage)], debug=True)
