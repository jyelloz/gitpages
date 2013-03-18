#!/usr/bin/env python

from flask.ext.script import Manager

from gitpages.web.application import create

manager = Manager(create)

if __name__ == '__main__':
    manager.run()
