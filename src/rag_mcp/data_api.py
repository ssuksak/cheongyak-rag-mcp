"""공공데이터포털 API 클라이언트."""

import logging
from typing import Any

import httpx

from .config import get_config

logger = logging.getLogger(__name__)


class DataGoKrClient:
    def __init__(self):
        self.config = get_config()

    def _get(self, service_id: str, params: dict[str, Any] | None = None) -> dict:
        if not self.config.data_go_kr_api_key:
            return {
                "error": "DATA_GO_KR_API_KEY가 설정되지 않았습니다. data.go.kr에서 API 키를 발급받으세요."
            }

        base_params = {
            "serviceKey": self.config.data_go_kr_api_key,
            "type": "json",
            "pageNo": "1",
            "numOfRows": "50",
        }
        if params:
            base_params.update(params)

        url = f"{self.config.data_go_kr_base_url}/{service_id}"
        try:
            r = httpx.get(url, params=base_params, timeout=15)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"data.go.kr API error: {e}")
            return {"error": f"API 요청 실패: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"data.go.kr request failed: {e}")
            return {"error": f"API 요청 실패: {str(e)}"}

    def fetch_apt_list(self, region_code: str | None = None, page: int = 1) -> dict:
        return self._get(
            "15061149", {"pageNo": str(page), "LAWD_CD": region_code or ""}
        )

    def fetch_officetel_list(
        self, region_code: str | None = None, page: int = 1
    ) -> dict:
        return self._get(
            "15059223", {"pageNo": str(page), "LAWD_CD": region_code or ""}
        )
