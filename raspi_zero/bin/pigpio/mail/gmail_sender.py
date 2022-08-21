import logging
import os
import smtplib

# Referenced code
# https://www.bc-robotics.com/tutorials/sending-email-using-python-raspberry-pi/
# Sending An Email Using Python On The Raspberry Pi


class GMailer:
    _SMTP_SERVER = "smtp.gmail.com"
    _SMTP_PORT = 587
    _GMAIL_PASSWD = os.environ.get("GMAIL_PASSWD")
    GMAIL_USER = os.environ.get("GMAIL_USER")

    def __init__(self, logger=None):
        self.logger = logger
        if self.logger is not None:
            self.logger_debug = (self.logger.getEffectiveLevel() <= logging.DEBUG)
        else:
            self.logger_debug = False

    def sendmail(self, subject, content, recipients, event=None):
        # Create Headers:
        if recipients is not None:
            if len(recipients) > 0:
                # https://docs.python.org/ja/3/library/smtplib.html: SMTP 使用例
                to_addrs = ",".join(recipients)
            else:
                to_addrs = self.GMAIL_USER
        else:
            to_addrs = self.GMAIL_USER
        headers = ["From: " + self.GMAIL_USER, "Subject: " + subject, "To: " + to_addrs,
                   "MIME-Version: 1.0", "Content-Type: text/plain"]
        headers = "\r\n".join(headers)
        if self.logger_debug:
            self.logger.debug("headers: {}".format(headers))
        # Connection to Gmail server
        session = smtplib.SMTP(self._SMTP_SERVER, self._SMTP_PORT)
        session.ehlo()
        session.starttls()
        session.ehlo()

        # Login
        session.login(self.GMAIL_USER, self._GMAIL_PASSWD)

        # Send mail and Exit
        header_content = headers + "\r\n\r\n" + content
        header_content = header_content.encode("utf8")
        if self.logger_debug:
            self.logger.debug("header_content: {}".format(header_content))
        session.sendmail(self.GMAIL_USER, to_addrs, header_content)
        session.quit()
        if event is not None:
            event.set()
