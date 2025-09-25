# 
from diglife.utils import extract_json, extract_article

from prompt_writing_assistant.prompt_helper import get_prompts_from_sql
from llmada.core import BianXieAdapter
import asyncio
import json
from pydantic import BaseModel, Field, model_validator
from prompt_writing_assistant.utils import super_print

from dotenv import load_dotenv, find_dotenv
dotenv_path = find_dotenv()
load_dotenv(dotenv_path,override=True)

bx = BianXieAdapter()



class MemoryCard(BaseModel):
    title: str
    content: str
    time: str

class MemoryCards(BaseModel):
    memory_cards: list[MemoryCard] = Field(..., description="记忆卡片列表")



from pydantic import BaseModel, Field, model_validator

class MemoryCard(BaseModel):
    title: str
    content: str
    time: str


class MemoryCardManager():
    def __init__(self):
        self.bx = BianXieAdapter()

    @staticmethod
    def get_score(S:list[int],total_score:int = 0,epsilon:float = 0.001,K:float = 0.8)->float:
        # 一个根据 列表分数 计算总分数的方法 如[1,4,5,7,1,5] 其中元素是 1-10 的整数

        # 一个非常小的正数，确保0分也有微弱贡献，100分也不是完美1
        # 调整系数，0 < K <= 1。K越大，总分增长越快。


        # 数字人生总进度 
        # 人生主题分值计算
        
        for score in S:
            # 1. 标准化每个分数到 (0, 1) 区间
            normalized_score = (score + epsilon) / (10 + epsilon)

            # 2. 更新总分
            # 每次增加的是“距离满分的剩余空间”的一个比例
            total_score = total_score + (100 - total_score) * normalized_score * K

            # 确保不会因为浮点数精度问题略微超过100，虽然理论上不会
            if total_score >= 100 - 1e-9: # 留一点点余地，避免浮点数误差导致判断为100
                total_score = 100 - 1e-9 # 强制设置一个非常接近100但不等于100的值
                break # 如果已经非常接近100，可以提前终止

        return total_score
    
    async def ascore_from_memory_card(self,memory_cards:list[str])->list[int]:
        # 记忆卡片打分 
        score_memory_card_prompt, _  = get_prompts_from_sql(prompt_id="0088",table_name = "llm_prompt")
        
        tasks = []
        for memory_card in memory_cards:
            tasks.append(
                 self.bx.aproduct(score_memory_card_prompt + "\n" + memory_card)
            )
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return [json.loads(extract_json(result)) for result in results]

    def memoryCards2str(self,memory_cards:MemoryCards):
        memoryCards_str = ""
        memoryCards_time_str = ""
        for memory_card in memory_cards:
            memory_card_str = memory_card['title'] + "\n" + memory_card['content']
            memoryCards_str += memory_card_str

            memoryCards_time_str += "\n"
            memoryCards_time_str += memory_card['time']
        return memoryCards_str, memoryCards_time_str


    async def amemory_card_merge(self,memory_cards:list[str]):
        # 记忆卡片合并
        print(memory_cards,"memory_cards")
        print(type(memory_cards))
        memory_card_merge_prompt, _  = get_prompts_from_sql(prompt_id="0089",table_name = "llm_prompt")

        memoryCards_str, memoryCards_time_str = self.memoryCards2str(memory_cards)
        super_print(memoryCards_str + "\n 各记忆卡片的时间" + memoryCards_time_str,'inpus_func')
        result = await bx.aproduct(memory_card_merge_prompt + "\n" + memoryCards_str + "\n 各记忆卡片的时间" + memoryCards_time_str)
        super_print(result,'result')
        return json.loads(extract_json(result))


    async def amemory_card_polish(self,memory_cards:MemoryCards)->dict:
        # 记忆卡片润色
        # TODO 要将时间融入到内容中润色
        memory_card_polish_prompt, _  = get_prompts_from_sql(prompt_id="0090",table_name = "llm_prompt")
        
        tasks = []
        for memory_card in memory_cards:
            tasks.append(
                 self.bx.aproduct(memory_card_polish_prompt + "\n记忆卡片标题" + memory_card['title'] + "\n记忆卡片内容" + memory_card['content'] + "\n记忆卡片发生时间" + memory_card['time'])
            )
        results = await asyncio.gather(*tasks, return_exceptions=False)

        result = {
            "title":'123',
            "content":'123',
            "time":'123'
        }
        
        results = MemoryCards(MemoryCard(title = result.get("title"),
                      content=result.get("content"),
                      time= result.get('time') 
                      ))
        return results

    async def agenerate_memory_card_by_text(self,chat_history_str:str, weight:int = 1000):
        # 0091 上传文件生成记忆卡片-memory_card_system_prompt
        # 0092 聊天历史生成记忆卡片-time_prompt

        memory_card_system_prompt, _  = get_prompts_from_sql(prompt_id="0091",table_name = "llm_prompt")
        time_prompt, _  = get_prompts_from_sql(prompt_id="0092",table_name = "llm_prompt")
    
        number_ = len(chat_history_str)//weight + 1
        base_prompt = memory_card_system_prompt.format(number = number_) + chat_history_str

        try:
            result = await bx.aproduct(base_prompt)
            result_dict = json.loads(extract_json(result))

            chapters = result_dict['chapters']
            for i in chapters:
                time_result = await bx.aproduct(time_prompt + f"# chat_history: {chat_history_str} # chapter:" + i.get('content'))
                time_dict = json.loads(extract_json(time_result))
                i.update(time_dict)

            return chapters
        except Exception as e:
            print(f"Error processing  {chat_history_str[:30]}: {e}")
            return ""
        
    async def agenerate_memory_card(self,chat_history_str:str, weight:int = 1000):
        # 0093 上传文件生成记忆卡片-memory_card_system_prompt
        # 0094 聊天历史生成记忆卡片-time_prompt


        memory_card_system_prompt, _  = get_prompts_from_sql(prompt_id="0093",table_name = "llm_prompt")
        time_prompt, _  = get_prompts_from_sql(prompt_id="0094",table_name = "llm_prompt")
    
        number_ = len(chat_history_str)//weight + 1
        base_prompt = memory_card_system_prompt.format(number = number_) + chat_history_str
        try:
            result = await bx.aproduct(base_prompt)
            result_dict = json.loads(extract_json(result))

            chapters = result_dict['chapters']
            for i in chapters:
                time_result = await bx.aproduct(time_prompt + f"# chat_history: {chat_history_str} # chapter:" + i.get('content'))
                time_dict = json.loads(extract_json(time_result))
                i.update(time_dict)

            return chapters
        except Exception as e:
            print(f"Error processing  {chat_history_str[:30]}: {e}")
            return ""

