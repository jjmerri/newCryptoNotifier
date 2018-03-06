#!/usr/bin/env python3.6

# =============================================================================
# IMPORTS
# =============================================================================

from threading import Thread
import os
import sys
import configparser
import requests
import time
import logging

# =============================================================================
# GLOBALS
# =============================================================================

# Reads the config file
config = configparser.ConfigParser()
config.read("new_crypto_checker.cfg")

discord_webhooks = []
discord_webhooks.append(config.get("CRYPTO_CHECKER", "discord_webhook"))

check_urls = []
check_urls.append("https://api.coinbase.com/v2/prices/{ticker}-USD/historic?period=month")
check_urls.append("https://api.coinbase.com/v2/prices/{ticker}-USD/buy")
check_urls.append("https://api.coinbase.com/v2/exchange-rates?currency={ticker}")

check_urls.append("https://api.gdax.com/products/{ticker}-USD")
check_urls.append("https://api.gdax.com/products/{ticker}-BTC")
check_urls.append("https://api.gdax.com/currencies/{ticker}")

ENVIRONMENT = config.get("CRYPTO_CHECKER", "environment")

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('crypto_checker')
logger.setLevel(logging.INFO)

supported_tickers = ["XRP", "ADA", "BCC", "XEM", "XLM", "MIOTA", "DASH", "NEO", "TRX", "EOS", "XMR"]
discovered_cryptos = []
RUNNING_FILE = "crypto_checker.running"


def check_new_cryptos():
    price_threads = [];

    for supported_ticker in supported_tickers:
        for check_url in check_urls:
            # Thread api calls because they take a while in succession
            t = Thread(target=check_new_crypto, args=[supported_ticker, check_url.format(ticker = supported_ticker)])
            price_threads.append(t)
            t.start()

    # Wait for all checks
    for price_thread in price_threads:
        price_thread.join()

def check_new_crypto(ticker, check_url):
    """
    Checks to see if the ticket is available at the check_url
    :param ticker: the ticker of the crypto to check
    :param check_url: the url to check to see if ticker is supported
    """
    r = requests.get(check_url)
    response = r.json()

    if r.status_code == 200 and ticker not in discovered_cryptos:
        logger.info("New crypto supported! {ticker} is available at {check_url}".format(ticker = ticker, check_url = check_url))
        send_new_crypto_notifications(ticker, check_url)
        discovered_cryptos.append(ticker)


def send_new_crypto_notifications(ticker, check_url):
    for discord_webhook in discord_webhooks:
        payload = {"content": "@everyone '{ticker} found at {check_url}'".format(ticker = ticker, check_url = check_url),
                   "username": "Coin Poller"}
        headers = {'content-type': 'application/json'}

        response = requests.post(discord_webhook, json = payload, headers = headers)

def create_running():
    running_file = open(RUNNING_FILE, "w")
    running_file.write(str(os.getpid()))
    running_file.close()

# =============================================================================
# MAIN
# =============================================================================

def main():
    logger.info("start")
    start_process = False

    if ENVIRONMENT == "DEV" and os.path.isfile(RUNNING_FILE):
        os.remove(RUNNING_FILE)
        logger.info("running file removed")

    if not os.path.isfile(RUNNING_FILE):
        create_running()
        start_process = True
    else:
        start_process = False
        logger.error("Reply already running! Will not start.")

    while start_process and os.path.isfile(RUNNING_FILE):
        try:
            logger.info("Start Main Loop")

            check_new_cryptos()

            logger.info("End Main Loop")
            time.sleep(600)
        except Exception as err:
            logger.exception("Unknown Exception in main loop")

            time.sleep(600)

    sys.exit()

# =============================================================================
# RUNNER
# =============================================================================
if __name__ == '__main__':
    main()
