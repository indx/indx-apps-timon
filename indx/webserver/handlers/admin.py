#    Copyright (C) 2011-2013 University of Southampton
#    Copyright (C) 2011-2013 Daniel Alexander Smith
#    Copyright (C) 2011-2013 Max Van Kleek
#    Copyright (C) 2011-2013 Nigel R. Shadbolt
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License, version 3,
#    as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging, re
from indx.webserver.handlers.base import BaseHandler
import indx.indx_pg2 as database
from twisted.internet.defer import Deferred
import indx.server # causes an infinite dependency loop

class AdminHandler(BaseHandler):
    """ Add/remove boxes, add/remove users, change config. """
    base_path = 'admin'
    
    def info(self, request):
        """ Information about the INDX. """
        return self.return_ok(request, data = {"indx_uri": self.webserver.server_url} )

    def invalid_name(self, name):
        # import indx.server
        """ Check if this name is safe (only contains a-z0-9_-). """ 
        return re.match("^[a-z0-9_-]*$", name) is None and name not in indx.server.BOX_NAME_BLACKLIST

    def _is_box_name_okay(self, name):
        """ checks new box, listening on /name. """
        d = Deferred()
        if self.invalid_name(name): return d.callback(False)
        def cont(boxes):
            logging.debug('boxes {0}, {1}'.format(boxes, not name in boxes))
            return d.callback(not name in boxes)
        self.webserver.get_master_box_list().addCallback(cont).addErrback(d.errback)
        return d

    def delete_box_handler(self, request):
        """ Delete a box. """
        args = self.get_post_args(request)
        box_name = args['name'][0]
        username,password = self.get_session(request).username, self.get_session(request).password
        logging.debug('asking to delete box ' + box_name)

        logging.debug("Deleting box {0} for user {1}".format(box_name,username))
        try:
            success = database.delete_box(box_name,username,password) ## TODO make this nonblocking
            if success:
                return self.return_no_content(request)
            else:
                return self.return_internal_error(request)
        except Exception as e:
            logging.debug(' error deleting box {0} '.format(e))
            return self.return_internal_error(request)
    
    def create_box_handler(self, request):
        """ Create a new box. """
        args = self.get_post_args(request)
        box_name = args['name'][0]
        username,password = self.get_session(request).username, self.get_session(request).password
        logging.debug('asking to create box ' + box_name)
        def start():
            self.webserver.register_box(box_name,self.webserver.root)
            self.return_created(request)
        def do_create():
            logging.debug("Creating box {0} for user {1}".format(box_name,username))
            try:
                success = database.create_box(box_name,username,password) ## TODO make this nonblocking
                if success:
                    return start()
                else:
                    return self.return_internal_error(request)
            except Exception as e:
                logging.debug(' error creating box {0} '.format(e))
                return self.return_internal_error(request)
        def check(result):
            try :
                logging.debug(' result > {0} '.format(result))
                return do_create() if result else self.return_bad_request(request)
            except Exception as e :
                logging.debug('{0}'.format(e))
        self._is_box_name_okay(box_name)\
            .addCallback(check)\
            .addErrback(lambda *er: logging.debug('{0}'.format(er)) and self.return_forbidden(request))        

    def list_boxes_handler(self,request):
        username,password = self.get_session(request).username, self.get_session(request).password
        def boxes(db_list):
            return self.return_ok(request, data={"list": db_list})
        database.list_boxes(username, password)\
            .addCallback(boxes)\
            .addErrback(lambda *x: self.return_internal_error(request))

    def create_user_handler(self, request):
        args = self.get_post_args(request)
        new_username, new_password = args['username'][0],  args['password'][0]
        username,password = self.webserver.get_indx_user_password()
        logging.debug("Creating new user with username: {0}".format(new_username))
        database.create_user(new_username, new_password, username, password)\
            .addCallback(lambda *x: self.return_ok())\
            .addErrback(lambda *x: self.return_internal_error())
        
AdminHandler.subhandlers = [
    {
        'prefix': 'list_boxes',
        'methods': ['GET'],
        'require_auth': True,
        'require_token': False,
        'handler': AdminHandler.list_boxes_handler,
        'content-type':'text/plain', # optional
        'accept':['application/json']
    },    
    {
        'prefix': 'delete_box',
        'methods': ['POST'],
        'require_auth': True,
        'require_token': False,
        'handler': AdminHandler.delete_box_handler,
        'content-type':'text/plain', # optional
        'accept':['application/json']
    },
    {
        'prefix': 'create_box',
        'methods': ['POST'],
        'require_auth': True,
        'require_token': False,
        'handler': AdminHandler.create_box_handler,
        'content-type':'text/plain', # optional
        'accept':['application/json']
    },
    {
        'prefix': 'create_box',
        'methods': ['POST'],
        'require_auth': False,
        'require_token': False,
        'handler': BaseHandler.return_forbidden,
        'content-type':'text/plain', # optional
        'accept':['application/json']
    },
    {
        'prefix': 'create_user',
        'methods': ['POST'],
        'require_auth': True,
        'require_token': False,
        'handler': AdminHandler.create_user_handler,
        'content-type':'text/plain', # optional
        'accept':['application/json']
    },
    {
        'prefix': 'info',
        'methods': ['GET'],
        'require_auth': False,
        'require_token': False,
        'handler': AdminHandler.info,
        'content-type':'application/json', # optional
        'accept':['application/json']
    },    
    { 
        'prefix':'*',
        'methods': ['OPTIONS'],
        'require_auth': False,
        'require_token': False,
        'handler': BaseHandler.return_ok,
        'content-type':'text/plain', # optional
        'accept':['application/json']
   }
]