### 




class BiographyGenerate():
    def __init__(self):
        model_name = "gemini-2.5-flash-preview-05-20-nothinking"
        bx = BianXieAdapter()
        bx.model_pool.append(model_name)
        bx.set_model(model_name=model_name)
        self.bx = bx


    async def extract_person_name(self,bio_chunk:str):
        """0087 提取人名"""
        extract_person_name_prompt, _  = get_prompts_from_sql(prompt_id="0087",table_name = "llm_prompt")
        result = await self.bx.aproduct(extract_person_name_prompt + "\n" + bio_chunk)
        return json.loads(extract_json(result))


    async def extract_person_place(self,bio_chunk:str):
        """0086 提取地名"""
        extract_place_name_prompt, _  = get_prompts_from_sql(prompt_id="0086",table_name = "llm_prompt")
        result = await self.bx.aproduct(extract_place_name_prompt + "\n" + bio_chunk)
        return json.loads(extract_json(result))

    '''
    # def material_generate(self,vitae:str,memory_cards:list[str])->str: # 简历, 
    #     """
    #     素材整理
    #     vitae : 简历
    #     memory_cards : 记忆卡片们
    #     """
    #     def split_into_chunks(my_list, chunk_size = 5):
    #         """
    #         使用列表推导式将列表分割成大小为 chunk_size 的块。
    #         """
    #         return [my_list[i:i + chunk_size] for i in range(0, len(my_list), chunk_size)]

    #     # --- 示例 ---
    #     chunks = split_into_chunks(memory_cards, chunk_size = 5)

    #     material = ""
    #     for i,chunk in enumerate(chunks):
    #         chunk = json.dumps(chunk,ensure_ascii = False)
    #         if i == 0:
    #             material = self.bx.product(interview_material_clean_prompt + vitae + chunk)
    #         else:
    #             material = self.bx.product(interview_material_add_prompt + "#素材:\n" + material + "#记忆卡片:\n" + chunk)
    #     return material
    '''
 
    async def amaterial_generate(self,vitae:str,memory_cards:list[str])->str:
        """
        素材整理
        vitae : 简历
        memory_cards : 记忆卡片们
        0085 素材整理
        0082 素材增量生成
        """
        interview_material_clean_prompt, _  = get_prompts_from_sql(prompt_id="0085",table_name = "llm_prompt")
        interview_material_add_prompt, _  = get_prompts_from_sql(prompt_id="0082",table_name = "llm_prompt")
        
        def split_into_chunks(my_list, chunk_size = 5):
            """
            使用列表推导式将列表分割成大小为 chunk_size 的块。
            """
            return [my_list[i:i + chunk_size] for i in range(0, len(my_list), chunk_size)]

        # --- 示例 ---
        chunks = split_into_chunks(memory_cards, chunk_size = 5)

        material = ""
        for i,chunk in enumerate(chunks):
            chunk = json.dumps(chunk,ensure_ascii = False)
            if i == 0:
                base_prompt = interview_material_clean_prompt + vitae + chunk
                # material = await asyncio.to_thread(self.bx.product, 
                #                                    interview_material_clean_prompt + vitae + chunk)
            else:
                base_prompt = interview_material_add_prompt + "#素材:\n" + material + "#记忆卡片:\n" + chunk
                # material = await asyncio.to_thread(self.bx.product, 
                #                                    interview_material_add_prompt + "#素材:\n" + material + "#记忆卡片:\n" + chunk)
            material = await self.bx.aproduct(base_prompt)
            
        return material

    '''
    def outline_generate(self,material:str)->str:
        """
        大纲生成
        """
        outline_origin = self.bx.product(outline_prompt + material)
        outline = extract_json(outline_origin)
        return json.loads(outline)
    '''
    
    async def aoutline_generate(self,material:str)->str:
        """
        0084 大纲生成
        """

        outline_prompt, _  = get_prompts_from_sql(prompt_id="0084",table_name = "llm_prompt")
        outline_origin = await self.bx.aproduct(outline_prompt + material)
        outline = extract_json(outline_origin)
        return json.loads(outline)

    async def agener_biography_brief(self,outline:dict)->str:
        """
        0083 传记简介
        """
        biography_brief_prompt, _  = get_prompts_from_sql(prompt_id="0083",table_name = "llm_prompt")
        outline = json.dumps(outline)
        brief = await self.bx.aproduct(biography_brief_prompt + outline)
        return brief


    async def awrite_chapter(self,chapter,
                             master = "",
                             material = "", 
                             outline:dict = {},
                             suggest_number_words = 3000):
        created_material =""
        try:
            # 0080 prompt_get_infos
            # 0081 prompt_base

            prompt_get_infos, _  = get_prompts_from_sql(prompt_id="0080",table_name = "llm_prompt")
            prompt_base, _  = get_prompts_from_sql(prompt_id="0081",table_name = "llm_prompt")
        

            material_prompt = prompt_get_infos.format(material= material,frame = json.dumps(outline), requirements = json.dumps(chapter))
            material = await self.bx.aproduct(material_prompt)
            words = prompt_base.format(master = master, chapter = f'{chapter.get("chapter_number")} {chapter.get("title")}', 
                                       topic = chapter.get("topic"),
                                        number_words = suggest_number_words,
                                        material = material ,reference = "",
                                        port_chapter_summery = '' )
            article = await self.bx.aproduct(words)

            chapter_name = await self.extract_person_name(article)
            chapter_place = await self.extract_person_place(article)

            assert isinstance(chapter_name,list)
            assert isinstance(chapter_place,list)

            return {"chapter_number":chapter.get("chapter_number"),"article": extract_article(article),
                    "material":material,"created_material":created_material,
                    "chapter_name":chapter_name,
                    "chapter_place":chapter_place}
        
        except Exception as e:
            print(f"Error processing chapter {chapter.get('chapter_number')}: {e}")
            return None

    async def agenerate_biography_free(self,user_name, vitae, memory_cards:list):
        # 简要版说法
        prompt, _  = get_prompts_from_sql(prompt_id="0095",table_name = "llm_prompt")
        memory_cards_str = "\n".join(memory_cards)
        result = await bx.aproduct(prompt + "\n" + f"{user_name},{vitae},{memory_cards_str}")
        result = extract_article(result)
        return result

