import argparse
import logging
import os
import pigpio
import signal
import socket
import subprocess
import threading
import time
from datetime import datetime
from urllib.parse import quote_plus
import db.weatherdb as wdb
import util.file_util as FU
from mail.gmail_sender import GMailer
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
FMT_MAIL_CONTENT = "[{}] Weather sensors UDP packet is delayed, so the battery may be dead."
MAIL_SUBJECT = "Weather sensor UDP packet is delayed."

# Global instance
pi = None
led_driver = None
udp_client = None
# Global flag
led_available = False
has_led_i2c_error =False
# Callback brightness switch
cb_brightness = None
curr_brightness = None
# Prevent chattering
prev_tick = 0
THRESHOLD_DIFF_TICK = 500000
# for delayed notificaton
mailer = None
delayed_mail_sent = False
isLogLevelDebug = False
# Subprocess configuration
conf_subprocess = None

# Dict for next brightness: HIGH > MID > LOW > DIM
NextBrightness = {Brightness.HIGH: Brightness.MID,
                  Brightness.MID: Brightness.LOW,
                  Brightness.LOW: Brightness.DIM,
                  Brightness.DIM: Brightness.HIGH}


def mail_config():
    """
    Mail configuration
    :return: [is Sendmail: True or False], [subject], [content-template], [recipients]
    """
    conf_path = os.path.join(base_dir, "conf", "conf_sendmail.json")
    is_sendmail=True
    mail_conf = None
    if os.path.exists(conf_path):
        mail_conf = FU.read_json(conf_path)
        if isLogLevelDebug:
            logger.debug(mail_conf)
        is_sendmail = mail_conf["enable"]

    if is_sendmail:
        if mail_conf is not None:
            # Custom configuration
            if len(mail_conf["subject"]) > 0:
                subject = mail_conf["subject"]
            else:
                subject = MAIL_SUBJECT
            content_template = mail_conf["content-template"]
            recipients = mail_conf["recipients"]
        else:
            # Default configuration
            subject = MAIL_SUBJECT
            content_template = FMT_MAIL_CONTENT
            recipients = None

    if isLogLevelDebug:
        logger.debug("is_sendmail: {}\nsubject: {}\ncontent-template: {}\nrecipients: {}".format(
            is_sendmail, subject, content_template, recipients
        ))
    return is_sendmail, subject, content_template, recipients


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
        # Current process terminate
        exit(-1 if has_led_i2c_error else 0)


def has_i2cdevice(slave_addr):
    """
    Check connection with i2c device.
    :param slave_addr: i2c device address
    :return: if available True, not False.
    """
    handle = pi.i2c_open(BUS_NUM, slave_addr)
    if isLogLevelDebug:
        logger.debug("i2c_handle: {}".format(handle))
    is_available = False
    if handle >= 0:
        try:
            b = pi.i2c_read_byte(handle)
            if isLogLevelDebug:
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
    if isLogLevelDebug:
        logger.debug("pin:{}, level:{}, tick: {}".format(gpio_pin, level, tick))
    if prev_tick != 0:
        tick_diff = pigpio.tickDiff(prev_tick, tick)
        if isLogLevelDebug:
            logger.debug("tick_diff:{}".format(tick_diff))
        if tick_diff < THRESHOLD_DIFF_TICK:
            if isLogLevelDebug:
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


def subproc_displaymessage(delayed_datetime):
    """
    Display delayed message on Subprocess Display message script.
    :param delayed_datetime: happen delayed datetime
    """
    msg = conf_subprocess["displayMessage"]["msgfmt"].format(delayed_datetime)
    encoded = quote_plus(msg)
    if isLogLevelDebug:
        logger.debug("encoded: {}".format(encoded))
    script = conf_subprocess["displayMessage"]["script"]
    exec_status = subprocess.run([script, "--encoded-message", encoded])
    logger.info("Subprocess DisplayMessage terminated: {}".format(exec_status))


def subproc_playmelody():
    """
    Play the melody as an alert on Subprocess Play melody script.
    """
    script = conf_subprocess["playMelody"]["script"]
    exec_status = subprocess.run([script])
    logger.info("Subprocess PlayMelody terminated: {}".format(exec_status))


