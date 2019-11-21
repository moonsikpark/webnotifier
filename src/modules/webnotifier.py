"""
Copyright (c) 2019, Moonsik Park
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import requests
import sqlite3
import os
import sys
from lxml import html
import logging
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS {notifier_name} (
    url TEXT PRIMARY KEY UNIQUE,
    title TEXT NOT NULL,
    alerted INTEGER NOT NULL DEFAULT 0
);
"""

LOG_FILE = os.environ.get("WEBNOTIFIER_LOG_FILE", "webnotifier.log")
LOG_LEVEL = os.environ.get("WEBNOTIFIER_LOGLEVEL", "ERROR").upper()

logger = logging.getLogger("webnotifier")
handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s  [%(filename)s:%(lineno)s] - %(message)s"
)
logger.setLevel(LOG_LEVEL)
handler.setFormatter(formatter)
logger.addHandler(handler)


class BaseWebNotifier:
    notifier_name = None
    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1"
    telegram_bot_name = None
    telegram_bot_token = None
    telegram_dest_channel = None
    message_format = 'title: "{title}"\nurl: "{url}"'
    telegram_delay_second = 1
    db_file = "webnotifier.db"
    base_url = None

    def __init__(self):
        logger.info(f"Started notifier '{self.notifier_name}'.")
        self.session = requests.session()
        self.telegram_api_endpoint = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        self.db_conn = sqlite3.connect(self.db_file, isolation_level="IMMEDIATE")
        self.db_cur = self.db_conn.cursor()
        self.db_cur.execute(SCHEMA.format(notifier_name=self.notifier_name))

        self.collected_html = self.session.get(
            self.base_url, headers={"User-Agent": self.user_agent}
        ).text

        self.collect_data(self.collected_html)
        self.send_alert()

        self.db_conn.close()
        logger.info(f"Ended notifier {self.notifier_name}.")

    def insert_data(self, url, title):
        self.db_cur.execute(
            f"INSERT OR IGNORE INTO {self.notifier_name} (url, title) values(:url, :title);",
            {"url": url, "title": title},
        )
        self.db_conn.commit()

    def verify_alerted_item(self, url, retval):
        self.db_cur.execute(
            f"UPDATE {self.notifier_name} SET alerted = :retval WHERE url = :url;",
            {"retval": retval, "url": url},
        )
        self.db_conn.commit()

    def get_unnotified_items(self, retval):
        self.db_cur.execute(
            f"SELECT url, title FROM {self.notifier_name} WHERE alerted = :retval;",
            {"retval": retval},
        )

        return self.db_cur.fetchall()

    def collect_data(self, collected_html):
        pass

    def send_alert(self):
        data = self.get_unnotified_items(0)
        logger.debug(f"Got {len(data)} item to send alert.")
        for item in data:
            url = item[0]
            url_escaped = item[0].replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
            title = item[1]
            title_escaped = item[1].replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
            text = self.message_format.format(url=url_escaped, title=title_escaped)

            self.send_telegram_alert(url, text)

            time.sleep(self.telegram_delay_second)

        failed_data = self.get_unnotified_items(-1)
        logger.debug(f"Got {len(failed_data)} once failed item to send alert.")
        for item in failed_data:
            url = item[0]
            title = item[1]
            text = self.message_format.format(url=url, title=title, retry=True)

            self.send_telegram_alert(url, text)

            time.sleep(self.telegram_delay_second)

    def send_telegram_alert(self, url, text, retry=False):
        logger.debug(f"Sending telegram alert of '{url}'.")
        res = self.session.get(
            self.telegram_api_endpoint,
            data={
                "chat_id": self.telegram_dest_channel,
                "text": text,
                "parse_mode": "html",
            },
        )
        if res.status_code == requests.codes.ok:
            logger.debug(f"Successfully sent Telegram alert of '{url}'.")
            self.verify_alerted_item(url, 1)
        elif not retry:
            logger.error(
                f"Failed to send Telegram alert of '{url}'. Response: {res.text}"
            )
            self.verify_alerted_item(url, -1)
        else:
            logger.error(
                f"Aborting. Failed twice to send Telegram alert of '{url}'. Response: {res.text}"
            )
            self.verify_alerted_item(url, -2)
