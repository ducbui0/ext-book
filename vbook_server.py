#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tomato Novel Downloader - Intermediary HTTP Server for VBook (Python Version)
This server acts as an intermediary between the VBook app and the PC.
It serves downloaded novels, provides metadata, and triggers download jobs in the background.

Zero external dependencies - runs on standard Python 3.
"""

import os
import re
import json
import sys
import glob
import logging
import urllib.parse
import urllib.request
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

# --- File logging setup: ghi request log ra logs/server.log ---
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_file_handler = logging.FileHandler(
    os.path.join(_LOG_DIR, "server.log"), encoding="utf-8"
)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_logger = logging.getLogger("vbook_server")
_logger.setLevel(logging.INFO)
_logger.addHandler(_file_handler)

PORT = 18423

# Global dictionary for debouncing /api/jobs requests
last_job_times = {}

# Track running download processes per book_id — tránh mở nhiều CMD cùng lúc
running_jobs = {}  # book_id -> subprocess.Popen

# Server-side cache cho /api/preview — tránh scrape Fanqie mỗi lần VBook poll
_preview_cache = {}  # book_id -> {"data": metadata, "ts": timestamp}
_PREVIEW_CACHE_TTL = 300  # 5 phút (300 giây)

# Cache cho nội dung file txt để cắt chương siêu tốc
_txt_cache = {}  # book_id -> {"content": text, "ts": timestamp}
_TXT_CACHE_TTL = 600  # 10 phút

_CHUNK_SIZE = 65536  # 64 KB chunks for file streaming


# --- Fix #8: Cache save_path — chỉ đọc config.yml một lần ---
_save_path_cache = None

def get_save_path():
    """Reads the download save directory from config.yml. Result is cached after first call."""
    global _save_path_cache
    if _save_path_cache is not None:
        return _save_path_cache

    save_path = ""
    try:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("save_path:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            save_path = parts[1].strip().strip("'\"")
                            break
    except Exception as e:
        print(f"[-] Loi doc config.yml: {e}")

    # --- Fix #6: Fallback về thư mục chứa script thay vì cwd ---
    if not save_path:
        save_path = os.path.dirname(os.path.abspath(__file__))

    _save_path_cache = os.path.abspath(save_path)
    return _save_path_cache


def get_downloader_exe():
    """
    Finds the Tomato Novel Downloader CLI executable.
    Fix #7: Dùng glob pattern thay vì hardcode version name.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Glob tìm bất kỳ version nào của Windows exe, chọn mới nhất theo tên
    win_patterns = [
        os.path.join(base_dir, "TomatoNovelDownloader-Win64-*.exe"),
        os.path.join(base_dir, "TomatoNovelDownloader-*.exe"),
    ]
    for pattern in win_patterns:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]  # sort theo tên → chọn version cao nhất

    # Source build path
    source_build = os.path.join(
        base_dir, "Tomato-Novel-Downloader", "target", "release", "tomato-novel-downloader.exe"
    )
    if os.path.exists(source_build):
        return source_build

    # Linux/Mac: tìm trong PATH
    if sys.platform != "win32":
        try:
            if subprocess.call(
                ["which", "tomato-novel-downloader"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) == 0:
                return "tomato-novel-downloader"
        except Exception:
            pass

    return None


def find_key_recursive(obj, target_keys):
    """Recursively searches for a key in a JSON object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in target_keys:
                return v
            res = find_key_recursive(v, target_keys)
            if res is not None:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_key_recursive(item, target_keys)
            if res is not None:
                return res
    return None


def scan_book_files(save_dir, book_id):
    """
    Fix #2: Scan thư mục book để tìm file txt/epub thực tế.
    Nếu file nằm ở thư mục cha (do downloader sinh ra), tự động di chuyển vào thư mục book.
    Trả về dict với 'txt_file' và 'epub_file' (URL path).
    """
    result = {"txt_file": None, "epub_file": None}
    book_dir = os.path.join(save_dir, book_id)
    if not os.path.isdir(book_dir):
        return result

    # 1. Đọc status.json để lấy tên truyện thực tế
    book_name = None
    status_file = os.path.join(book_dir, "status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            book_name = data.get("book_name")
        except Exception:
            pass

    # 2. Nếu có tên truyện, kiểm tra xem có file txt/epub ở thư mục cha không và di chuyển vào trong
    if book_name:
        for ext in [".txt", ".epub"]:
            src_file = os.path.join(save_dir, book_name + ext)
            dest_file = os.path.join(book_dir, book_name + ext)
            if os.path.exists(src_file):
                try:
                    import shutil
                    shutil.move(src_file, dest_file)
                    print(f"[+] Tu dong di chuyen {book_name}{ext} vao thu muc {book_id}")
                except Exception as e:
                    print(f"[-] Khong the di chuyen file {book_name}{ext}: {e}")

    # 3. Quét thư mục con để tìm file thực tế
    try:
        for fname in os.listdir(book_dir):
            fname_lower = fname.lower()
            if fname_lower.endswith(".txt") and result["txt_file"] is None:
                result["txt_file"] = "/download/{}/{}".format(
                    urllib.parse.quote(book_id), urllib.parse.quote(fname)
                )
            elif fname_lower.endswith(".epub") and result["epub_file"] is None:
                result["epub_file"] = "/download/{}/{}".format(
                    urllib.parse.quote(book_id), urllib.parse.quote(fname)
                )
    except Exception as e:
        print(f"[-] Loi scan thu muc book {book_id}: {e}")
    return result


def build_preview_metadata(save_dir, book_id, metadata):
    """Enriches metadata dict with local file info (cover, txt_file, epub_file)."""
    metadata["book_id"] = book_id

    # Cover
    if "cover_url" not in metadata or not metadata["cover_url"]:
        for c in ["cover.jpg", "cover.png", "cover.webp", "cover.jpeg"]:
            if os.path.exists(os.path.join(save_dir, book_id, c)):
                metadata["cover_url"] = "/download/{}/{}".format(
                    urllib.parse.quote(book_id), c
                )
                break
        else:
            metadata["cover_url"] = ""

    # Txt/Epub file paths (actual scanned files)
    file_info = scan_book_files(save_dir, book_id)
    metadata["txt_file"] = file_info["txt_file"]
    metadata["epub_file"] = file_info["epub_file"]
    return metadata


def fetch_book_metadata_from_web(book_id):
    """Fetches book metadata directly from the Fanqie website."""
    url = f"https://fanqienovel.com/page/{book_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://fanqienovel.com/"
    }

    metadata = {
        "book_id": book_id,
        "book_name": f"Truyện {book_id}",
        "author": "Không rõ",
        "description": "Không có mô tả.",
        "cover_url": "",
        "finished": False,
        "chapter_count": 0,
        "word_count": 0,
        "score": 0.0,
        "read_count_text": "0",
        "category": "Chưa phân loại",
        "txt_file": None,
        "epub_file": None
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # 1. Parse __NEXT_DATA__ JSON
        next_data_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if next_data_match:
            try:
                data = json.loads(next_data_match.group(1).strip())
                book_name = find_key_recursive(data, ["bookName", "book_name", "title", "name"])
                if book_name: metadata["book_name"] = book_name
                author = find_key_recursive(data, ["author", "authorName", "author_name"])
                if author: metadata["author"] = author
                desc = find_key_recursive(data, ["abstract", "description", "intro", "introduce"])
                if desc: metadata["description"] = desc
                cover = find_key_recursive(data, ["thumb_url", "cover_url", "cover"])
                if cover: metadata["cover_url"] = cover
                finished = find_key_recursive(data, ["finished"])
                if finished is not None: metadata["finished"] = bool(finished)
                cc = find_key_recursive(data, ["chapterCount", "chapter_count"])
                if cc: metadata["chapter_count"] = int(cc)
                wc = find_key_recursive(data, ["wordCount", "word_count", "words_count"])
                if wc: metadata["word_count"] = int(wc)
                score = find_key_recursive(data, ["score", "rating_score"])
                if score: metadata["score"] = float(score)
                rc = find_key_recursive(data, ["read_count_text", "readCountText"])
                if rc: metadata["read_count_text"] = str(rc)
                cat = find_key_recursive(data, ["category", "categoryName"])
                if cat: metadata["category"] = cat
                return metadata
            except Exception as e:
                print(f"[-] Loi parse __NEXT_DATA__: {e}")

        # 2. Parse __INITIAL_STATE__ JSON
        init_state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
        if init_state_match:
            try:
                data = json.loads(init_state_match.group(1).strip())
                page_data = data.get("page", {})

                book_name = page_data.get("bookName") or find_key_recursive(page_data, ["bookName", "book_name", "title", "name"])
                if book_name: metadata["book_name"] = book_name

                author = page_data.get("authorName") or page_data.get("author") or find_key_recursive(page_data, ["authorName", "author", "author_name"])
                if author: metadata["author"] = author

                desc = page_data.get("abstract") or page_data.get("description") or find_key_recursive(page_data, ["abstract", "description", "intro", "introduce"])
                if desc: metadata["description"] = desc

                cover = page_data.get("thumbUrl") or page_data.get("cover_url") or find_key_recursive(page_data, ["thumbUrl", "thumb_url", "cover_url", "cover"])
                if cover: metadata["cover_url"] = cover

                finished = page_data.get("creationStatus")
                if finished is not None:
                    metadata["finished"] = "完结" in str(finished) or finished == 2 or finished == "2"

                cc = page_data.get("chapterTotal") or page_data.get("chapter_count")
                if cc: metadata["chapter_count"] = int(cc)

                return metadata
            except Exception as e:
                print(f"[-] Loi parse __INITIAL_STATE__: {e}")

        # 3. Basic HTML backup regex
        name_match = re.search(r'<div class="info-name"><h1>(.*?)</h1>', html)
        if name_match: metadata["book_name"] = name_match.group(1).strip()

        author_match = re.search(r'<div class="info-author">.*?<span>(.*?)</span>', html)
        if author_match: metadata["author"] = author_match.group(1).strip()

    except Exception as e:
        print(f"[-] Loi lay metadata tu web cho book_id {book_id}: {e}")

    # Fallback to fetching TOC
    try:
        toc_url = f"https://fanqienovel.com/api/reader/directory/detail?bookId={book_id}"
        req = urllib.request.Request(toc_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            toc_data = json.loads(response.read().decode("utf-8"))
            if toc_data.get("code") == 0:
                inner_data = toc_data.get("data", {})
                book_name = inner_data.get("bookName")
                if book_name: metadata["book_name"] = book_name
                vol_list = inner_data.get("chapterListWithVolume", [])
                cc = sum(len(vol) for vol in vol_list)
                if cc > 0: metadata["chapter_count"] = cc
    except Exception:
        pass

    return metadata


class VBookProxyHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        """Injects CORS headers for VBook web extensions."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-tomato-password")

    def send_json(self, data, status=200):
        """Helper: serialize and send a JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        save_dir = get_save_path()

        # 1. API: Library List
        if path == "/api/library":
            items = []
            if os.path.exists(save_dir):
                for entry in os.listdir(save_dir):
                    entry_path = os.path.join(save_dir, entry)
                    if os.path.isdir(entry_path) and entry.isdigit():
                        items.append({
                            "kind": "dir",
                            "name": entry,
                            "rel_path": entry
                        })
                    elif os.path.isfile(entry_path) and entry.lower().endswith((".txt", ".epub")):
                        items.append({
                            "kind": "file",
                            "name": entry,
                            "rel_path": entry,
                            "ext": entry.split(".")[-1].lower(),
                            "size": os.path.getsize(entry_path)
                        })

            self.send_json({
                "root": save_dir,
                "path": "",
                "items": items,
                "running": False,
                "scanned": len(items)
            })
            return

        # 1.5. API: Search Books
        if path == "/api/search":
            q = query.get("q", [""])[0].strip()
            items = []
            if q:
                try:
                    search_url = f"https://api-lf.fanqiesdk.com/api/novel/channel/homepage/search/search/v1/?offset=0&aid=1967&q={urllib.parse.quote(q)}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    req = urllib.request.Request(search_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        search_data = json.loads(response.read().decode("utf-8"))
                        ret_data = search_data.get("data", {}).get("ret_data", [])
                        for b in ret_data:
                            items.append({
                                "book_id": str(b.get("book_id")),
                                "title": b.get("title", ""),
                                "author": b.get("author", "Không rõ"),
                                "cover_url": b.get("thumb_url", "")
                            })
                except Exception as e:
                    print(f"[-] Loi tim kiem: {e}")

            self.send_json({"items": items})
            return

        # 1.7. API: Batch Preview — Fix #5: tránh N+1 requests từ homecontent.js
        if path == "/api/batch_preview":
            ids_param = query.get("ids", [""])[0]
            book_ids = [bid.strip() for bid in ids_param.split(",") if bid.strip()]
            results = {}
            for book_id in book_ids:
                # Ưu tiên dùng server-side cache nếu còn hiệu lực
                cached = _preview_cache.get(book_id)
                if cached and (time.time() - cached["ts"] < _PREVIEW_CACHE_TTL):
                    results[book_id] = cached["data"]
                    continue

                local_status_file = os.path.join(save_dir, book_id, "status.json")
                metadata = None
                if os.path.exists(local_status_file):
                    try:
                        with open(local_status_file, "r", encoding="utf-8") as f:
                            raw = json.load(f)
                        # Chỉ dùng nếu có dữ liệu thực (không phải dummy {})
                        if raw and raw.get("book_name"):
                            metadata = build_preview_metadata(save_dir, book_id, raw)
                    except Exception as e:
                        print(f"[-] Loi doc local status.json cho {book_id}: {e}")
                if not metadata:
                    # Không scrape web để tránh chậm batch; trả placeholder
                    metadata = {
                        "book_id": book_id,
                        "book_name": f"Sách {book_id}",
                        "author": "Không rõ",
                        "description": "",
                        "cover_url": "",
                        "finished": False,
                        "chapter_count": 0,
                        "txt_file": None,
                        "epub_file": None
                    }
                    metadata = build_preview_metadata(save_dir, book_id, metadata)

                # Lưu cache để /api/preview cũng được hưởng lợi
                _preview_cache[book_id] = {"data": metadata, "ts": time.time()}
                results[book_id] = metadata
            self.send_json(results)
            return

        # 2. API: Book Preview
        preview_match = re.match(r"^/api/preview/(\d+)$", path)
        if preview_match:
            book_id = preview_match.group(1)

            # Kiểm tra server-side cache trước — trả về ngay nếu còn hiệu lực
            cached = _preview_cache.get(book_id)
            if cached and (time.time() - cached["ts"] < _PREVIEW_CACHE_TTL):
                self.send_json(cached["data"])
                return

            local_status_file = os.path.join(save_dir, book_id, "status.json")
            metadata = None
            if os.path.exists(local_status_file):
                try:
                    with open(local_status_file, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    # Chỉ dùng nếu có dữ liệu thực (không phải dummy {})
                    if raw and raw.get("book_name"):
                        metadata = build_preview_metadata(save_dir, book_id, raw)
                except Exception as e:
                    print(f"[-] Loi doc local status.json cho {book_id}: {e}")

            if not metadata:
                print(f"[+] Book {book_id} chua tai, dang lay metadata tu Fanqie...")
                metadata = fetch_book_metadata_from_web(book_id)
                metadata = build_preview_metadata(save_dir, book_id, metadata)

            # Lưu vào cache
            _preview_cache[book_id] = {"data": metadata, "ts": time.time()}

            self.send_json(metadata)
            return

        # 2.5. API: Download Progress
        progress_match = re.match(r"^/api/progress/(\d+)$", path)
        if progress_match:
            book_id = progress_match.group(1)
            status_file = os.path.join(save_dir, book_id, "status.json")
            result = {
                "book_id": book_id,
                "downloaded": 0,
                "total": 0,
                "percent": 0,
                "book_name": "",
                "has_txt": False,
                "done": False
            }
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    downloaded_map = data.get("downloaded", {})
                    result["downloaded"] = len(downloaded_map)
                    result["book_name"] = data.get("book_name", "")
                    total = data.get("chapter_count", 0) or data.get("total_chapter", 0)
                    result["total"] = total
                    if total > 0:
                        result["percent"] = round(len(downloaded_map) / total * 100, 1)
                    # Kiểm tra xem có file .txt không (= đã tạo xong file gộp)
                    file_info = scan_book_files(save_dir, book_id)
                    result["has_txt"] = file_info["txt_file"] is not None
                    result["done"] = result["has_txt"] or (total > 0 and len(downloaded_map) >= total)
                except Exception as e:
                    print(f"[-] Loi doc progress cho {book_id}: {e}")
            self.send_json(result)
            return

        # 2.7. API: Chapter Extraction (Fix: Server-side chapter splitting for bulk download)
        chapter_match = re.match(r"^/api/chapter/(\d+)$", path)
        if chapter_match:
            book_id = chapter_match.group(1)
            title = query.get("title", [""])[0]
            next_title = query.get("next", [""])[0]

            file_info = scan_book_files(save_dir, book_id)
            txt_file_path = file_info["txt_file"]

            if not txt_file_path:
                self.send_error(404, "Chưa có file txt")
                return

            rel_file_path = urllib.parse.unquote(txt_file_path.replace("/download/", "", 1))
            local_path = os.path.abspath(os.path.join(save_dir, rel_file_path))

            if not os.path.exists(local_path):
                self.send_error(404, "Local file not found")
                return

            # Đọc file (có dùng cache RAM)
            txt_content = None
            cached = _txt_cache.get(book_id)
            if cached and (time.time() - cached["ts"] < _TXT_CACHE_TTL):
                txt_content = cached["content"]
            else:
                try:
                    with open(local_path, "r", encoding="utf-8") as f:
                        txt_content = f.read()
                    _txt_cache[book_id] = {"content": txt_content, "ts": time.time()}
                except Exception as e:
                    self.send_error(500, f"Lỗi đọc file txt: {e}")
                    return

            # Thuật toán cắt chương (giống JS)
            lines = txt_content.splitlines()
            start_line = -1
            end_line = len(lines)

            for i, line in enumerate(lines):
                trimmed = line.strip()
                if trimmed == title or trimmed.lower() == title.lower():
                    start_line = i + 1
                    break

            if start_line == -1:
                # Fallback indexOf
                idx = txt_content.find(title)
                if idx == -1:
                    idx = txt_content.lower().find(title.lower())
                if idx != -1:
                    start_idx = idx + len(title)
                    end_idx = len(txt_content)
                    if next_title:
                        next_idx = txt_content.find(next_title)
                        if next_idx == -1:
                            next_idx = txt_content.lower().find(next_title.lower())
                        if next_idx != -1 and next_idx > start_idx:
                            end_idx = next_idx
                    chapter_text = txt_content[start_idx:end_idx].strip()
                    self.send_json({"title": title, "content": chapter_text})
                    return
                self.send_error(404, "Không tìm thấy nội dung chương")
                return

            if next_title:
                for i in range(start_line, len(lines)):
                    trimmed = lines[i].strip()
                    if trimmed == next_title or trimmed.lower() == next_title.lower():
                        end_line = i
                        break

            chapter_text = "\n".join(lines[start_line:end_line]).strip()
            self.send_json({"title": title, "content": chapter_text})
            return

        # 3. Serving Static Files / Download Files
        download_match = re.match(r"^/download/(.+)$", path)
        if download_match:
            rel_file_path = urllib.parse.unquote(download_match.group(1))
            file_path = os.path.abspath(os.path.join(save_dir, rel_file_path))

            # Security check to prevent directory traversal
            if not file_path.startswith(save_dir):
                self.send_error(403, "Access Denied")
                return

            if os.path.exists(file_path) and os.path.isfile(file_path):
                ext = file_path.rsplit(".", 1)[-1].lower()
                mime = {
                    "txt": "text/plain; charset=utf-8",
                    "epub": "application/epub+zip",
                    "json": "application/json; charset=utf-8",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp"
                }.get(ext, "application/octet-stream")

                file_size = os.path.getsize(file_path)
                filename = os.path.basename(file_path)
                encoded_filename = urllib.parse.quote(filename)

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(file_size))
                
                # Fix: HTTP headers MUST be Latin-1. Dùng tên giả (ASCII) cho "filename", 
                # tên thật (UTF-8) dùng cho "filename*=" để hỗ trợ tiếng Trung/Việt.
                safe_ascii_name = f"download.{ext}"
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{safe_ascii_name}"; filename*=UTF-8\'\'{encoded_filename}'
                )
                self.send_cors_headers()
                self.end_headers()

                # Fix #4: Stream file theo chunks thay vì load toàn bộ vào RAM
                try:
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(_CHUNK_SIZE)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    # Khách hàng hủy kết nối giữa chừng (ví dụ: thoát màn hình đọc) - bỏ qua không in lỗi rác
                    print("[*] Thiet bi di dong da huy ket noi khi dang tai file (Connection Reset)")
                return
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b"File not found")
                return

        # 4. Standalone default response
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(b"<h3>Tomato VBook Intermediary Server is Running</h3>")
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # 1. API: Trigger Download Job
        if path == "/api/jobs":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                book_id = payload.get("book_id")
                if not book_id:
                    self.send_error(400, "Missing book_id")
                    return

                # --- DEBOUNCE + PROCESS CHECK LOGIC ---
                global last_job_times, running_jobs
                current_time = time.time()
                last_time = last_job_times.get(book_id, 0)

                # Kiểm tra nếu process cũ vẫn đang chạy → không mở CMD mới
                existing_proc = running_jobs.get(book_id)
                if existing_proc is not None and existing_proc.poll() is None:
                    print(f"[-] Bo qua /api/jobs cho ID={book_id}: tien trinh tai van dang chay (PID={existing_proc.pid})")
                    self.send_json({"success": True, "message": "Tien trinh tai dang chay, vui long cho."})
                    return

                if current_time - last_time < 120:  # 120 giây debounce để tránh spam
                    print(f"[-] Bo qua request /api/jobs cho ID={book_id} do goi qua nhanh (debounce)")
                    self.send_json({"success": True, "message": "Da bo qua do goi lien tuc."})
                    return
                last_job_times[book_id] = current_time
                # -----------------------------------------------

                exe = get_downloader_exe()
                if not exe:
                    self.send_json({
                        "error": "Khong tim thay file Tomato Novel Downloader de thuc hien tai. "
                                 "Vui long dat file .exe vao cung thu muc voi vbook_server.py."
                    }, status=500)
                    return

                save_dir = get_save_path()
                book_dir = os.path.join(save_dir, book_id)
                os.makedirs(book_dir, exist_ok=True)

                status_file = os.path.join(book_dir, "status.json")

                if not os.path.exists(status_file):
                    # Chưa có file → tạo dummy để downloader không báo lỗi "không tìm thấy book"
                    try:
                        with open(status_file, "w", encoding="utf-8") as f:
                            f.write("{}")
                        print(f"[+] Tao dummy status.json cho ID={book_id}")
                    except Exception as e:
                        print(f"[-] Khong the tao dummy status.json: {e}")

                # BẮT BUỘC LUÔN DÙNG --update
                # (Vì TomatoNovelDownloader sẽ báo lỗi "unexpected argument" nếu truyền bookId không có flag)
                # dummy status.json ở trên sẽ giúp --update hoạt động với cả sách mới
                cmd = [exe, "--update", book_id, "--retry-failed"]
                print(f"[+] Kich hoat truyen ID={book_id} bang CLI")

                if sys.platform == "win32":
                    # Dùng 'cmd /c start' để mở cửa sổ CMD hiển thị tiến độ
                    title = "TomatoNovelDownloader - ID " + book_id
                    cmd_visible = ["cmd.exe", "/c", "start", title] + cmd
                    proc = subprocess.Popen(cmd_visible, close_fds=True)
                else:
                    proc = subprocess.Popen(cmd, start_new_session=True, close_fds=True)

                # Lưu process để chặn duplicate
                running_jobs[book_id] = proc

                self.send_json({"success": True, "message": "Da kich hoat tien trinh tai xuong trong nen."})
                return
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
                return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def log_message(self, format, *args):
        """Override to write request log to both console and file."""
        msg = f"[{self.address_string()}] {format % args}"
        print(msg)
        _logger.info(msg)


def run_server():
    save_dir = get_save_path()
    exe = get_downloader_exe()

    print("===================================================================")
    print("        TOMATO NOVEL DOWNLOADER - INTERMEDIARY SERVER (PYTHON)")
    print("===================================================================")
    print(f"[*] Thu muc luu truyen (Save Directory): {save_dir}")
    if exe:
        print(f"[*] CLI Downloader duoc tim thay tai: {exe}")
    else:
        print("[-] CANH BAO: Khong tim thay executable TomatoNovelDownloader.")
        print("    -> Tinh nang tu dong tai khi 404 se khong hoat dong.")

    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, VBookProxyHandler)

    print("[*] Quet cac dia chi IP local tren may tinh...")
    hostname = socket.gethostname()
    try:
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            if not ip.startswith("127."):
                print(f"  -> [LAN]      http://{ip}:{PORT}")
    except Exception:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            print(f"  -> [LAN]      http://{s.getsockname()[0]}:{PORT}")
        except Exception:
            pass
        finally:
            s.close()

    # Hiển thị IP Tailscale nếu có
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            ts_ip = result.stdout.strip()
            if ts_ip:
                print(f"  -> [Tailscale] http://{ts_ip}:{PORT}")
    except Exception:
        # Thử đường dẫn cài đặt mặc định
        try:
            result = subprocess.run(
                [r"C:\Program Files\Tailscale\tailscale.exe", "ip", "-4"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                ts_ip = result.stdout.strip()
                if ts_ip:
                    print(f"  -> [Tailscale] http://{ts_ip}:{PORT}")
        except Exception:
            pass

    print("===================================================================")
    print(f"[+] Server dang lang nghe tren cong {PORT}...")
    print("[*] An Ctrl+C de dung server.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Dang dung server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
