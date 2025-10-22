# 1 日志不打在server中 不打在工具中, 只打在core 中

import math
import asyncio
from pro_craft.prompt_helper_async import AsyncIntel
from diglife.utils import memoryCards2str
from diglife.models import MemoryCardGenerate, MemoryCard2, MemoryCard, MemoryCardScore, MemoryCards, Document, Chapter
from diglife import super_log


class MemoryCardManager:
    def __init__(self):
        self.inters = AsyncIntel(model_name = "doubao-1-5-pro-256k-250115")

    @staticmethod
    def get_score_overall(
        S: list[int], total_score: int = 0, epsilon: float = 0.001, K: float = 0.8
    ) -> float:
        """
        计算 y = sqrt(1/600 * x) 的值。
        计算人生总进度
        """
        x = sum(S)
        
        S_r = [math.sqrt((1/101) * i)/6 for i in S]
        return sum(S_r)

        # return math.sqrt((1/601) * x)  * 100

    @staticmethod
    def get_score(
        S: list[int], total_score: int = 0, epsilon: float = 0.001, K: float = 0.01
    ) -> float:
        # 人生主题分值计算
        # 一个根据 列表分数 计算总分数的方法 如[1,4,5,7,1,5] 其中元素是 1-10 的整数

        # 一个非常小的正数，确保0分也有微弱贡献，100分也不是完美1
        # 调整系数，0 < K <= 1。K越大，总分增长越快。

        for score in S:
            # 1. 标准化每个分数到 (0, 1) 区间
            normalized_score = (score + epsilon) / (10 + epsilon)

            # 2. 更新总分
            # 每次增加的是“距离满分的剩余空间”的一个比例
            total_score = total_score + (100 - total_score) * normalized_score * K

            # 确保不会因为浮点数精度问题略微超过100，虽然理论上不会
            if total_score >= 100 - 1e-9:  # 留一点点余地，避免浮点数误差导致判断为100
                total_score = 100 - 1e-9  # 强制设置一个非常接近100但不等于100的值
                break  # 如果已经非常接近100，可以提前终止

        return total_score

    async def ascore_from_memory_card(self, memory_cards: list[str]) -> list[int]:
        # 正式运行
        tasks = []
        for memory_card in memory_cards:
            tasks.append(
                self.inters.intellect_remove_format(
                    input_data=memory_card,
                    prompt_id = "0088",
                    version = None,
                    inference_save_case=False,
                    OutputFormat = MemoryCardScore,
                )
            )
        result_1 = await asyncio.gather(*tasks, return_exceptions=False)
        return result_1

    async def amemory_card_merge(self, memory_cards: list[str]):
        memoryCards_str, memoryCards_time_str = memoryCards2str(memory_cards)
        result_1 = await self.inters.intellect_remove_format(
            input_data=memoryCards_str + "\n 各记忆卡片的时间" + memoryCards_time_str,
            prompt_id = "0089",
            version = None,
            inference_save_case=False,
            OutputFormat = MemoryCard2,
        )
        return result_1

    async def amemory_card_polish(self, memory_card: dict) -> dict:
        result_1 = await self.inters.intellect_remove_format(
            input_data="\n记忆卡片标题: "+ memory_card["title"]+ "\n记忆卡片内容: " + memory_card["content"] + "\n记忆卡片发生时间: " + memory_card["time"],
            prompt_id = "0090",
            version = None,
            inference_save_case=False,
            OutputFormat = MemoryCard,
        )
        result_1.update({"time": ""})
        return result_1

    async def agenerate_memory_card_by_text(
        self, chat_history_str: str, weight: int = 1000
    ):
        """
        0091 上传文件生成记忆卡片-memory_card_system_prompt
        0092 上传文件生成记忆卡片-time_prompt
        """
        number_ = len(chat_history_str) // weight + 1

        result_dict = await self.inters.intellect_remove_format(
            input_data = f"It is suggested to output {number_} events" + chat_history_str,
            prompt_id = "0091",
            version = None,
            inference_save_case=False,
            OutputFormat = Document,
            ExtraFormats=[Chapter],
        )
        
        chapters = result_dict["chapters"]

        tasks = []
        chapters = chapters
        for chapter in chapters:
            tasks.append(
                self.inters.intellect_remove_format(
                    input_data = f"# chat_history: {chat_history_str} # chapter:" + chapter.get("content"),
                    prompt_id = "0094",
                    version = None,
                    inference_save_case=False,
                    OutputFormat = MemoryCardGenerate,
                )
            )

        time_dicts = await asyncio.gather(*tasks, return_exceptions=False)
        
        for i,chapter in enumerate(chapters):
            chapter.update(time_dicts[i])
        return chapters

    async def agenerate_memory_card(self, chat_history_str: str, weight: int = 1000):
        """
        0093 聊天历史生成记忆卡片-memory_card_system_prompt
        0094 聊天历史生成记忆卡片-time_prompt
        """

        number_ = len(chat_history_str) // weight + 1

        result_dict = await self.inters.intellect_remove_format(
            input_data = f"建议输出卡片数量:  {number_} 个记忆卡片" + chat_history_str,
            prompt_id = "0093",
            version = None,
            inference_save_case=False,
            OutputFormat = Document,
            ExtraFormats=[Chapter],
        )

        chapters = result_dict["chapters"]

        tasks = []
        for chapter in chapters:
            tasks.append(
                self.inters.intellect_remove_format(
                    input_data = f"# chat_history: {chat_history_str} # chapter:" + chapter.get("content"),
                    prompt_id = "0094",
                    version = None,
                    inference_save_case=False,
                    OutputFormat = MemoryCardGenerate,
                )
            )

        time_dicts = await asyncio.gather(*tasks, return_exceptions=False)

        super_log(time_dicts,"time_dicts")

        for i,chapter in enumerate(chapters):
            chapter.update(time_dicts[i])
            chapter.update({"topic": 0})

        super_log(chapters,"聊天历史生成记忆卡片")
        return chapters