def send_mail(subject, content, recipients):
    """
    Send notification to recipients
    :param subject:
    :param content:
    :param recipients:
    """
    try:
        # Use application passwd (for 2 factor authenticate)
        mailer.sendmail(subject, content, recipients)
        logger.info("Mail sent to -> {}".format(recipients))
    except Exception as err:
        logger.warning(err)


def cleanup():
    """ GPIO cleanup, and UDP client close. """
    if cb_brightness is not None:
        cb_brightness.cancel()
    if led_driver is not None:
        # Check i2c connect.
        if not has_led_i2c_error:
            led_driver.cleanup()
    pi.stop()
    udp_client.close()


def led_standby():
    """ Initialize all LEDs to '----' """
    led_driver.printOutOfRange(led_num=LEDNumber.N1)
    led_driver.printOutOfRange(led_num=LEDNumber.N2)
    led_driver.printOutOfRange(led_num=LEDNumber.N3)
    led_driver.printOutOfRange(led_num=LEDNumber.N4)


def led_show_i2cerro():
    """ Raise exception to 'EEEE' """
    led_driver.printError(led_num=LEDNumber.N1)
    led_driver.printError(led_num=LEDNumber.N2)
    led_driver.printError(led_num=LEDNumber.N3)
    led_driver.printError(led_num=LEDNumber.N4)


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
    global delayed_mail_sent, has_led_i2c_error
    # Rest I2C Error flag.
    has_led_i2c_error = False
    server_ip = ''
    # Timeout setting
    client.settimeout(RECV_TIMEOUT)
    while True:
        try:
            data, addr = client.recvfrom(BUFF_SIZE)
        except socket.timeout:
            logger.warning("Socket timeout!")
            now = datetime.now()
            if delayed_mail_sent is not None:
                if conf_subprocess["playMelody"]["enable"]:
                    melody_thread = threading.Thread(target=subproc_playmelody)
                    logger.info("Subprocess PlayMelody thread start.")
                    melody_thread.start()
                if conf_subprocess["displayMessage"]["enable"]:
                    # Generate short message for Raspberry Pi zero (not scroll)
                    time_now = now.strftime('%H:%M')
                    display_thread = threading.Thread(target=subproc_displaymessage, args=(time_now,))
                    logger.info("Subprocess DisplayMessage thread start.")
                    display_thread.start()

                # Send Gmail: Read every occurence
                (is_sendmail, subject, content_template, recipients) = mail_config()
                if is_sendmail:
                    delayed_now = now.strftime('%Y-%m-%d %H:%M')
                    content = content_template.format(delayed_now)
                    mail_thread = threading.Thread(target=send_mail, args=(subject, content, recipients,))
                    logger.info("Mail Thread start.")
                    mail_thread.start()
                delayed_mail_sent = True
            continue

        if server_ip != addr:
            server_ip = addr
            logger.info("server ip: {}".format(server_ip))

        # Reset flag.
        if delayed_mail_sent:
            delayed_mail_sent = False
        # From ESP output: device_name, temp_out, temp_in, humid, pressure
        line = data.decode("utf-8")
        if isLogLevelDebug:
            logger.debug(line)
        record = line.split(",")
        # output 4Digit7SegLED
        if led_available:
            try:
                output_led(record[1], record[2], record[3], record[4])
            except Exception as i2c_err:
                has_led_i2c_error = True
                # Show I2C Error.
                led_show_i2cerro()
                raise i2c_err

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

    isLogLevelDebug = logger.getEffectiveLevel() <= logging.DEBUG
    parser = argparse.ArgumentParser()
    parser.add_argument("--udp-port", type=int, default=WEATHER_UDP_PORT, help="Port from UDP Server[ESPxx].")
    parser.add_argument("--brightness-pin", type=int, default=BRIGHTNESS_PIN, help="Brightness change SW Pin.")
    args = parser.parse_args()
    logger.info(args)

    signal.signal(signal.SIGTERM, detect_signal)
    BRIGHTNESS_PIN = args.brightness_pin

    # Configuration
    app_conf = FU.read_json(os.path.join(base_dir, "conf", "conf_udpmon.json"))
    if isLogLevelDebug:
        logger.debug(app_conf)
    # UDP receive timeout.
    RECV_TIMEOUT = float(app_conf["monitor"]["recv_timeout_seconds"])
    # Subprocess configration
    conf_subprocess = app_conf["subprocess"]

    # GMailer
    mailer = GMailer(logger=logger)

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
    except Exception as err:
        logger.error(err)
    finally:
        cleanup()
