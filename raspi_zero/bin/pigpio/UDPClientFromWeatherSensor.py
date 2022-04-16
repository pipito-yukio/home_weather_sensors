import argparse
import os
import pigpio
import signal
import socket
import threading
import time
from datetime import datetime
import db.weatherdb as wdb
import util.file_util as FU
from mail.gmail_sender import GMailer, GMAIL_USERNAME
from lib.ht16k33 import Brightness, BUS_NUM
from lib.led4digit7seg import LED4digit7Seg, LEDCommon, LEDNumber
from log import logsetting

"""
UDP packet monitor from ESP Weather sensors module
[UDP port] --port 2222
[GPIO Pin] --brightness-pin 17
Execute on system service
  sudo systemctl enable udp-weather-mon.service
  (user) pi
[connect]
  RaspberryPi: Raspi
  Bidirectional level conversion module for I2C bus: BusLvl
  LED matrix driver module: HT16k33
  [Raspi - HT16k33]
    VDD: 5V                           --|   
    VDD: 3v3    -> BusLvl.VREF1 -> BusLvl.VREF2 -> HT16k33.VDD
    GPIO2 (SDA) -> BusLvl.SDA1  -> BusLvl.SDA2  -> HT16k33.SDA
    GPIO3 (SCL) -> BusLvl.SCL1  -> BusLvl.SCL2  -> HT16k33.SCL
                                -> BusLvl.GND   -> HT16k33.GND
    GND                               --|
  [Tact button for brightness adjustment] Active HIGH (SW-ON: HIGH, SW-OFF: LOW) 
    GPIO17  <-> SW [1 (3)]
    VDD:3v3 <-> SW [2 (4)] 

  * If HT16k33 is not connected, only DB recording
"""

logger = logsetting.create_logger("service_weather")
base_dir = os.path.abspath(os.path.dirname(__file__))

# args option default
BRIGHTNESS_PIN = 17
WEATHER_UDP_PORT = 2222
I2C_ADDRESS = 0x70

BUFF_SIZE = 1024
# UDP packet receive timeout 12 minutes
RECV_TIMEOUT = 12. * 60
# FMT_MAIL_CONTENT = ""
FMT_MAIL_CONTENT = "[{}] Weather sensors UDP packet is delayed, so the battery may be dead."
MAIL_SUBJECT = "Weather sensor UDP packet is delayed."

# Global instance
pi = None
led_driver = None
udp_client = None
# Global flag
led_available = False
# Callback brightness switch
cb_brightness = None
curr_brightness = None
# Prevent chattering
prev_tick = 0
THRESHOLD_DIFF_TICK = 500000
# for delayed notificaton
mailer = None
delayed_mail_sent = False
# Melody IC pin
PIN_MELODY = 23
PLAY_TIME, POSE_TIME, PLAY_REPEAT = 30, 30, 3
melody_enable = False

# Dict for next brightness: HIGH > MID > LOW > DIM
NextBrightness = {Brightness.HIGH: Brightness.MID,
                  Brightness.MID: Brightness.LOW,
                  Brightness.LOW: Brightness.DIM,
                  Brightness.DIM: Brightness.HIGH}


def detect_signal(signum, frame):
    """
    Detect shutdown, and execute cleanup.
    :param signum: Signal number
    :param frame: frame
    :return:
    """
    logger.info("signum: {}, frame: {}".format(signum, frame))
    if signum == signal.SIGTERM:
        # signal shutdown
        cleanup()


def has_i2cdevice(slave_addr):
    """
    Check connection with i2c device.
    :param slave_addr: i2c device address
    :return: if available True, not False.
    """
    handle = pi.i2c_open(BUS_NUM, slave_addr)
    logger.debug("i2c_handle: {}".format(handle))
    is_available = False
    if handle >= 0:
        try:
            b = pi.i2c_read_byte(handle)
            logger.debug("read_byte: {}".format(b))
            is_available = True
        except Exception as e:
            logger.warning("{}".format(e))
        finally:
            pi.i2c_close(handle)
    else:
        logger.warning("I2C[{}] is not available.".format(slave_addr))
    return is_available


