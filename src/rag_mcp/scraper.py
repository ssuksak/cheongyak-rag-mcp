"""청약홈 (applyhome.co.kr) 웹 스크래퍼."""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .config import get_config

ALLOWED_DOMAINS = {"static.applyhome.co.kr", "www.applyhome.co.kr", "applyhome.co.kr"}

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


@dataclass
class SubscriptionItem:
    region: str
    housing_type: str
    supply_type: str
    name: str
    builder: str
    contact: str
    announce_date: str
    subscription_period: str
    result_date: str
    special_supply_status: str
    competition_rate_link: str


@dataclass
class SubscriptionDetail:
    name: str
    region: str
    builder: str
    supply_info: list[dict]
    schedule: dict
    eligibility: dict
    supply_counts: dict
    price_info: list[dict]
    raw_tables: list[dict]


@dataclass
class CalendarEntry:
    date: str
    name: str
    region: str
    type: str


class CheongyakScraper:
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.applyhome_base_url
        self._cache: dict = {}
        self._cache_time: dict = {}

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers=HEADERS, timeout=20, follow_redirects=True, max_redirects=3
        )

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        elapsed = time.time() - self._cache_time[key]
        return elapsed < self.config.cache_ttl_minutes * 60

    def fetch_current_subscriptions(
        self, region: str | None = None, page: int = 1
    ) -> list[SubscriptionItem]:
        cache_key = f"list_{region}_{page}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        items = []
        with self._get_client() as client:
            params = {"page": str(page)}
            if region:
                params["sido"] = region

            r = client.get(
                f"{self.base_url}/ai/aia/selectAPTLttotPblancListView.do", params=params
            )
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")

            if not table:
                logger.warning("No table found on 청약홈 list page")
                return items

            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all(["td"])
                if len(cells) < 8:
                    continue

                item = SubscriptionItem(
                    region=cells[0].get_text(strip=True),
                    housing_type=cells[1].get_text(strip=True),
                    supply_type=cells[2].get_text(strip=True),
                    name=cells[3].get_text(strip=True),
                    builder=cells[4].get_text(strip=True),
                    contact=cells[5].get_text(strip=True),
                    announce_date=cells[6].get_text(strip=True),
                    subscription_period=cells[7].get_text(strip=True),
                    result_date=cells[8].get_text(strip=True) if len(cells) > 8 else "",
                    special_supply_status=cells[9].get_text(strip=True)
                    if len(cells) > 9
                    else "",
                    competition_rate_link=cells[10].get_text(strip=True)
                    if len(cells) > 10
                    else "",
                )

                if region and region not in item.region:
                    continue
                items.append(item)

        self._cache[cache_key] = items
        self._cache_time[cache_key] = time.time()
        logger.info(f"Fetched {len(items)} subscriptions from 청약홈 (page {page})")
        return items

    def fetch_subscription_detail(self, name: str) -> SubscriptionDetail | None:
        with self._get_client() as client:
            r = client.get(f"{self.base_url}/ai/aia/selectAPTLttotPblancListView.do")
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")

            if not table:
                return None

            target_row = None
            target_item = None
            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all(["td"])
                if len(cells) >= 4 and name in cells[3].get_text(strip=True):
                    target_row = row
                    target_item = {
                        "name": cells[3].get_text(strip=True),
                        "region": cells[0].get_text(strip=True),
                        "builder": cells[4].get_text(strip=True),
                        "announce_date": cells[6].get_text(strip=True),
                        "subscription_period": cells[7].get_text(strip=True),
                        "result_date": cells[8].get_text(strip=True)
                        if len(cells) > 8
                        else "",
                    }
                    break

            if not target_row or not target_item:
                return None

            hmno = target_row.get("data-hmno", "")
            pbno = target_row.get("data-pbno", "")
            honm = target_row.get("data-honm", "")

            detail_tables = []
            schedule = {
                "announce_date": target_item["announce_date"],
                "subscription_period": target_item["subscription_period"],
                "result_date": target_item["result_date"],
            }
            supply_info = []
            price_info = []
            file_urls = []

            if hmno and pbno:
                form_data = {
                    "houseManageNo": hmno,
                    "pblancNo": pbno,
                    "houseNm": honm,
                }
                r2 = client.post(
                    f"{self.base_url}/ai/aia/selectAPTLttotPblancDetail.do",
                    data=form_data,
                )
                soup2 = BeautifulSoup(r2.text, "html.parser")
                detail_page_tables = soup2.find_all("table")

                for tbl in detail_page_tables:
                    cap = tbl.find("caption")
                    cap_text = cap.get_text(strip=True) if cap else ""
                    table_rows = tbl.find_all("tr")
                    table_data = []
                    for tr in table_rows:
                        row_cells = [
                            td.get_text(strip=True) for td in tr.find_all(["th", "td"])
                        ]
                        if row_cells:
                            table_data.append(row_cells)

                    detail_tables.append({"caption": cap_text, "rows": table_data})

                    if "청약일정" in cap_text:
                        for tr_data in table_data:
                            for cell in tr_data:
                                if re.match(r"\d{4}-\d{2}-\d{2}", cell):
                                    if "모집공고" in " ".join(tr_data):
                                        schedule["announce_date"] = cell
                                    elif "당첨" in " ".join(tr_data):
                                        schedule["result_date"] = cell

                    elif "공급대상" in cap_text and "특별" not in cap_text:
                        for tr_data in table_data[1:]:
                            if len(tr_data) >= 5:
                                supply_info.append(
                                    {
                                        "type": tr_data[0] if len(tr_data) > 0 else "",
                                        "area": tr_data[1] if len(tr_data) > 1 else "",
                                        "supply_area": tr_data[2]
                                        if len(tr_data) > 2
                                        else "",
                                        "general": tr_data[3]
                                        if len(tr_data) > 3
                                        else "",
                                        "special": tr_data[4]
                                        if len(tr_data) > 4
                                        else "",
                                        "total": tr_data[5] if len(tr_data) > 5 else "",
                                    }
                                )

                    elif "공급금액" in cap_text:
                        for tr_data in table_data[1:]:
                            if len(tr_data) >= 2:
                                price_info.append(
                                    {
                                        "type": tr_data[0],
                                        "price": tr_data[1] if len(tr_data) > 1 else "",
                                        "deposit_2nd": tr_data[2]
                                        if len(tr_data) > 2
                                        else "",
                                    }
                                )

                for a_tag in soup2.find_all("a", href=True):
                    href = a_tag["href"]
                    if "atchmnfl" in href.lower() or "download" in href.lower():
                        file_urls.append(
                            {
                                "url": href
                                if href.startswith("http")
                                else f"{self.base_url}{href}",
                                "label": a_tag.get_text(strip=True),
                            }
                        )

            return SubscriptionDetail(
                name=target_item["name"],
                region=target_item["region"],
                builder=target_item["builder"],
                supply_info=supply_info,
                schedule=schedule,
                eligibility={},
                supply_counts={},
                price_info=price_info,
                raw_tables=detail_tables,
            )

    def download_attachment(
        self, name: str, save_dir: str = "./data/documents"
    ) -> list[str]:
        detail = self.fetch_subscription_detail(name)
        if not detail or not detail.raw_tables:
            return []

        saved_files = []
        with self._get_client() as client:
            r = client.get(f"{self.base_url}/ai/aia/selectAPTLttotPblancListView.do")
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")

            if not table:
                return []

            rows = table.find_all("tr")
            target_row = None
            for row in rows[1:]:
                cells = row.find_all(["td"])
                if len(cells) >= 4 and name in cells[3].get_text(strip=True):
                    target_row = row
                    break

            if not target_row:
                return []

            hmno = target_row.get("data-hmno", "")
            pbno = target_row.get("data-pbno", "")

            if not hmno or not pbno:
                return []

            form_data = {
                "houseManageNo": hmno,
                "pblancNo": pbno,
                "houseNm": target_row.get("data-honm", ""),
            }
            r2 = client.post(
                f"{self.base_url}/ai/aia/selectAPTLttotPblancDetail.do",
                data=form_data,
            )
            soup2 = BeautifulSoup(r2.text, "html.parser")

            for a_tag in soup2.find_all("a", href=True):
                href = a_tag["href"]
                if "atchmnfl" not in href.lower():
                    continue

                if not href.startswith(("/", "https://", "http://")):
                    continue

                url = (
                    href
                    if href.startswith("http")
                    else f"https://static.applyhome.co.kr{href}"
                )

                parsed_url = urlparse(url)
                if parsed_url.scheme not in ("http", "https"):
                    logger.warning(f"Skipping non-HTTP URL: {url}")
                    continue
                if parsed_url.hostname not in ALLOWED_DOMAINS:
                    logger.warning(f"Skipping external domain: {url}")
                    continue

                label = a_tag.get_text(strip=True)
                safe_name = re.sub(r"[^\w가-힣]", "_", name)[:30]
                safe_label = re.sub(r"[^\w가-힣.]", "_", label)[:50]

                try:
                    save_dir_resolved = Path(save_dir).resolve()
                    save_dir_resolved.mkdir(parents=True, exist_ok=True)
                    filepath = (
                        save_dir_resolved / f"{safe_name}_{safe_label}{ext}"
                    ).resolve()
                    if not str(filepath).startswith(str(save_dir_resolved)):
                        logger.error(f"Path escape detected: {filepath}")
                        continue

                    resp = client.get(url, follow_redirects=True)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "")
                        ext = ".pdf"
                        if "hwp" in content_type:
                            ext = ".hwp"
                        elif "html" in content_type:
                            ext = ".html"

                        filepath.write_bytes(resp.content)
                        saved_files.append(str(filepath))
                        logger.info(f"Downloaded: {filepath}")
                except Exception as e:
                    logger.error(f"Download failed for {url}: {e}")

        return saved_files

    def fetch_calendar(
        self, year: int | None = None, month: int | None = None
    ) -> list[CalendarEntry]:
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        entries = []
        with self._get_client() as client:
            params = {"year": str(year), "month": str(month)}
            r = client.get(
                f"{self.base_url}/ai/aib/selectSubscrptCalenderView.do", params=params
            )
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")

            if not table:
                return entries

            cells = table.find_all("td")
            for td in cells:
                day_text = td.get_text(strip=True)
                links = td.find_all("a")
                for link in links:
                    link_text = link.get_text(strip=True)
                    if link_text and link_text not in ["경쟁률", "상세"]:
                        onclick = link.get("onclick", "")
                        entries.append(
                            CalendarEntry(
                                date=f"{year}-{month:02d}",
                                name=link_text,
                                region="",
                                type="",
                            )
                        )

        return entries

    def fetch_remaining_subscriptions(
        self, region: str | None = None
    ) -> list[SubscriptionItem]:
        items = []
        with self._get_client() as client:
            params = {}
            if region:
                params["sido"] = region

            r = client.get(
                f"{self.base_url}/ai/aia/selectAPTRemndrLttotPblancListView.do",
                params=params,
            )
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")

            if not table:
                return items

            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all(["td"])
                if len(cells) < 6:
                    continue

                items.append(
                    SubscriptionItem(
                        region=cells[0].get_text(strip=True),
                        housing_type=cells[1].get_text(strip=True),
                        supply_type=cells[2].get_text(strip=True),
                        name=cells[3].get_text(strip=True),
                        builder=cells[4].get_text(strip=True),
                        contact=cells[5].get_text(strip=True) if len(cells) > 5 else "",
                        announce_date=cells[6].get_text(strip=True)
                        if len(cells) > 6
                        else "",
                        subscription_period=cells[7].get_text(strip=True)
                        if len(cells) > 7
                        else "",
                        result_date="",
                        special_supply_status="",
                        competition_rate_link="",
                    )
                )

        return items

    def fetch_other_subscriptions(self) -> list[SubscriptionItem]:
        items = []
        with self._get_client() as client:
            r = client.get(f"{self.base_url}/ai/aia/selectOtherLttotPblancListView.do")
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")

            if not table:
                return items

            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all(["td"])
                if len(cells) < 4:
                    continue

                items.append(
                    SubscriptionItem(
                        region=cells[0].get_text(strip=True),
                        housing_type=cells[1].get_text(strip=True)
                        if len(cells) > 1
                        else "",
                        supply_type="기타",
                        name=cells[3].get_text(strip=True),
                        builder=cells[4].get_text(strip=True) if len(cells) > 4 else "",
                        contact=cells[5].get_text(strip=True) if len(cells) > 5 else "",
                        announce_date=cells[6].get_text(strip=True)
                        if len(cells) > 6
                        else "",
                        subscription_period="",
                        result_date="",
                        special_supply_status="",
                        competition_rate_link="",
                    )
                )

        return items

    def search_subscriptions(self, keyword: str) -> list[SubscriptionItem]:
        all_items = self.fetch_current_subscriptions()
        all_items += self.fetch_remaining_subscriptions()

        keyword_lower = keyword.lower()
        return [
            item
            for item in all_items
            if keyword_lower in item.name.lower()
            or keyword_lower in item.region.lower()
            or keyword_lower in item.builder.lower()
        ]
