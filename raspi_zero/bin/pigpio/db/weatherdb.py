import datetime
from datetime import timedelta
import os
import sqlite3
from .sqlite3db import get_connection, close_connection
from .sqlite3conv import to_float, strdate2timestamp, DateFormatError

"""
Weather database CRUD functions, Finder class 
"""

# Weather database file path: (*)Environment on system service
# config file: /etc/default/udp-weather-mon
my_home = os.environ.get("HOME")
weather_db = os.environ.get("PATH_WEATHER_DB", my_home + "/db/weather.db")

# SQLite3 is 'RETURNING id' not available
INSERT_DEVICE = "INSERT INTO t_device(name) VALUES (?)"
ALL_DEVICES = "SELECT id, name FROM t_device ORDER BY id"
FIND_DEVICE = "SELECT id FROM t_device WHERE name = ?"

INSERT_WEATHER = """
INSERT INTO t_weather(did, measurement_time, temp_out, temp_in, humid, pressure) 
 VALUES (?, ?, ?, ?, ?, ?)  
"""
TRUNCATE_WEATHER = """
DELETE FROM t_weather;
DELETE FROM SQLITE_SEQUENCE WHERE name='t_weather';
VACUUM;
"""

# Global flag
flag_truncating = False
# t_device cache: {name: id}
cache_did_map = {}


def set_dbpath(dbpath):
    """
    Update Environ value
    :param dbpath: another path
    """
    global weather_db
    weather_db = dbpath


def get_did(conn, device_name, add_device=True, logger=None):
    """
    Get the device ID corresponding to the device name.
    1. if exist in cache, return from cache.
    2. if not exist in cache, if exist in t_device return did
    3. if not exist in t_device, insert into t_device and return did
    :param conn: Weather Weather database connection
    :param device_name: Device name
    :param add_device: flag into t_device, if True then insert into t_device and cache
    :param logger: application logger or None
    :return: did
    """
    try:
        did = cache_did_map[device_name]
    except KeyError:
        did = None

    if did is not None:
        return did

    did = find_device(conn, device_name, logger)
    if did is not None:
        cache_did_map[device_name] = did
        return did

    if not add_device:
        return None

    did = add_device(conn, device_name, logger)
    cache_did_map[device_name] = did
    return did


def all_devices(logger=None):
    """
    All record name-ID dict in t_device
    :param logger: application logger or None
    :return: Dict {device name: id}, if not record then blank dict
    """
    devices = {}
    conn = get_connection(weather_db, read_only=True, logger=logger)
    for device in conn.execute(ALL_DEVICES):
        devices[device[1]] = device[0] # {key: name, value: id}
    conn.close()
    return devices


def find_device(conn, device_name, logger=None):
    """
    Check device name in t_device.
    :param conn: Weather database connection
    :param device_name: Device name
    :param logger: application logger or None
    :return: if exists then Device ID else None
    """
    with conn:
        cur = conn.execute(FIND_DEVICE, (device_name,))
        rec = cur.fetchone()
    if logger is not None:
        logger.debug("{}: {}".format(device_name, rec))
    if rec is not None:
        rec = rec[0]
    return rec


def add_device(conn, device_name, logger=None):
    """
    Insert Device name to t_device and return inserted ID.
    :param conn: Weather database connection
    :param device_name: Device name
    :param logger: application logger or None
    :return: inserted ID
    """
    try:
        with conn:
            conn.execute(INSERT_DEVICE, (device_name,))
            if logger is not None:
                logger.debug("ADD_DEVICE")
            # SQLite3 not returning id
            # did = cur.fetchone()[0]
        did = find_device(conn, device_name, logger)
        if logger is not None:
            logger.debug("id: {}, name: {}".format(did, device_name))
    except sqlite3.Error as err:
        if logger is not None:
            logger.warning("error device_name:{}, {}".format(device_name, err))
        # return default id
        did = 0
    return did


def truncate(logger=None):
    """
    Truncate all record to t_weather.
    :param logger: application logger or None
    """
    global flag_truncating
    conn = get_connection(weather_db, logger=logger)
    try:
        flag_truncating = False
        if logger is not None:
            logger.info("Truncate start.")
        with conn:
            conn.executescript(TRUNCATE_WEATHER)
    finally:
        flag_truncating = False
        close_connection(conn)
        if logger is not None:
            logger.info("Truncate finished.")


def insert(device_name, temp_out, temp_in, humid, pressure, measurement_time=None, logger=None):
    """
    Insert weather sensor data to t_weather
    :param device_name: device name (required)
    :param temp_out: Outdoor Temperature (float or None)
    :param temp_in: Indoor Temperature (float or None)
    :param humid: humidity (float or None)
    :param pressure: pressure (float or None)
    :param measurement_time: unix epoch at local time
    :param logger: application logger or None
    """
    conn = get_connection(weather_db, logger=logger)
    did = get_did(conn, device_name, logger=logger)
    rec = (did,
           int(measurement_time),
           to_float(temp_out),
           to_float(temp_in),
           to_float(humid),
           to_float(pressure)
           )
    if logger is not None:
        logger.debug(rec)
    try:
        with conn:
            conn.execute(INSERT_WEATHER, rec)
    except sqlite3.Error as err:
        if logger is not None:
            logger.warning("rec: {}\nerror:{}".format(rec, err))
    finally:
        close_connection(conn, logger=logger)


