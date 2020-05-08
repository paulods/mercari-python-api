from time import sleep

import logging
import os
import re
import requests
import tempfile
import wget
from bs4 import BeautifulSoup, NavigableString

logger = logging.getLogger(__name__)


class Item:
    def __init__(self, name, price, desc, sold_out, photo, url, local_url):
        self.name = name
        self.price = price
        self.desc = desc
        self.sold_out = sold_out
        self.photo = photo
        self.url = url
        self.local_url = local_url

    def print(self):
        logger.info(self.name)
        logger.info(self.price)
        logger.info(self.desc)
        logger.info(self.sold_out)
        logger.info(self.photo)
        logger.info(self.url)


def _get_mercari_jp_end_point(page=0, keyword='hibiki 17', price_min=None, price_max=None):
    # https://www.mercari.com/jp/search/?page=200&keyword=%E9%9F%BF%EF%BC%91%EF%BC%97&sort_order=&price_max=10000
    url = f'https://www.mercari.com/jp/search/?page={page}'
    url += f'&keyword={keyword}'
    url += '&sort_order='
    if price_max is not None:
        url += f'&price_max={price_max}'
    if price_min is not None:
        url += f'&price_min={price_min}'
    return url


def fetch_all_items(keyword: str = 'hibiki 17',
                    price_min: int = None,
                    price_max: int = None,
                    max_items_to_fetch: int = None):
    items_list = []
    for page_id in range(int(1e9)):
        items, search_res_head_tag = fetch_items_pagination(keyword, page_id, price_min, price_max)
        items_list.extend(items)
        logger.info(f'Found {len(items_list)} items so far.')

        if max_items_to_fetch is not None and len(items_list) > max_items_to_fetch:
            logger.info(f'Reached the maximum items to fetch: {max_items_to_fetch}.')
            break

        if search_res_head_tag is None:
            break
        else:
            search_res_head = str(search_res_head_tag.contents[0]).strip()
            num_items = re.findall('\d+', search_res_head)
            if len(num_items) == 1 and num_items[0] == '0':
                break
    logger.info('No more items to fetch.')
    return items_list


def fetch_items_pagination(keyword: str, page_id: int, price_min: int = None, price_max: int = None):
    soup = _get_soup(_get_mercari_jp_end_point(page_id, keyword, price_min=price_min, price_max=price_max))
    sleep(2)
    if soup.find('h3', {'class': 'search-result-no-head'}):
        logger.info('No more items to fetch.')
        items = []
        search_res_head_tag = None
        return items, search_res_head_tag
    search_res_head_tag = soup.find('h2', {'class': 'search-result-head'})
    items = [s.find('a').attrs['href'] for s in soup.find_all('section', {'class': 'items-box'})]
    for i in range(len(items)):
        items[i] = items[i][:items[i].find('?_s')]
    return items, search_res_head_tag


# https://item.mercari.com/jp/m72639077322/
# https://item.mercari.com/jp/m47283125349/ SOLD
def get_item_info(item_url: str = 'https://item.mercari.com/jp/m72639077322/') -> Item:
    soup = _get_soup(item_url)
    soup = soup.find('section', {'class': 'item-box-container'})
    price = str(soup.find('span', {'class': 'item-price bold'}).contents[0])
    name = str(soup.find('h1', {'class': 'item-name'}).contents[0])

    def filter_html_br(x):
        return isinstance(x, NavigableString)

    desc = list(filter(filter_html_br, soup.find('div', {'class': 'item-description f14'})))
    desc = list(map(str, desc))
    desc = ''.join(desc)

    sold_out = soup.find('div', {'class': 'item-sold-out-badge'})
    sold_out = sold_out is not None

    photo = soup.find('div', {'class': 'item-photo'})
    photo = photo.find('img').attrs['data-src']

    temp_folder = os.path.join(tempfile.gettempdir(), 'mercari')
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    logger.info(f'Selected tmp folder = {temp_folder}.')
    local_url = wget.download(url=photo, out=temp_folder, bar=None)
    item = Item(name=name, price=price, desc=desc, sold_out=sold_out, photo=photo, url=item_url, local_url=local_url)
    return item


def _get_soup(url):
    logger.info(f'GET: {url}')
    headers = {'User-Agent': "'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36'"}
    response = requests.get(url, headers=headers, timeout=20)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'lxml')
    return soup


def main():
    # fetch_all_items()
    item = get_item_info()
    item.print()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - mercari - %(levelname)s - %(message)s', level=logging.INFO)
    main()
