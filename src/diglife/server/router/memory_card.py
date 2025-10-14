from fastapi import APIRouter
from diglife.core import MemoryCardManager
from diglife.embedding_pool import EmbeddingPool
from diglife import logger
from diglife.models import MemoryCardsRequest, MemoryCard, MemoryCards, MemoryCardsGenerate, ChatHistoryOrText
import os

router = APIRouter(tags=["memory_card"])

ep = EmbeddingPool()
MCmanager = MemoryCardManager(model_name = os.getenv("llm_model_name"),
                              api_key = os.getenv("llm_api_key"))

running_log = logger.info

@router.post("/score")
async def score_from_memory_card_server(request: MemoryCardsRequest):
    """
    记忆卡片质量评分
    接收一个记忆卡片内容字符串，并返回其质量评分。
    """
    running_log("running memory_card/score")
    results = await MCmanager.ascore_from_memory_card(memory_cards=request.memory_cards)
    return {"message": "memory card score successfully", "result": results}

@router.post("/merge", response_model=MemoryCard, summary="记忆卡片合并")
async def memory_card_merge_server(request: MemoryCards) -> dict:
    running_log("running memory_card_merge")
    memory_cards = request.model_dump()["memory_cards"]
    result = await MCmanager.amemory_card_merge(memory_cards=memory_cards)
    return MemoryCard(
        title=result.get("title"),
        content=result.get("content"),
        time=result.get("time"),
    )


@router.post("/polish", response_model=MemoryCard, summary="记忆卡片发布AI润色")
async def memory_card_polish_server(request: MemoryCard) -> dict:
    """
    记忆卡片发布AI润色接口。
    接收记忆卡片内容，并返回AI润色后的结果。
    """
    running_log("running memory_card_polish")
    memory_card = request.model_dump()
    result = await MCmanager.amemory_card_polish(memory_card=memory_card)
    return MemoryCard(title=result.get("title"), content=result.get("content"), time="")


@router.post("/generate_by_text",response_model=MemoryCardsGenerate,summary="上传文件生成记忆卡片")
async def memory_card_generate_by_text_server(request: ChatHistoryOrText) -> dict:
    """
    # 0091 上传文件生成记忆卡片-memory_card_system_prompt
    # 0092 上传文件生成记忆卡片-time_prompt
    """
    running_log("running generate_by_text")
    chapters = await MCmanager.agenerate_memory_card_by_text(
        chat_history_str=request.text, weight=int(os.getenv("card_weight",1000))
    )

    return MemoryCardsGenerate(memory_cards=chapters)


@router.post("/generate",response_model=MemoryCardsGenerate,summary="聊天历史生成记忆卡片")
async def memory_card_generate_server(request: ChatHistoryOrText) -> dict:
    """
    # 0093 聊天历史生成记忆卡片-memory_card_system_prompt
    # 0094 聊天历史生成记忆卡片-time_prompt
    """
    running_log("running memory_card generate")
    chapters = await MCmanager.agenerate_memory_card(
        chat_history_str=request.text, weight=int(os.getenv("card_weight",1000))
    )

    print(chapters,'chapters')
    return MemoryCardsGenerate(memory_cards=chapters)
