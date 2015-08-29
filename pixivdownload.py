#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import time
import cPickle as pickle
import random
import argparse
import requests

from multiprocessing import Pool
from pixivpy3 import *

PATH = os.path.abspath(sys.path[0]+os.sep+'pixiv')
MAXPOOL = 4

_USERNAME = ''
_PASSWORD = ''


def creat_src_list(imgs):
    def get_down_info(img):
        if 'image_urls' in img:
            src = img.image_urls['large']
            ext = os.path.splitext(src)[1]
            filename = '%d' % (img.id) + ext
            return {src: filename}
        else:
            return get_down_info(img.work)
    if imgs:
        src_list = dict()
        for img in imgs:
            src_list.update(get_down_info(img))
        return src_list
    else:
        return None


def download_img(src, filename, path):
    def bulid_http_header():
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.155 Safari/537.36'
        referer = 'http://www.pixiv.net'
        headers = {'Referer': referer,
                   'User-Agent': user_agent
                   }

        return headers
    headers = bulid_http_header()

    for i in range(3):
        try:
            response = requests.get(src, headers=headers, timeout=10)
        except requests.exceptions.RequestException:
            time.sleep(random.randint(5, 10))
        else:
            os.chdir(path)
            with open(filename, 'wb') as fp:
                fp.write(response.content)
            return 0
    else:
        return {src: filename}


def parser_args(args):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='flag')

    image_parser = subparsers.add_parser('i')
    image_parser.add_argument('illust_id', type=int)

    user_parser = subparsers.add_parser('u')
    user_parser.add_argument('author_id', type=int)

    rank_parser = subparsers.add_parser('r')
    rank_parser.add_argument(
        '--mode',
        choices=[
            'daily',
            'weeky',
            'monthly'],
        default='daily')

    load_parser = subparsers.add_parser('l')
    load_parser.add_argument('--load_file', default='fail_list')

    return vars(parser.parse_args(args))


def image(illust_id):
    json_result = api.works(illust_id)
    return creat_src_list(json_result.response)


def rank(mode, page=1, per_page=50, date=None):
    json_result = api.ranking_all(mode, page, per_page, date)
    return creat_src_list(json_result.response[0].works)


def users_works(author_id):
    json_result = api.users_works(author_id)
    src_list = creat_src_list(json_result.response)
    for i in range(2, json_result.pagination['pages'] + 1):
        json_result = api.users_works(author_id, page=i)
        src_list.update(creat_src_list(json_result.response))
    return src_list


def load(load_file):
    with open(load_file, 'rb') as fp:
        return pickle.load(fp)

#  def me_feeds(show_r18):
    #  json_result = api.me_feeds(show_r18)
    #  return creat_src_list(json_result.response)


def main(args):
    api = PixivAPI()
    api.login(_USERNAME, _PASSWORD)

    fuc_dict = {'i': image,
                'r': rank,
                'u': users_works,
                'l': load
                }
    args_dict = parser_args(args)

    src_list = fuc_dict[args_dict.pop('flag')](**args_dict)

    if not src_list:
        print('input error!')
        return 2

    path = PATH
    if not os.path.exists(path):
        os.mkdir(path)
    os.chdir(path)

    try:
        download_pool = Pool(processes=min(MAXPOOL, len(src_list)))
        result_list = []
        for src, filename in src_list.items():
            result_list.append(
                download_pool.apply_async(
                    download_img, (src, filename, path)))
    except Exception as e:
        print e
        sys.exit(1)
    finally:
        download_pool.close()
        download_pool.join()

    with open('fail.list', 'ab') as fp:
        fail_list = {}
        for r in result_list:
            if r.get():
                fail_list.update(r.get())
        pickle.dump(fail_list, fp)

    print('%s images download successful' % (len(src_list) - len(fail_list)))

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
