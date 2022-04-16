import os
import uuid
from flask import Flask
from weather_finder.log import logsetting
from weather_finder.config import config_dict

app = Flask(__name__)
app_logger = logsetting.get_logger('app_main')
app.config.from_object('weather_finder.config')
app.config.from_pyfile(os.path.join(".", "messages/messages.conf"), silent=False)
app.secret_key = uuid.uuid4().bytes

# サーバホストとセッションのドメインが一致しないとブラウザにセッションIDが設定されない
IP_HOST = os.environ.get('IP_HOST', None)
has_prod = os.environ.get("ENV") == "production"
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