class DigitalAvatar():
    def __init__(self):
        pass

    async def abrief(self,memory_cards:MemoryCards)->str:
        """
        数字分身介绍
        """
        memoryCards_str, memoryCards_time_str = memoryCards2str(memory_cards)
        prompt, _  = get_prompts_from_sql(prompt_id="0098",table_name = "llm_prompt")
        feature = await bx.aproduct(prompt + memoryCards_str)

        return json.loads(extract_json(feature))
    
    async def personality_extraction(self,memory_cards:MemoryCards)->str:
        """
        数字分身性格提取
        """
        memoryCards_str, memoryCards_time_str = memoryCards2str(memory_cards)
        prompt, _  = get_prompts_from_sql(prompt_id="0099",table_name = "llm_prompt")
        result = await bx.aproduct(prompt + memoryCards_str)
        return extract_article(result)
    
    
    async def desensitization(self,memory_cards:list[str])->list[str]:
        """
        数字分身脱敏
        """
        prompt, _  = get_prompts_from_sql(prompt_id="0100",table_name = "llm_prompt")
        tasks = []
        for memory_card in memory_cards:
            tasks.append(
                 bx.aproduct(prompt + "\n" + memory_card)
            )
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return [extract_article(i) for i in results]

def memoryCards2str(memory_cards:MemoryCards):
    memoryCards_str = ""
    memoryCards_time_str = ""
    for memory_card in memory_cards:
        memory_card_str = memory_card['title'] + "\n" + memory_card['content']
        memoryCards_str += memory_card_str

        memoryCards_time_str += "\n"
        memoryCards_time_str += memory_card['time']
    return memoryCards_str, memoryCards_time_str

async def auser_dverview(old_dverview: str, memory_cards: MemoryCards)->str:
    "用户概述"
    memoryCards_str,_  = memoryCards2str(memory_cards)

    prompt, _  = get_prompts_from_sql(prompt_id="0096",table_name = "llm_prompt")

    result = await bx.aproduct(prompt + old_dverview + memoryCards_str)

    return result


async def auser_relationship_extraction(chat_history: str)->dict:
    """
    用户关系提取
    """
    prompt, _  = get_prompts_from_sql(prompt_id="0097",table_name = "llm_prompt")
    
    result = await bx.aproduct( prompt +  "聊天历史"+ chat_history)

    return json.loads(extract_json(result))

