import json
import io
from flask import request, Response, url_for, render_template, redirect, session, abort, jsonify, g
from werkzeug.exceptions import BadRequest, InternalServerError
from weather_finder import app, app_logger
from weather_finder.db.weatherdb import weather_db, WeatherFinder
from weather_finder.db import sqlite3db
from weather_finder.db.sqlite3conv import DateFormatError

APP_ROOT = app.config["APPLICATION_ROOT"]
PATH_CHECK_REC_COUNT = "checkRecCount"
CHECK_REC_COUNT_URL = APP_ROOT + "/" + PATH_CHECK_REC_COUNT
CODE_BAD_REQUEST = 400

def get_dbconn():
    db = getattr(g, '_dbconn', None)
    if db is None:
        db = g._dbconn = sqlite3db.get_connection(weather_db, read_only=True, logger=app_logger)
    return db

@app.errorhandler(BadRequest)
def incorrect_access(ex):
    return "Bad request !", CODE_BAD_REQUEST


@app.teardown_appcontext
def close_conn(exception):
    db = getattr(g, '_dbconn', None)
    if db is not None:
        db.close()

@app.route(APP_ROOT)
def index():
    if "errors" in session:
        errmsgs = session["errors"]
    else:
        errmsgs = create_posterror_dict() 
    return render_template("findweather.html",
                           ip_host=app.config["SERVER_NAME"],
                           app_root_url=APP_ROOT,
                           path_check_rec_count=PATH_CHECK_REC_COUNT,
                           init_rec_count=app.config.get("MSG_INIT_REC_COUNT"),
                           msg_download_limit_count=app.config.get("MSG_DOWNLOAD_LIMIT_COUNT"),
                           errmsgs=errmsgs
                           )


@app.route(APP_ROOT + 'download_csv', methods=["POST"])
def download_csv():
    if request.form.get("downloadWeather"):
        # Download Weather CSV
        app_logger.debug("downloadWeather")
        device_name = request.form.get("deviceName")
        date_from = request.form.get("dateFrom")
        date_to = request.form.get("dateTo")
        chk_weather_headers = request.form.getlist("weatherHeader") # name="weatherHeader"
        chk_with_header = None
        if chk_weather_headers is not None:
            chk_with_header = True if "withHeader" in chk_weather_headers else None # value="withHeader"
        chk_with_device_csv = request.form.get("withDeviceCSV")
        app_logger.debug("deviceName: {}".format(device_name))
        app_logger.debug("dateFrom: {}".format(date_from))
        app_logger.debug("dateTo: {}".format(date_to))
        app_logger.debug("weatherHeader: {}".format(chk_weather_headers))
        app_logger.debug("withHeader: {}".format(chk_with_header))
        if device_name is None or len(device_name) == 0:
            # Redirect index page
            error_dict = create_posterror_dict()
            error_dict["msg_deviceName"] = app.config.get("INVALID_DEVICE_NAME")
            session["errors"] = error_dict
            return redirect(url_for('index'))

        wf = None
        try:
            conn = get_dbconn()
            return _download_weather(conn, device_name, date_from, date_to, with_header=chk_with_header)
        except DateFormatError as dfe:
            field_name = dfe.field_name
            dict_key = "msg_" + field_name
            error_dict = create_posterror_dict()
            error_dict[dict_key] = app.config.get("INVALID_DATEFORMAT")
            session["errors"] = error_dict
            return redirect(url_for('index'))
        except Exception as exp:
            app_logger.error(exp)
            return abort(501)
        finally:
            if wf is not None:
                wf.close()

    elif request.form.get("downloadDevice"):
        # Download Device CSV
        app_logger.info("downloadDevice")
        wf = None
        try:
            conn = get_dbconn()
            return _download_device(conn)
        except Exception as exp:
            app_logger.error(exp)
            return abort(501)
        finally:
            if wf is not None:
                wf.close()
    else:
        return abort(CODE_BAD_REQUEST)


@app.route(CHECK_REC_COUNT_URL, methods=["GET"])
def checkRecCount():
    # Request parameter
    device_name = request.args.get("deviceName")
    date_from = request.args.get("dateFrom")
    date_to = request.args.get("dateTo")
    app_logger.debug("query string: {}".format(request.query_string))
    app_logger.debug("deviceName: {}".format(device_name))
    app_logger.debug("dateFrom: {}".format(date_from))
    app_logger.debug("dateTo: {}".format(date_to))
    if device_name is None or len(device_name) == 0:
        err_dict = create_geterror_dict()
        err_dict["fieldName"] = "error_deviceName"
        err_dict["errorMessage"] = app.config.get("INVALID_DEVICE_NAME")
        app_logger.debug("error_dict: {}".format(err_dict))
        return create_error_response(err_dict)

    wf = None
    try:
        conn = get_dbconn()
        wf = WeatherFinder(conn=conn, logger=app_logger)
        rec_count = wf.get_count(device_name, date_from=date_from, date_to=date_to)
        return create_rec_count_response(rec_count)
    except DateFormatError as dfe:
        app_logger.warning(dfe)
        field_name = dfe.field_name
        err_dict = create_geterror_dict()
        err_dict["fieldName"] = "error_" + field_name
        err_dict["errorMessage"] = app.config.get("INVALID_DATEFORMAT")
        app_logger.debug("error_dict: {}".format(err_dict))
        return create_error_response(err_dict)
    except Exception as exp:
        app_logger.error(exp)
    finally:
        if wf is not None:
            wf.close()


def _download_weather(conn, device_name, date_from=None, date_to=None, with_header=False):
    wf = WeatherFinder(conn=conn, logger=app_logger)
    csv_lines = wf.find(device_name, date_from=date_from, date_to=date_to)
    # csv text to String buffer.
    output = io.StringIO()
    if with_header:
        output.write(WeatherFinder.CSV_WEATHER_HEADER)
    for line in csv_lines:
        output.write(line + "\n")
    # Rewind first position.
    output.seek(0)
    csvname = wf.csv_filename
    res = Response(output,
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=" + csvname})
    app_logger.debug(res)
    return res


def _download_device(conn):
    wf = WeatherFinder(conn=conn, logger=app_logger)
    csv_lines = wf.get_devices()
    output = io.StringIO()
    output.write(WeatherFinder.CSV_DEVICE_HEADER)
    for line in csv_lines:
        output.write(line + "\n")
    output.seek(0)
    csvname = WeatherFinder.DEVICE_CSV_FILENAME
    res = Response(output,
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=" + csvname})
    app_logger.debug(res)
    return res


def create_posterror_dict():
    """ Error messages dictionary for POST request """
    return {"msg_deviceName":"", "msg_dateFrom":"", "msg_dateTo":""}


def create_geterror_dict():
    """ Error messages dictionary for GET request """
    return {"filedName":"", "errorMessage":""}


def create_error_response(error_dict):
    resp_obj = {"status": "error"}
    resp_obj["data"] = {
        "fieldName": error_dict["fieldName"],
        "errorMessage": error_dict["errorMessage"],
    }
    return jsonify(resp_obj)


def create_rec_count_response(rec_count):
    resp_obj = {"status": "success"}
    resp_obj["data"] = {
        "recCount": rec_count
    }
    return jsonify(resp_obj)
