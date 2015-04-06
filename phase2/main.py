#!/usr/bin/env python
#
# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import httplib2
import os
import threading
import urllib

from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from oauth2client.appengine import AppAssertionCredentials
from apiclient.discovery import build
import webapp2

# Global variables
API_KEY = "your-api-key"
PROJECT_ID = "your-numeric-project-id"

# [START credentials_setup]
# Set up the Prediction API service
CREDENTIALS = AppAssertionCredentials(
    scope='https://www.googleapis.com/auth/prediction' +
    ' https://www.googleapis.com/auth/devstorage.full_control')
SERVICES = threading.local()
# [END credentials_setup]


def get_service():
    """Returns a prediction API service object local to the current thread."""
    http = CREDENTIALS.authorize(httplib2.Http(memcache))
    if not hasattr(SERVICES, "service"):
        SERVICES.service = build("prediction", "v1.6", http=http,
                                 developerKey=API_KEY)
    return SERVICES.service


def predict_language(message):
    return True


# [START get_sentiment]
def get_sentiment(message):
    """Returns true if the predicted sentiment is positive, false otherwise."""
    body = {"input": {"csvInstance": [message]}}
    output = get_service().hostedmodels().predict(
        body=body, hostedModelName="sample.sentiment",
        project=PROJECT_ID).execute()
    prediction = output["outputLabel"]
    # Model returns either "positive", "negative" or "neutral".
    if prediction == "positive":
        return True
    else:
        return False
# [END get_sentiment]


def guestbook_key(guestbook_name=None):
    """Constructs an ndb key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name or 'default_guestbook')


class Author(ndb.Model):
    """A model representing an author."""
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)


# [START greeting_model]
class Greeting(ndb.Model):
    """A model representing an individual Guestbook entry.

    The model has an author, content, and date.
    """
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    positive = ndb.BooleanProperty(indexed=False)
# [END greeting_model]


class TrainModel(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('Not implemented!')


class CheckModel(webapp2.RequestHandler):
    def get(self):
        # checks if a model is trained
        self.response.out.write("Not implemented!")


class MainPage(webapp2.RequestHandler):
    def get(self):
        guestbook_name = self.request.get('guestbook_name')
        greetings_query = Greeting.query(
            ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
        greetings = greetings_query.fetch(10)
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        template_values = {
            'greetings': greetings,
            'url': url,
            'url_linktext': url_linktext
        }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))


# [START guestbook_handler]
class Guestbook(webapp2.RequestHandler):
    def post(self):
        guestbook_name = self.request.get('guestbook_name')
        greeting = Greeting(parent=guestbook_key(guestbook_name))

        if users.get_current_user():
            greeting.author = Author(
                identity=users.get_current_user().user_id(),
                email=users.get_current_user().email())
        greeting.content = self.request.get('content')
        greeting.positive = get_sentiment(greeting.content)
        greeting.put()
        self.redirect('/?' +
                      urllib.urlencode({'guestbook_name': guestbook_name}))
# [END guestbook_handler]


APPLICATION = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', Guestbook),
    ('/trainmodel', TrainModel),
    ('/checkmodel', CheckModel)
], debug=True)
