
from diglife.utils import extract_json, extract_article, super_log
from prompt_writing_assistant.prompt_helper import Intel,IntellectType
from llmada.core import BianXieAdapter, ArkAdapter
from diglife.models import MemoryCard, MemoryCardScore, MemoryCards
import math
import asyncio
import json
from .utils import memoryCards2str
inters = Intel(model_name = "doubao-1-5-pro-256k-250115")
table_name="prompts_table"
from diglife import logger
from pydantic import BaseModel, Field, model_validator


class MemoryCardManager:
    def __init__(self,model_name: str = "gemini-2.5-flash-preview-05-20-nothinking",
                      api_key: str = None):
        self.bx = BianXieAdapter(model_name=model_name,
                                 api_key= api_key,
                                 )

    @staticmethod
    def get_score_overall(
        S: list[int], total_score: int = 0, epsilon: float = 0.001, K: float = 0.8
    ) -> float:
        """
        计算 y = sqrt(1/600 * x) 的值。
        计算人生总进度
        """
        x = sum(S)
        return math.sqrt((1/600) * x)  * 100

    @staticmethod
    def get_score(
        S: list[int], total_score: int = 0, epsilon: float = 0.001, K: float = 0.1
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

        # 记忆卡片打分
        demand = "124"
        output_format = """
输出格式
```json
{
    "score": 得分,
    "reason": 给分理由
}
```
"""
        # 正式运行
        tasks = []
        for memory_card in memory_cards:
            tasks.append(
                inters.aintellect_2(input = memory_card,type=IntellectType.inference,prompt_id = "0088",demand = demand,version=None,
                                    output_format=output_format)
            )
        results = await asyncio.gather(*tasks, return_exceptions=False)

        result_1 = [json.loads(extract_json(result)) for result in results]
        try:
            for score in result_1:
                MemoryCardScore(**score)
        except:
            # log
            pass
        return result_1

    async def amemory_card_merge(self, memory_cards: list[str]):

        memoryCards_str, memoryCards_time_str = memoryCards2str(memory_cards)
        # 记忆卡片合并
        demand = "124"
        output_format = """
输出格式
```json
{
    "title": 标题,
    "content": 内容,
    "time": 发生的时间,
}
```
"""
        result = await inters.aintellect_2(input = memoryCards_str + "\n 各记忆卡片的时间" + memoryCards_time_str,
                                type=IntellectType.inference,prompt_id = "0089",demand = demand,version=None,
                                output_format=output_format)

        try:
            result_1 = json.loads(extract_json(result))
            MemoryCard(**result_1)
        except Exception as e:
            print(e)

        return result_1

    async def amemory_card_polish(self, memory_card: dict) -> dict:
        # 记忆卡片润色
        # TODO 要将时间融入到内容中润色
        # memory_card_polish_prompt, _ = inters.get_prompts_from_sql(
        #     prompt_id="0090", table_name=table_name
        # )

        demand = "124"
        output_format = """
输出格式
```json
{
    "title": 标题,
    "content": 内容,
}
```
"""
        result = await inters.aintellect_2(input = "\n记忆卡片标题: "+ memory_card["title"]+ "\n记忆卡片内容: " + memory_card["content"] + "\n记忆卡片发生时间: " + memory_card["time"],
                                type=IntellectType.inference,prompt_id = "0090",demand = demand,version=None,
                                output_format=output_format)

        try:
            result_1 = json.loads(extract_json(result))
            result_1.update({"time": ""})
            MemoryCard(**result_1)
        except Exception as e:
            print(e)

        return result_1


    async def agenerate_memory_card_by_text(
        self, chat_history_str: str, weight: int = 1000
    ):
        # 0091 上传文件生成记忆卡片-memory_card_system_prompt
        # 0092 上传文件生成记忆卡片-time_prompt
        demand = ""
        output_format = """
输出格式
```json
{
    "title": "标题内容",
    "chapters": [
        {
            "title": "记忆卡片标题",
            "content": "记忆卡片的内容"
        },
        ...
    ]
}
```
"""
        number_ = len(chat_history_str) // weight + 1
        result = await inters.aintellect_2(input = f"It is suggested to output {number_} events" + chat_history_str,
                                type=IntellectType.inference,prompt_id = "0091",demand = demand,version=None,
                                output_format=output_format)


        try:
            result_dict = json.loads(extract_json(result))

            class Chapter(BaseModel):
                title: str
                content: str

            class Output(BaseModel):
                title: str
                chapters: list[Chapter]
            Output(**result_dict)
        except Exception as e:
            print(e)
            
        chapters = result_dict["chapters"]
        output_format_2 = """
输出格式
```json
{
    "title": 卡片的标题,
    "content": chapter 提供的内容,
    "time": 卡片记录事件的发生时间,
    "score": 卡片得分,
    "tag": 卡片标签,
}
```
"""

        

        demand_2 = "24555"

        chapters = chapters
        for i in chapters:

            time_result = await inters.aintellect_2(input = f"# chat_history: {chat_history_str} # chapter:" + i.get("content"),
                                type=IntellectType.inference,prompt_id = "0092",demand = demand_2,version=None,
                                output_format=output_format_2
                                )

            time_dict = json.loads(extract_json(time_result))
            i.update(time_dict)

        return chapters


    async def agenerate_memory_card(self, chat_history_str: str, weight: int = 1000):
        # 0093 聊天历史生成记忆卡片-memory_card_system_prompt
        # 0094 聊天历史生成记忆卡片-time_prompt
        demand = ""
        output_format = """
输出格式
```json
{
    "title": "标题内容",
    "chapters": [
        {
            "title": "记忆卡片标题",
            "content": "记忆卡片的内容"
        },
        ...
    ]
}
```
"""
        number_ = len(chat_history_str) // weight + 1
        result = await inters.aintellect_2(input = f"It is suggested to output {number_} events" + chat_history_str,
                                type=IntellectType.inference,prompt_id = "0093",demand = demand,version=None,
                                output_format=output_format)

        try:
            result_dict = json.loads(extract_json(result))

            class Chapter(BaseModel):
                title: str
                content: str

            class Output(BaseModel):
                title: str
                chapters: list[Chapter]
            Output(**result_dict)
        except Exception as e:
            print(e)
            
        output_format_2 = """
输出格式
```json
{
    "title": 卡片的标题,
    "content": chapter 提供的内容,
    "time": 卡片记录事件的发生时间,
    "score": 卡片得分,
    "tag": 卡片标签,
}
```
"""


        chapters = result_dict["chapters"]
        demand_2 = """
我补充以下信息
评分规则:  
9-10 分    内容标准: 真实动人  
7-9  分     内容标准: 细节丰富  
5-7 分    内容标准: 内容完整  
3-5  分     内容标准: 略显模糊  
0-3 分    内容标准: 内容稀薄

需要为记忆卡片做一个标签(tag) 四个字以内

时间规则:
- **时间格式 (二选一):**
    1.  **具体日期:** `YYYY年MM月DD日` (未知月/日用 `--` 代替，如 `1995年07月--日`)
    2.  **年龄段:** `N到M岁` (必须为十年跨度，如 `11到20岁`, `21到30岁`)
    3. 优先**具体日期**

例如:
```json
{time: "1995年07月--日", #此类优先
 score:分数(0-10),
 tag: "四字以内"}
{time: "11到20岁",
 score:分数(0-10),
 tag: "四字以内"}
{time: "2020年--月--日",
 score:分数(0-10),
 tag: "四字以内"}
```
"""

        chapters = chapters

        for i in chapters:
            time_result = await inters.aintellect_2(input = f"# chat_history: {chat_history_str} # chapter:" + i.get("content"),
                                type=IntellectType.inference,prompt_id = "0094",demand = demand_2,version=None,
                                output_format=output_format_2
                                )
            time_dict = json.loads(extract_json(time_result))
            i.update(time_dict)
            i.update({"topic": 0})
        return chapters