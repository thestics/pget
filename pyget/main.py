#!/usr/bin/env python3
# -*-encoding: utf-8-*-
# Author: Danil Kovalenko

import sys
import argparse
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import requests
from tqdm import tqdm


def init_progress_bar(pbar, label, max_label_size, max_iterations):
    # make progress bars right-aligned
    fmt_string = "{" f":<{max_label_size}" "}"
    pbar.set_description(fmt_string.format(label))
    pbar.total = max_iterations


def update_progress_bar(pbar):
    pbar.update(1)


def validate_response(resp):
    if resp.status_code != 200:
        return False, f"Status code {resp.status_code}"
    if not 'content-length' in resp.headers:
        return False, f"Response is not a file"
    return True, ""


def close_pbars(pbars: List):
    for pbar in pbars:
        pbar.close()


def download(
        url,
        pbar: tqdm,
        max_label_size: int,
        res_dir: Path,
        ev: threading.Event,
        chunk_size: int = 1024
):
    resp = requests.get(url, stream=True)
    
    valid, reason = validate_response(resp)
    if not valid:
        pbar.set_description(
            f"{url} Failed to fetch. {reason}")
        return

    size = int(resp.headers['content-length'])
    max_iterations = size // chunk_size
    
    init_progress_bar(pbar, url, max_label_size, max_iterations)
    file_name = url.split('/')[-1]
    with open(res_dir/file_name, 'wb') as f:
        for data in resp.iter_content(chunk_size=chunk_size):
            if ev.is_set():
                return
            update_progress_bar(pbar)
            f.write(data)


def run_tasks(res_dir: str, urls: List[str]):
    """Launch an executor and perform tasks. Wait until all tasks are done"""
    res_dir = Path(res_dir)
    assert res_dir.exists()

    max_len = len(max(urls, key=lambda x: len(x))) + 1
    progress_bars = [tqdm(ncols=150) for _ in urls]
    
    # event to stop already launched tasks
    ev = threading.Event()
    
    try:
        with ThreadPoolExecutor(thread_name_prefix="download_worker") as ex:
            futures = {
                ex.submit(download, url, pb, max_len, res_dir, ev): (url, )
                for url, pb in zip(urls, progress_bars)
            }
            as_completed(futures)
    except KeyboardInterrupt:
        ev.set()
        raise
    finally:
        close_pbars(progress_bars)
    return futures


def format_output(completed_futures: dict):
    """Process completed futures, write to stderr if necessary"""
    for f, (url, ) in completed_futures.items():
        if f.exception() is not None:
            e = f.exception()
            e_msg = traceback.format_exception(type(e), e, e.__traceback__)
            err = ''.join(e_msg)
            sys.stderr.write(f"\nFailed to fetch {url}\n{err}")


def main():
    args = config_cli()
    urls = read_urls(args.input)
    res_dir = args.output
    try:
        completed = run_tasks(res_dir, urls)
        format_output(completed)
    except KeyboardInterrupt as e:
        exit("Received SIGINT, leaving.")


def config_cli():
    parser = argparse.ArgumentParser(description='Download files concurrently')
    parser.add_argument('input', type=str, help='Input file with target urls')
    parser.add_argument('output', type=str, help='Output directory')
    return parser.parse_args()


def read_urls(urls_path):
    path = Path(urls_path)
    assert path.exists()
    
    with open(path, 'r') as f:
        return [url.strip() for url in f.readlines()]


if __name__ == "__main__":
    main()