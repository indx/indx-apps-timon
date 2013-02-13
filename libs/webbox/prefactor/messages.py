#    This file is part of WebBox.
#
#    Copyright 2011-2012 Daniel Alexander Smith
#    Copyright 2011-2012 University of Southampton
#
#    WebBox is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    WebBox is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with WebBox.  If not, see <http://www.gnu.org/licenses/>.


import rdflib, logging, traceback, uuid
from httputils import resolve_uri
from webbox.box import WebBox
from rdflib.graph import Graph
from time import strftime

## TODO ----
## this module handles webbox<->webbox sharing
## DOES NOT WORK YET
## module needs to be updated for non-SPARQL thingies

class WebBoxMessages:
    """ A class that handles webbox messages, by looking at received RDF. """

    def __init__(self, graph, webbox):
        self.graph = graph
        self.webbox = webbox
        self.sioc_graph = webbox.webbox_ns + "ReceivedSIOCGraph" # the graph for received messages as sioc:Posts
        self.sioc_ns = "http://rdfs.org/sioc/ns#"; # SIOC namespace
        self.message_uri_prefix = self._webbox_url() + "/post-" # The URI prefix of the sioc:Post resources we make

    """ functions to return things from the webbox, do not use self.webbox directly. """
    def _webbox_url(self):
        return self.webbox.server_url

    def _uri2path(self, uri):
        return self.webbox.uri2path(uri)

    def _send_message(self, recipient, message):
        return self.webbox.send_message(recipient, message)

    def _subscriptions(self):
        return self.webbox.get_subscriptions()



    def _new_sioc_post(self, topic_uri, recipient_uri):
        """ Create a new rdf/xml sioc:Post based on a topic, and for a given recipient.
            Timestamp is set to now, and sender is taken from WebID authenticated person (TBC). """

        uri = self.message_uri_prefix + uuid.uuid1().hex

        graph = Graph()
        graph.add(
            (rdflib.URIRef(uri),
             rdflib.URIRef("http://xmlns.com/foaf/0.1/primaryTopic"),
             rdflib.URIRef(topic_uri)))

        graph.add(
            (rdflib.URIRef(uri),
             rdflib.URIRef("http://rdfs.org/sioc/ns#addressed_to"),
             rdflib.URIRef(recipient_uri)))

        graph.add(
            (rdflib.URIRef(uri),
             rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
             rdflib.URIRef(self.sioc_ns+"Post")))

        graph.add(
            (rdflib.URIRef(uri),
             rdflib.URIRef("http://purl.org/dc/terms/created"),
             rdflib.Literal(strftime("%Y-%m-%dT%H:%M:%SZ")))) # FIXME forces zulu time, which may be technically incorrect
        
        rdf = graph.serialize(format="xml") # rdf/xml
        return {"rdf": rdf, "uri": uri}

    def get_owners(self):
        """ Return an array of the URIs of all of the owners of this store (typically only one). """

        query = "SELECT DISTINCT ?owner WHERE { ?owner <%s> <%s> } " % (WebBox.address_predicate, self._webbox_url())
        response = self.webbox.query_store.query(query)
        if response['status'] >= 200 and response['status'] <= 299:
            results = response['data']
            logging.debug(str(results))
            owners = []
            for row in results:
                owner = unicode(row['owner']['value'])
                owners.append(owner)
            return owners
        else:
            logging.error("Couldn't get owner of store, response: %s" % str(response))
        return []
       

    def handle_all(self):
        """ Handle all WebBox message RDF types, called individually. """

        funcs = (
            self.handle_to_messages,
            self.handle_subscribe,
            self.handle_unsubscribe,
        )

        for func in funcs:
            response = func()
            if response is not None:
                logging.debug("Got response from function: "+str(response))
                return response

        logging.debug("handle_all returned None (success)")
        return None # success


    def subscribe(self, person_uri, resource_uri):
        """ Subscribe this person to this resource. """
        return self._subscriptions().subscribe(person_uri, resource_uri)

    def unsubscribe(self, person_uri, resource_uri):
        """ Unsubscribe this person from this resource. """
        return self._subscriptions().unsubscribe(person_uri, resource_uri)


    def handle_subscribe(self):
        logging.debug("Handling 'subscribe'")

        for s, p, o in self.graph:
            if unicode(p) == unicode(WebBox.subscribe_predicate):
                logging.debug("got a subscribe message, handling now...")
                person_uri = unicode(s)
                resource_uri = unicode(o)

                response = self.subscribe(person_uri, resource_uri)
                if response is not None:
                    return response

        return None # success

    def handle_unsubscribe(self):
        logging.debug("Handling 'unsubscribe'")

        for s, p, o in self.graph:
            if unicode(p) == unicode(WebBox.unsubscribe_predicate):
                logging.debug("got an unsubscribe message, handling now...")
                person_uri = unicode(s)
                resource_uri = unicode(o)

                response = self.unsubscribe(person_uri, resource_uri)
                if response is not None:
                    return response

        return None # success


    def handle_to_messages(self):
        """ Handle "to" messages, i.e. the webbox has received a message sent to us. """

        logging.debug("Handling 'to' messages.")

        for s, p, o in self.graph:
            if unicode(p) == unicode(WebBox.to_predicate):
                message_uri = unicode(s)
                recipient_uri = unicode(o)

                if recipient_uri in self.get_owners():
                    """ This message is to us. -  we will receive it. """
                    logging.debug("Got a message for us: " + message_uri)

                    # resolve URI of the message
                    try:
                        response = resolve_uri(message_uri, accept="*/*", include_info=True) # might not be rdf
                        rdf = response['data']
                        headers = response['headers']

                        ctype = ""
                        if "Content-type" in headers:
                            ctype = headers['Content-type']

                        logging.debug("resolved, headers are: "+str(headers))
                        logging.debug("resolved it.")

                        if ctype in self.webbox.rdf_formats:
                            # This is RDF, parse it etc

                            # TODO handle this properly by calling a method in WebBox

                            # put into 4store
                            # put resolved URI into the store
                            # put into its own graph URI in 4store
                            response = self.webbox.SPARQLPost(message_uri, rdf, ctype)
                            logging.debug("Put it in the store: "+str(response))

                            # TODO save to a file using a webbox method, as above

                            if response['status'] > 299:
                                return response
                        else:
                            # It's non-RDF, let's just save it
                            # TODO save to a file
                            # TODO add metadata to the store, by calling a method in webbox
                            pass


                        # store a copy as a sioc:Post in the SIOC graph
                        sioc_post = self._new_sioc_post(message_uri, recipient_uri)
                        response = self.webbox.SPARQLPost(self.sioc_graph, sioc_post['rdf'], "application/rdf+xml")

                        logging.debug("Put a sioc:Post in the store: "+str(response))

                        if response['status'] > 299:
                            return response


                        # TODO notify apps etc.
                        logging.debug("Received message of URI, and put it in store: " + message_uri)
                    except Exception as e:
                        logging.debug("Error with message received: " + str(e))
                        logging.debug(traceback.format_exc())
                        return {"data": "Error receiving message: "+message_uri, "status": 500, "reason": "Internal Server Error"}

                else:
                    """ This message is for other people. - we will send it. """
                    logging.debug("Got a message for other person: "+message_uri+", for: "+recipient_uri)

                    # send a message out with this triple.
                    success = self._send_message(recipient_uri, message_uri)
                    if type(success).__name__=='bool' and success == True:
                        # everything went better than expected
                        pass
                    else:
                        # oh dear, didn't work, success is the error message
                        return {"data": "", "status": 502, "reason": "Bad Gateway"}

        return None # none means successful.
        
