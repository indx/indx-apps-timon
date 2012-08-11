#!/bin/bash

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
#    Foobar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with WebBox.  If not, see <http://www.gnu.org/licenses/>.

export DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

export PATH="$DIR/../4store:$PATH"

export ME=`whoami`
export KBNAME="webbox_$ME"

#./new_4store_kb.sh
rm -r "/var/lib/4store/$KBNAME"
rm ~/.webbox/journal.sqlite
rm ~/.webbox/subscriptions.sqlite
rm -r ~/.webbox/files/*