def change_brightness(gpio_pin, level, tick):
    """
    Change LED brightness.
    :param gpio_pin: Brightness GPIO pin number
    :param level: level
    :param tick: tick time.
    """
    global curr_brightness, prev_tick
    logger.debug("pin:{}, level:{}, tick: {}".format(gpio_pin, level, tick))
    if prev_tick != 0:
        tick_diff = pigpio.tickDiff(prev_tick, tick)
        logger.debug("tick_diff:{}".format(tick_diff))
        if tick_diff < THRESHOLD_DIFF_TICK:
            logger.debug("tick_diff:{} < {} return".format(tick_diff, THRESHOLD_DIFF_TICK))
            return

    prev_tick = tick
    next_brightness = NextBrightness[curr_brightness]
    if curr_brightness != next_brightness:
        curr_brightness = next_brightness
        led_driver.set_brightness(next_brightness)


def setup_gpio():
    """ Tact button for brightness adjustment. """
    global cb_brightness
    pi.set_mode(BRIGHTNESS_PIN, pigpio.INPUT)
    pi.write(BRIGHTNESS_PIN, pigpio.LOW)
    # Set internal pull-down register.
    pi.set_pull_up_down(BRIGHTNESS_PIN, pigpio.PUD_DOWN)
    # SW OFF(LOW) -> ON(HIGH)
    cb_brightness = pi.callback(BRIGHTNESS_PIN, pigpio.RISING_EDGE, change_brightness)


def play_melody(repeat=1):
    """
    Play the melody as an alert.
    :param repeat: repeat count
    """
    pi.set_mode(PIN_MELODY, pigpio.OUTPUT)
    pi.write(PIN_MELODY, pigpio.LOW)
    logger.info("Play melody start")
    for i in range(repeat):
        pi.write(PIN_MELODY, pigpio.HIGH)
        time.sleep(PLAY_TIME)
        pi.write(PIN_MELODY, pigpio.LOW)
        if repeat > 1 and i < repeat:
            time.sleep(POSE_TIME)
    logger.info("Play melody finished")


def send_mail(content):
    """
    Send notification to my gmail account.
    :param content: notification content
    """
    try:
        # Use application passwd (for 2 factor authenticate)
        mailer.sendmail(GMAIL_USERNAME, MAIL_SUBJECT, content)
        logger.info("Mail sent -> {}".format(content))
    except Exception as err:
        logger.warning(err)


def cleanup():
    """ GPIO cleanup, and UDP client close. """
    if cb_brightness is not None:
        cb_brightness.cancel()
    if led_driver is not None:
        led_driver.cleanup()
    if melody_enable:
        pi.write(PIN_MELODY, pigpio.LOW)
    pi.stop()
    udp_client.close()


def led_standby():
    """ Initialize all LEDs to '----' """
    led_driver.printOutOfRange(led_num=LEDNumber.N1)
    led_driver.printOutOfRange(led_num=LEDNumber.N2)
    led_driver.printOutOfRange(led_num=LEDNumber.N3)
    led_driver.printOutOfRange(led_num=LEDNumber.N4)


def isfloat(val):
    """
    Check float value.
    :param val: float value
    :return: True if float else False.
    """
    try:
        float(val)
    except ValueError:
        return False
    else:
        return True


def valid_temp(val):
    """
    Check temperature value.
    Numerial and valid range: -40.0 〜 50.0
    :param val: temperature value
    :return: True if valid temperature range else False.
    """
    if val < -40.0 or val > 50.0:
        return False
    return True


def valid_humid(val):
    """
    Check humidity value.
    Numerial and valid range: 0.0 〜 100.0 (%)
    :param val: humidity value
    :return: True if valid humidity range else False.
    """
    if val < 0.0 or val > 100.0:
        return False
    return True


def valid_pressure(val):
    """
    Check pressure value.
    Numerial and valid range: 900 〜 1100 hpa
    :param val: pressure value
    :return: True if valid pressure range else False.
    """
    if val < 900 or val > 1100:
        return False
    return True


def output_led(temp_out, temp_in, humid, pressure):
    """
    Output measurement values to LED.
    :param temp_out: Outer temperature value
    :param temp_in: Inner temperature value
    :param humid: Inner humidity value
    :param pressure: Inner pressure value
    """
    if not isfloat(temp_out):
        led_driver.printError(led_num=LEDNumber.N1)
    else:
        val = float(temp_out)
        if not valid_temp(val):
            led_driver.printOutOfRange(led_num=LEDNumber.N1)
        else:
            led_driver.printFloat(val, led_num=LEDNumber.N1)
    # LED2: Inner temperature
    if not isfloat(temp_in):
        led_driver.printError(led_num=LEDNumber.N2)
    else:
        val = float(temp_in)
        if not valid_temp(val):
            led_driver.printOutOfRange(led_num=LEDNumber.N2)
        else:
            led_driver.printFloat(val, led_num=LEDNumber.N2)
    # LED3: humidity
    if not isfloat(humid):
        led_driver.printError(led_num=LEDNumber.N3)
    else:
        val = float(humid)
        if not valid_humid(val):
            led_driver.printOutOfRange(led_num=LEDNumber.N3)
        else:
            led_driver.printFloat(val, led_num=LEDNumber.N3)
    # LED4: pressure(interger)
    if not isfloat(pressure):
        led_driver.printError(led_num=LEDNumber.N4)
    else:
        val = float(pressure)
        val = int(round(val, 0))
        if not valid_pressure(val):
            led_driver.printOutOfRange(led_num=LEDNumber.N4)
        else:
            led_driver.printInt(val, led_num=LEDNumber.N4)


