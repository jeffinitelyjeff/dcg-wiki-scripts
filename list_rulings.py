import argparse
import datetime
import logging
import os
import pprint
import sys
import time

import bs4
import requests
import wikitextparser as wtp

import set_data


FILENAME = os.path.basename(__file__)
RULING_WIKI_URL = "https://digimoncardgame.fandom.com/wiki/Card_Rulings:{}?action=edit"
RULING_WIKI_LINK_URL = "https://digimoncardgame.fandom.com/wiki/Card_Rulings:{}"

run_timestamp = datetime.datetime.now()

pp = pprint.PrettyPrinter(indent=2)

parser = argparse.ArgumentParser()
parser.add_argument('--log', type=str)
parser.add_argument('--delay-ms', type=int, default=0)
input_group = parser.add_mutually_exclusive_group(required=True)
input_group.add_argument('--scrape-set', type=str)
input_group.add_argument('--scrape-all', action='store_true')
condition_group = parser.add_mutually_exclusive_group(required=True)
condition_group.add_argument('--multiple-sources', action='store_true')

args = parser.parse_args()

log_dir = os.path.abspath(args.log or ".")
log_name = f"{FILENAME}-{run_timestamp:%Y%m%d}.log"
log_path = os.path.join(log_dir, log_name)

logging.basicConfig(format='[%(asctime)s] %(message)s',
                    filename=log_path, level=logging.DEBUG)
logger = logging.getLogger()


def log(msg, print_dest="stderr"):
  logger.info(msg)

  if print_dest == "stderr":
    print(msg, file=sys.stderr)

  if print_dest == "stdout":
    print(msg)


def card_num(set_id, idx):
  format_str = "{}-{:03d}" if set_id in set_data.BT_COUNTS else "{}-{:02d}"
  return format_str.format(set_id, idx)


def scrape_wikitext(data_url):
  log(f"Scraping [{data_url}]", print_dest=None)

  r = requests.get(data_url)

  try:
    soup = bs4.BeautifulSoup(r.text, "lxml")
    data = soup.find(id="wpTextbox1").string
  except AttributeError:
    return None

  return data


def get_rulings_wt(card_num):
  data_url = RULING_WIKI_URL.format(card_num)
  raw_wt = scrape_wikitext(data_url)

  if raw_wt:
    return wtp.parse(raw_wt)
  else:
    log(f"No rulings for {card_num}", print_dest=None)


def test_card(card_num):
  wt = get_rulings_wt(card_num)
  if not wt:
    return False

  if args.multiple_sources:
    return wt.get_lists() and len(wt.get_lists()[0].items) > 1
  else:
    # TODO
    return False


def wait():
  if args.delay_ms > 0:
    time.sleep(args.delay_ms / 1000)


def test_set(set_id):
  card_count = set_data.BT_COUNTS.get(
    set_id) or set_data.ST_COUNTS.get(set_id) or 0

  hit_cards = []

  for i in range(1, card_count + 1):
    c_num = card_num(set_id, i)
    if test_card(c_num):
      hit_cards.append(c_num)

    wait()

  log(f"Found {len(hit_cards)} hits in {set_id}")

  return hit_cards


def main():
  log(f"\n\n\n\n{'=' * 60}\n", print_dest=None)
  log(f"Running {FILENAME}", print_dest=None)

  log(f"args: {args}", print_dest=None)

  hit_cards = []

  if args.scrape_set:
    set_id = args.scrape_set
    hit_cards.extend(test_set(set_id))

  if args.scrape_all:
    ordered_sets = []
    ordered_sets.extend(s for s in reversed(set_data.BT_COUNTS))
    ordered_sets.extend(s for s in reversed(set_data.ST_COUNTS))
    for set_id in ordered_sets:
      hit_cards.extend(test_set(set_id))

  list_text = "\n".join(
    [f"- {c}: {RULING_WIKI_LINK_URL.format(c)}" for c in hit_cards])

  if args.multiple_sources:
    title_text = "Rulings Pages With Multiple Non-reftag Sources:"

  log(f"{title_text}:\n{list_text}")


if __name__ == "__main__":
  main()
