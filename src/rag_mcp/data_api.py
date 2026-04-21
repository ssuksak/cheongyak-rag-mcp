"""공공데이터포털 API 클라이언트 — 청약 공식 데이터 소스."""

import logging
from typing import Any

import httpx

from .config import get_config

logger = logging.getLogger(__name__)

API_SERVICES = {
    "apt_subscription": {
        "service_id": "15061149",
        "name": "한국부동산원_APT분양정보",
        "description": "아파트 분양/청약 정보",
    },
    "officetel_subscription": {
        "service_id": "15059223",
        "name": "한국부동산원_오피스텔분양정보",
        "description": "오피스텔 분양 정보",
    },
    "competition_rate": {
        "service_id": "15098906",
        "name": "국토교통부_청약경쟁률",
        "description": "APT 청약 경쟁률",
    },
    "presale_transfer": {
        "service_id": "15098780",
        "name": "국토교통부_분양권전매",
        "description": "분양권 전매 정보",
    },
    "lh_supply": {
        "service_id": "15058470",
        "name": "LH_공급예정주택",
        "description": "LH 공급 예정 주택 정보",
    },
    "housing_price": {
        "service_id": "15058057",
        "name": "국토교통부_주택분양가",
        "description": "주택 분양가 정보",
    },
    "price_cap": {
        "service_id": "15057583",
        "name": "한국부동산원_분양가상한제",
        "description": "분양가상한제 대상 APT",
    },
    "housing_supply": {
        "service_id": "15050056",
        "name": "국토교통부_주택공급",
        "description": "주택 공급 정보",
    },
    "supply_record": {
        "service_id": "15098647",
        "name": "국토교통부_주택공급실적",
        "description": "주택 공급 실적",
    },
}


class DataGoKrClient:
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.data_go_kr_base_url

    @property
    def is_configured(self) -> bool:
        return bool(
            self.config.data_go_kr_api_key and self.config.data_go_kr_api_key.strip()
        )

    def _request(self, service_key: str, params: dict[str, Any] | None = None) -> dict:
        if not self.is_configured:
            return {
                "error": "DATA_GO_KR_API_KEY가 설정되지 않았습니다.",
                "hint": "https://www.data.go.kr 에서 회원가입 후 아래 API들의 '활용신청'을 하세요:\n"
                + "\n".join(
                    f"  - {v['name']} (ID: {v['service_id']})"
                    for v in API_SERVICES.values()
                ),
            }

        base_params = {
            "serviceKey": self.config.data_go_kr_api_key,
            "type": "json",
            "pageNo": str(params.get("pageNo", "1")),
            "numOfRows": str(params.get("numOfRows", "50")),
        }
        if params:
            for k in ("pageNo", "numOfRows"):
                params.pop(k, None)
            base_params.update(params)

        url = f"{self.base_url}/{service_key}"
        try:
            r = httpx.get(url, params=base_params, timeout=15)
            r.raise_for_status()
            data = r.json()

            header = data.get("response", {}).get("header", {})
            result_code = header.get("resultCode", "")
            if result_code != "00":
                return {
                    "error": f"API 오류 (code: {result_code})",
                    "message": header.get("resultMsg", ""),
                    "service_id": service_key,
                }

            return data
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def list_services(self) -> list[dict]:
        return [
            {
                "key": k,
                "service_id": v["service_id"],
                "name": v["name"],
                "description": v["description"],
            }
            for k, v in API_SERVICES.items()
        ]

    def fetch_apt_subscriptions(self, **params) -> dict:
        return self._request(API_SERVICES["apt_subscription"]["service_id"], params)

    def fetch_officetel_subscriptions(self, **params) -> dict:
        return self._request(
            API_SERVICES["officetel_subscription"]["service_id"], params
        )

    def fetch_competition_rate(self, **params) -> dict:
        return self._request(API_SERVICES["competition_rate"]["service_id"], params)

    def fetch_presale_transfer(self, **params) -> dict:
        return self._request(API_SERVICES["presale_transfer"]["service_id"], params)

    def fetch_lh_supply(self, **params) -> dict:
        return self._request(API_SERVICES["lh_supply"]["service_id"], params)

    def fetch_housing_price(self, **params) -> dict:
        return self._request(API_SERVICES["housing_price"]["service_id"], params)

    def fetch_price_cap(self, **params) -> dict:
        return self._request(API_SERVICES["price_cap"]["service_id"], params)

    def fetch_housing_supply(self, **params) -> dict:
        return self._request(API_SERVICES["housing_supply"]["service_id"], params)

    def fetch_supply_record(self, **params) -> dict:
        return self._request(API_SERVICES["supply_record"]["service_id"], params)
