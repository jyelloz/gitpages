#!/usr/bin/env python

import logging
from flask.ext.script import Manager
from gitpages.web.application import create


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    manager = Manager(create)
    manager.run()
