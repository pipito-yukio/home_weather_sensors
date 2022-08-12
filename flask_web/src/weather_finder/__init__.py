import os
import uuid

from flask import Flask

from weather_finder.log import logsetting

app = Flask(__name__)
app_logger = logsetting.get_logger('app_main')
app.config.from_object('weather_finder.config')
app.config.from_pyfile(os.path.join(".", "messages/messages.conf"), silent=False)
app.secret_key = uuid.uuid4().bytes
# Strip newline
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True

# サーバホストとセッションのドメインが一致しないとブラウザにセッションIDが設定されない
IP_HOST = os.environ.get('IP_HOST', None)
has_prod = os.environ.get("FLASK_ENV") == "production"
if has_prod:
    # Production mode
    SERVER_HOST = IP_HOST + ":8080"
else:
    SERVER_HOST = IP_HOST + ":5000"

app.config["SERVER_NAME"] = SERVER_HOST
app.config["APPLICATION_ROOT"] = "/weather_finder"
# use flask jsonify with japanese message
app.config["JSON_AS_ASCII"] = False
app_logger.debug("app.secret_key: {}".format(app.secret_key))
app_logger.debug("{}".format(app.config))

# Application main program
from weather_finder.views import app_main
