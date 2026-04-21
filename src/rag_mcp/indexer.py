"""청약 데이터 RAG 인덱서."""

import json
import logging
import uuid
from dataclasses import asdict

from .config import get_config
from .scraper import CheongyakScraper, SubscriptionItem

logger = logging.getLogger(__name__)


def _item_to_documents(item: SubscriptionItem) -> list[dict]:
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{item.name}_{item.announce_date}"))

    summary = (
        f"[{item.supply_type}] {item.name}\n"
        f"지역: {item.region}\n"
        f"주택구분: {item.housing_type}\n"
        f"시공사: {item.builder}\n"
        f"모집공고일: {item.announce_date}\n"
        f"청약기간: {item.subscription_period}\n"
        f"당첨자발표일: {item.result_date}\n"
        f"문의처: {item.contact}\n"
        f"특별공급: {item.special_supply_status}"
    )

    metadata = {
        "source": "applyhome",
        "name": item.name,
        "region": item.region,
        "housing_type": item.housing_type,
        "supply_type": item.supply_type,
        "builder": item.builder,
        "announce_date": item.announce_date,
        "subscription_period": item.subscription_period,
        "result_date": item.result_date,
    }

    return [{"id": doc_id, "text": summary, "metadata": metadata}]


def index_subscriptions(vector_store, region: str | None = None) -> dict:
    scraper = CheongyakScraper()

    all_items = scraper.fetch_current_subscriptions(region=region)
    all_items += scraper.fetch_remaining_subscriptions(region=region)

    if not all_items:
        return {"indexed": 0, "total": 0, "message": "가져올 청약 데이터가 없습니다."}

    documents = []
    for item in all_items:
        documents.extend(_item_to_documents(item))

    collection = vector_store._get_collection()

    existing = collection.get(where={"source": "applyhome"}, include=["metadatas"])
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info(f"Cleared {len(existing['ids'])} existing applyhome entries")

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        collection.add(
            ids=[d["id"] for d in batch],
            documents=[d["text"] for d in batch],
            metadatas=[d["metadata"] for d in batch],
        )

    logger.info(f"Indexed {len(documents)} subscription documents")
    return {
        "indexed": len(documents),
        "total_items": len(all_items),
        "items": [asdict(item) for item in all_items],
    }


SUBSCRIPTION_GUIDE = """# 청약 자격 요건 가이드

## 1. 청약통장 종류
- **청약저축**: 국민주택규모(85㎡ 이하) 청약용, 매월 2~50만원 납입
- **청약예금**: 민영주택 청약용, 일시예치 (서울 300만원~)
- **청약부금**: 국민주택 + 민영주택 모두 가능, 매월 5~50만원 납입

## 2. 청약 순위
### 제1순위
- 청약저축: 가입 후 2년 경과 + 24회 이상 납입
- 청약예금: 가입 후 2년 경과 (예치금액 기준 지역별 상이)
- 청약부금: 가입 후 2년 경과 + 24회 이상 납입

### 제2순위
- 청약저축: 가입 후 6개월 경과 + 6회 이상 납입
- 청약예금: 가입 후 6개월 경과
- 청약부금: 가입 후 6개월 경과 + 6회 이상 납입

## 3. 주택소유 유무
- **무주택자**: 본인 및 배우자 명의 주택이 없어야 함
- **유주택자**: 1주택 소유자도 청약 가능 (규제지역 제외)
- **규제지역**: 무주택자만 청약 가능 (투기과열지구 등)

## 4. 지역 요건
- **해당지역 거주**: 청약하는 주택이 있는 지역 거주자 우선
- **거주기간**: 일부 지역은 1년 이상 거주 필요

## 5. 소득 및 자산 기준 (공공주택)
- **도시근로자 월평균소득**: 기준 중위소득 이하
- **자산기준**: 부동산·자동차 등 총자산 기준 충족
- **순자산**: 순자산액 기준 충족

## 6. 특별공급 유형
- 신혼부부 특별공급
- 다자녀 특별공급
- 노부모 부양 특별공급
- 생애최초 특별공급
- 기관추천 특별공급
- 청년 특별공급
- 이전기관 특별공급

## 7. 청약보증금
- 전용 85㎡ 이하: 200만원 (수도권 300만원)
- 전용 85㎡ 초과: 500만원
- 당첨 시 계약금은 분양가의 10%

## 8. 주의사항
- 5년간 청약당첨 횟수 제한 (규제지역 1회)
- 허위청약 시 당첨 취소 + 과태료
- 의무거주기간 존재 (1~5년)
- 분양권 전매제한 있을 수 있음
"""
