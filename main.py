#!/usr/bin/env python

import logging

from gitpages.web.application import create

logging.basicConfig(level=logging.DEBUG)
application = create()

if __name__ == '__main__':
    application.run(debug=True, host='127.0.0.1')
