#!/usr/bin/env python

import logging

from gitpages.web.application import create

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    create().run(debug=True, host='127.0.0.1')
