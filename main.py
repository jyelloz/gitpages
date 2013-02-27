from flask import Flask
from flask_failsafe import failsafe

from gitpages.web.application import create

if __name__ == '__main__':
    create().run(debug=True, host='0.0.0.0')
