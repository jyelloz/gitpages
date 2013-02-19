#!/usr/bin/env python

from flask.ext.script import Manager

from web.ui import create

manager = Manager(create())

if __name__ == "__main__":
    manager.run()
