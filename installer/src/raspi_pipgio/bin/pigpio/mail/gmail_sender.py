import os
import smtplib

# Referenced code
# https://www.bc-robotics.com/tutorials/sending-email-using-python-raspberry-pi/
# Sending An Email Using Python On The Raspberry Pi

GMAIL_USERNAME = os.environ.get("GMAIL_USER")


class GMailer:
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    _GMAIL_PASSWD = os.environ.get("GMAIL_PASSWD")

    def sendmail(self, recipient, subject, content, event=None):
        # Create Headers
        headers = ["From: " + GMAIL_USERNAME, "Subject: " + subject, "To: " + recipient,
                   "MIME-Version: 1.0", "Content-Type: text/plain"]
        headers = "\r\n".join(headers)
        # Connection to Gmail server
        session = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT)
        session.ehlo()
        session.starttls()
        session.ehlo()

        # Login
        session.login(GMAIL_USERNAME, self._GMAIL_PASSWD)

        # Send mail and Exit
        header_content = headers + "\r\n\r\n" + content
        header_content = header_content.encode("utf8")
        session.sendmail(GMAIL_USERNAME, recipient, header_content)
        session.quit()
        if event is not None:
            event.set()
