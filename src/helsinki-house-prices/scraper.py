import requests
import math
import json
import datetime
import os
import time
import argparse

BASE_URL = "https://asunnot.oikotie.fi/"
TOKEN_API_URL = BASE_URL + "user/get?format=json"
MAX_ADS_REQUEST = 48
REQUEST_DELAY = 2  # seconds to pause between successive API requests
DATA_DIR = "./data"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_adverts", type=int, required=True)
    args = parser.parse_args()
    return args


def format_filename_with_current_timestamp(prefix, file_ext):
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{prefix}-{formatted_time}{file_ext}"
    return filename


class OikotieScraper:
    """
    Class to scrape recent house sale adverts from the
    oikotie.fi API and write the retrieved data to file
    """

    def __init__(self):
        self.cuid = None
        self.token_timestamp = None
        self.token = None
        self._s = requests.Session()
        self.adverts = []

    def get_api_token(self):
        response = self._s.get(url=TOKEN_API_URL)
        if response.status_code == 200:
            response_dict = response.json().get("user")
            self.cuid = response_dict.get("cuid")
            self.token_timestamp = str(response_dict.get("time"))
            self.token = response_dict.get("token")
            self.headers = {
                "Ota-Cuid": self.cuid,
                "Ota-Loaded": self.token_timestamp,
                "Ota-Token": self.token,
                "Content-Type": "application/json",
            }

    def _api_url(
        self,
        limit,
        offset,
        card_type=100,  # homes for sale, TODO: work out other card types e.g. lomaasunnot
        locations="%5B%5B2,7,%22Uusimaa%22%5D%5D",  # Uusimaa defaults
        sort_by="published_sort_desc",
    ):
        return (
            BASE_URL + "api/search?"
            f"cardType={card_type}&"
            f"limit={limit}&"
            f"locations={locations}&"
            f"offset={offset}&"
            f"sortBy={sort_by}"
        )

    def _query_api(self, n_ads_to_request, offset=0):
        url = self._api_url(n_ads_to_request, offset)
        response = self._s.get(
            url,
            headers=self.headers,
        )
        return response.json()["cards"]

    def get_adverts(self, n_adverts):
        adverts_to_add = []

        if n_adverts <= MAX_ADS_REQUEST:
            query_result = self._query_api(n_adverts)
            adverts_to_add.extend(query_result)

        else:
            n_iterations = math.ceil(n_adverts / MAX_ADS_REQUEST)
            for m in range(n_iterations):
                offset = m * MAX_ADS_REQUEST
                query_result = self._query_api(n_adverts, offset)
                adverts_to_add.extend(query_result)
                time.sleep(REQUEST_DELAY)

        self.adverts.extend(adverts_to_add)

    def write_adverts(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.adverts, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    args = parse_args()
    n_adverts = args.n_adverts

    scraper = OikotieScraper()
    scraper.get_api_token()
    scraper.get_adverts(n_adverts)

    filename = format_filename_with_current_timestamp("data", ".json")
    dest_filepath = os.path.join(DATA_DIR, filename)

    scraper.write_adverts(dest_filepath)
