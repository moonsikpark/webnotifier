# WebNotifier

## Why

To get updates of websites via Telegram, with no hassle(tm)

## How

1. Fork this repo.

    git clone https://github.com/moonsikpark/webnotifier.git

2. Edit `main.py` for your needs. Subclass `BaseWebNotifier` and fill in the blanks. Override `collect_data()` with your methods for crunching HTML data. Add your class to `main()`

3. Set environment variable `WEBNOTIFIER_LOG_FILE` to your desired log file location and  `WEBNOTIFIER_LOGLEVEL` for the desired log level.

4. Voilà!

WebNotifier provides a base class `BaseWebNotifier`. You need to subclass it to create your own bot.

In main.py:

    from modules.webnotifier import BaseWebNotifier
    from lxml import html # Use the parser of your needs. Beautifulsoup works well.


    class MyNotifier(BaseWebNotifier):
        notifier_name = "mynotifier"    # This should be unique.
        telegram_bot_name = "name"      # Name when you've created a bot with BotFather.
        telegram_bot_token = "token"    # Token provided when you've created a bot with BotFather.
        telegram_dest_channel = "@chan" # ID of the channel your bot will send alert to.
        telegram_delay_second = 1       # Delay while sending alerts
        message_format = "title: {title}\n url: {url}" # Message format, must include {title} and {url}
        db_file = "webnotifier.db"      # Database file location
        base_url = "http://example.com" # Source URL for your data.

        def collect_data(self, collected_html):
            # collected_html contains base_url's html.
            for item in data_processed_from_html:
                url = "<URL to send alert>"
                title = "<Title of the URL>"
                self.insert_data(url, title)  # call self.insert_data() for all data you want to notify

    def main():
        MyNotifier() # Don't forget to add your class here!-

## Example
                
    from modules.webnotifier import BaseWebNotifier
    from lxml import html


    class MyNotifier(BaseWebNotifier): # You can set global vars in a class and subclass that. DRY!
        telegram_bot_name = "<name>"
        telegram_bot_token = "<token>"
        telegram_dest_channel = "@<chan>"
        telegram_delay_second = 1


    class PpomppuNationalNotifier(MyNotifier): # Subclass the class with global vars.
        notifier_name = "ppomppunational"
        message_format = '<b>[국뽐]</b> {title}\n{url}'
        base_url = "http://m.ppomppu.co.kr/new/bbs_list.php?id=ppomppu"

        def collect_data(self, collected_html):
            for item in html.fromstring(collected_html).xpath(
                "//ul[@class='bbsList']/li/a[@class='list_b_01']"
            ):
                url = "http://m.ppomppu.co.kr/new/" + item.attrib["href"]
                title = item.find_class("title")[0].text.lstrip()
                self.insert_data(url, title)

    class PpomppuForeignNotifier(MyNotifier):
        notifier_name = "ppomppuforeign"
        message_format = '<b>[해뽐]</b> {title}\n{url}'
        base_url = "http://m.ppomppu.co.kr/new/bbs_list.php?id=ppomppu4"
        

        def collect_data(self, collected_html):
            for item in html.fromstring(collected_html).xpath(
                "//ul[@class='bbsList']/li/a[@class='list_b_01']"
            ):
                url = "http://m.ppomppu.co.kr/new/" + item.attrib["href"]
                title = item.find_class("title")[0].text.lstrip()
                self.insert_data(url, title)

    class ClienNotifier(MyNotifier):
        notifier_name = "clien"
        message_format = '<b>[알구게]</b> {title}\n{url}'
        base_url = "https://m.clien.net/service/board/jirum"
        

        def collect_data(self, collected_html):
            for item in html.fromstring(collected_html).xpath(
                "//div[@class='content_list']/div[@data-role='list-row']/div[@class='list_title']/a"
            ):
                url = "https://m.clien.net" + item.attrib["href"].split("?")[0]
                title = item.findall("span")[0].text
                self.insert_data(url, title)


    def main():
        PpomppuNationalNotifier()
        PpomppuForeignNotifier()
        ClienNotifier()

    if __name__ == "__main__":
        main()