def loop(client):
    """
    Infinit UDP packet monitor loop.
    :param client: UDP socket
    """
    global delayed_mail_sent
    server_ip = ''
    # Timeout setting
    client.settimeout(RECV_TIMEOUT)
    while True:
        try:
            data, addr = client.recvfrom(BUFF_SIZE)
        except socket.timeout:
            logger.warning("Socket timeout!")
            if delayed_mail_sent is not None:
                # Play melody as an alert.
                if melody_enable:
                    melody_thread = threading.Thread(target=play_melody, args=(PLAY_REPEAT, ))
                    logger.info("Melody Thread start.")
                    melody_thread.start()
                # Send Gmail.
                str_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                mail_content = FMT_MAIL_CONTENT.format(str_now)
                mail_thread = threading.Thread(target=send_mail, args=(mail_content, ))
                logger.info("Mail Thread start.")
                mail_thread.start()
                delayed_mail_sent = True
            continue

        if server_ip != addr:
            server_ip = addr
            logger.debug("server ip: {}".format(server_ip))

        # Reset flag.
        if delayed_mail_sent:
            delayed_mail_sent = False
        # From ESP output: device_name, temp_out, temp_in, humid, pressure
        line = data.decode("utf-8")
        logger.debug(line)
        record = line.split(",")
        # output 4Digit7SegLED
        if led_available:
            output_led(record[1], record[2], record[3], record[4])
        # Insert weather DB with local time
        # unix_tmstmp = int(time.time())   # time.time() is UTC unix epoch
        local_time = time.localtime()
        unix_tmstmp = time.mktime(local_time)
        wdb.insert(*record, measurement_time=unix_tmstmp, logger=logger)


if __name__ == '__main__':
    pi = pigpio.pi()
    if not pi.connected:
        logger.warning("pigpiod not stated!")
        exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--udp-port", type=int, default=WEATHER_UDP_PORT, help="Port from UDP Server[ESPxx].")
    parser.add_argument("--brightness-pin", type=int, default=BRIGHTNESS_PIN, help="Brightness change SW Pin.")
    args = parser.parse_args()
    logger.info(args)

    signal.signal(signal.SIGTERM, detect_signal)
    BRIGHTNESS_PIN = args.brightness_pin
    # Gmail sendor for Weather sensors UDP packet delay notification

    # Configuration
    app_conf = FU.read_json(os.path.join(base_dir, "conf", "conf_udpmon.json"))
    logger.info("app_conf: {}".format(app_conf))
    # UDP receive timeout.
    RECV_TIMEOUT = float(app_conf["monitor"]["recv_timeout_seconds"])
    conf_melody = app_conf["Melody"]
    melody_enable = conf_melody["enable"]
    PIN_MELODY = conf_melody["gpio_pin"]
    PLAY_TIME, POSE_TIME, PLAY_REPEAT = conf_melody["play_time"], conf_melody["pose_time"], conf_melody["play_repeat"]

    mailer = GMailer()
    hostname = socket.gethostname()
    # Receive broadcast
    broad_address = ("", args.udp_port)
    logger.info("{}: {}".format(hostname, broad_address))
    # UDP client
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_client.bind(broad_address)
    # HT16k33 connection check
    led_available = has_i2cdevice(I2C_ADDRESS)
    # LED for displaying measurement data
    if led_available:
        curr_brightness = Brightness.HIGH
        led_driver = LED4digit7Seg(pi, I2C_ADDRESS, common=LEDCommon.CATHODE, brightness=curr_brightness, logger=None)
        led_driver.clear_memory()
        led_standby()
        # GPIO pin setting for brightness adjustment
        setup_gpio()
    try:
        loop(udp_client)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