class WeatherFinder:
    # Private constants
    _SELECT_DEVICE = "SELECT id, name FROM t_device order by id"
    _SELECT_WEATHER_COUNT = "SELECT count(*) FROM t_weather WHERE did=? "
    # datetime function is only SQLite3.
    _SELECT_WEATHER = """
    SELECT did, datetime(measurement_time, 'unixepoch', 'localtime'), temp_out, temp_in, humid, pressure
    FROM t_weather WHERE did=? 
    """
    # strtime function si only SQLite3: insert data local timestamp
    _FN_STRFTIME = "strftime('%s', ?, '-9 hours')"
    # if record count > GENERATOR_THRETHOLD then CSV Generator else CSV list
    _GENERATOR_WEATHER_THRESHOLD = 10000
    _GENERATOR_WEATHER_BATCHSIZE = 1000
    # CSV constants
    _FMT_WEATHER_CSV_FILENAME = "weather_{}.csv"
    _FMT_WEATHER_CSV_LINE = '{},"{}",{},{},{},{}'
    _FMT_DEVICE_CSV_LINE = '{},"{}"'
    # Public const
    DEVICE_CSV_FILENAME = "device.csv"
    """ CSV t_device Header """
    CSV_DEVICE_HEADER = '"id","name"\n'
    """ CSV t_weather Header """
    CSV_WEATHER_HEADER = '"did","measurement_time","temp_out","temp_in","humid","pressure"\n'

    def __init__(self, conn=None, logger=None):
        """
        Constructor
        if web app context conn is not None then self.closing_conn = False
        :param conn: Web application conn, if None then batch application
        :param logger: application logger or None
        """
        self.logger = logger
        self.conn = conn
        self.closing_conn = self.conn is None
        self.cursor = None
        self.csv_iter = None
        self._csv_name = None

    def close(self):
        """ Close cursor and if self.closing_conn then connection close """
        if self.cursor is not None:
            self.cursor.close()
        if self.closing_conn:
            if self.conn is not None:
                close_connection(self.conn, logger=None)

    @property
    def csv_filename(self):
        """ CSV filename ** [xxx] no '-'
          from_date and to_date is not None: 'weather_[device_name]_[from_date]-[to_date]_[today].csv'
          from_date is not None: 'weather_[device_name]_[from_date]_[today].csv'
          to_date is not None: 'weather_[device_name]_[to_date]_[today].csv'
          all None: 'weather_[device_name]_[all_[today].csv'
        """
        return self._FMT_WEATHER_CSV_FILENAME.format(self._csv_name)

    def _csv_iterator(self):
        """
        Generate Csv generator
          line: did, "YYYY-mm-DD HH:MM:SS(measurement_time)",temp_out,temp_in,humid,pressure
          (*) temp_out,temp_in,humid, pressure: if filedValue is None then empty string
        :return: Record generator
        """
        while True:
            batch_resords = self.cursor.fetchmany(self._GENERATOR_WEATHER_BATCHSIZE)
            if not batch_resords:
                break
            for rec in batch_resords:
                yield self._FMT_WEATHER_CSV_LINE.format(rec[0],
                                                        rec[1],
                                                        rec[2] if rec[2] is not None else '',
                                                        rec[3] if rec[3] is not None else '',
                                                        rec[4] if rec[4] is not None else '',
                                                        rec[5] if rec[5] is not None else '')

    def _csv_list(self):
        """
        Get CSV list
          line: did, "YYYY-mm-DD HH:MM:SS(measurement_time)",temp_out,temp_in,humid,pressure
          (*) temp_out,temp_in,humid, pressure: if filedValue is None then empty string
        :return: Record list, if no record then blank list
        """
        return [self._FMT_WEATHER_CSV_LINE.format(rec[0],
                                                  rec[1],
                                                  rec[2] if rec[2] is not None else '',
                                                  rec[3] if rec[3] is not None else '',
                                                  rec[4] if rec[4] is not None else '',
                                                  rec[5] if rec[5] is not None else '') for rec in self.cursor]

    @staticmethod
    def _check_datestring(date_from=None, date_to=None):
        """"
        Check date range.
        :param date_from: measurement_time from date, None or empty is valid
        :param date_to: measurement_time to date, None or empty is valid
        :param device_id: Device ID
        :return: from datetime(date_from is empty then None) , to datetime(date_to is empty then None)
        :exception: DateFormatError
        """
        dt_from, dt_to = None, None
        if date_from is not None and len(date_from) > 0:
            dt_from = strdate2timestamp(date_from)
            if dt_from is None:
                raise DateFormatError(date_from, filed_name="dateFrom")
        if date_to is not None and len(date_to) > 0:
            dt_to = strdate2timestamp(date_to)
            if dt_to is None:
                raise DateFormatError(date_to, filed_name="dateTo")

        if dt_to is not None:
            # measurement_time < dt_to + 1
            dt_to += timedelta(days=1)
        return dt_from, dt_to

    def _build_query(self, device_name, date_from=None, date_to=None, device_id=None):
        """
        Build queries and csv name
        :param device_name: Device name
        :param date_from: measurement_time from date
        :param date_to: measurement_time to date
        :param device_id: Device ID
        :return: count_sql, sql, criteria(sql parameters)
        """
        # Check input date
        dt_from, dt_to = self._check_datestring(date_from, date_to)

        name_suffix = device_name + "_"
        # Build query criteria, and csv filename
        if dt_from is not None and dt_to is not None:
            # measurement_time >= strftime('%s', dt_from) AND measurement_time < strftime('%s', dt_to)
            where = "AND (measurement_time >= " + self._FN_STRFTIME + \
                " AND measurement_time < " + self._FN_STRFTIME + ")"
            count_sql, sql = self._SELECT_WEATHER_COUNT + where, self._SELECT_WEATHER + where
            criteria = [device_id, dt_from, dt_to]
            name_suffix += date_from.replace("-", "") + \
                "-" + date_to.replace("-", "")
        elif dt_from is not None and dt_to is None:
            # measurement_time >= strftime('%s', dt_from)
            where = "AND measurement_time >= " + self._FN_STRFTIME
            count_sql, sql = self._SELECT_WEATHER_COUNT + where, self._SELECT_WEATHER + where
            criteria = [device_id, dt_from]
            name_suffix += date_from.replace("-", "")
        elif dt_from is None and dt_to is not None:
            # dmeasurement_time < strftime('%s', dt_to)
            where = "AND measurement_time < " + self._FN_STRFTIME
            count_sql, sql = self._SELECT_WEATHER_COUNT + where, self._SELECT_WEATHER + where
            criteria = [device_id, dt_to]
            name_suffix += date_to.replace("-", "")
        else:
            # All record
            count_sql, sql = self._SELECT_WEATHER_COUNT, self._SELECT_WEATHER
            criteria = [device_id]
            name_suffix += "all"
        # Build csv filename suffix
        date_part = datetime.date.today()
        self._csv_name = name_suffix + "_" + date_part.strftime("%Y%m%d")
        sql += " ORDER BY did, measurement_time"
        if self.logger is not None:
            self.logger.debug(sql)
        return count_sql, sql, criteria

    def get_count(self, device_name, date_from=None, date_to=None):
        """
        Check record count in the t_weather table corresponding to the specified time period of the device name.
        :param device_name: Device name
        :param date_from: measurement_time from date
        :param date_to: measurement_time to date
        :return: Record count, device name not exists then 0
         """
        if self.conn is None:
            self.conn = get_connection(weather_db, read_only=True, logger=self.logger)
        did = get_did(self.conn, device_name, add_device=False, logger=self.logger)
        if did is None:
            return 0

        count_sql, sql, criteria = self._build_query(device_name, date_from, date_to, device_id=did)
        try:
            # Check record count
            self.cursor = self.conn.cursor()
            self.cursor.execute(count_sql, criteria)
            # fetchone() return tuple (?,)
            row_count = self.cursor.fetchone()[0]
            if self.logger is not None:
                self.logger.info("Record count: {}".format(row_count))
        except sqlite3.Error as err:
            if self.logger is not None:
                self.logger.warning(
                    "criteria: {}\nerror:{}".format(criteria, err))
            raise err
        return row_count

    def find(self, device_name, date_from=None, date_to=None):
        """
        Get records in the t_weather table corresponding to the specified time period of the device name.
        :param device_name: Device name
        :param date_from: measurement_time from date
        :param date_to: measurement_time to date
        :return: Record iterable, device name not exists None
        """
        if self.conn is None:
            self.conn = get_connection(weather_db, read_only=True, logger=self.logger)
        did = get_did(self.conn, device_name, add_device=False, logger=self.logger)
        if did is None:
            return []

        count_sql, sql, criteria = self._build_query(device_name, date_from, date_to, device_id=did)
        try:
            # Check record count
            self.cursor = self.conn.cursor()
            self.cursor.execute(count_sql, criteria)
            # fetchone() return tuple (?,)
            row_count = self.cursor.fetchone()[0]
            if self.logger is not None:
                self.logger.info("Record count: {}".format(row_count))
            # Get record
            self.cursor.execute(sql, criteria)
            if row_count > self._GENERATOR_WEATHER_THRESHOLD:
                if self.logger is not None:
                    self.logger.info("Return CSV iterator")
                # make generator
                csv_iterable = self._csv_iterator()
            else:
                self.logger.info("Return CSV list")
                csv_iterable = self._csv_list()
        except sqlite3.Error as err:
            if self.logger is not None:
                self.logger.warning("criteria: {}\nerror:{}".format(criteria, err))
            raise err
        return csv_iterable

    def get_devices(self):
        if self.conn is None:
            self.conn = get_connection(weather_db, read_only=True, logger=self.logger)
        devices = []
        for device in self.conn.execute(self._SELECT_DEVICE):
            devices.append(self._FMT_DEVICE_CSV_LINE.format(device[0], device[1]))
        return devices
