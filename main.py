import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BPEngine:
    def __init__(self, db_path):
        db_path = os.path.join(BASE_DIR, db_path)
        
        # 增加一个检查逻辑，方便在日志里看报错
        if not os.path.exists(db_path):
            print(f"CRITICAL ERROR: {db_path} 不存在！当前目录下文件有: {os.listdir(BASE_DIR)}")
            self.heroes = []
            self.hero_map = {}
            return
        with open(db_path, 'r', encoding='utf-8') as f:
            self.db = json.load(f)
        self.heroes = self.db.get("heroes", [])
        self.hero_map = {str(h["hero_id"]): h for h in self.heroes}
        self.official_roles = {"战士", "法师", "坦克", "刺客", "射手", "辅助"}
        
        # 你的手动梯度字典保持不变
        self.tier_scores = {
            "金蝉": -5, "明世隐": -5, "程咬金": -5,
            "姜子牙": 0, "元流之子(法师)": 0, "米莱狄": 0, "妲己": 0, "安琪拉": 0, "嬴政": 0,
            "黄忠": 0, "扁鹊": 0, "元流之子(坦克)": 0, "阿轲": 0, "云中君": 0,
            "孙膑": 0, "牛魔": 0, "庄周": 0, "钟无艳": 0, "亚连": 0, "吕布": 0, "亚瑟": 0,
            "伽罗": 2, "夏侯惇": 2, "蔡文姬": 2, 
            "莱西奥": 3, "蒙犽": 3, "百里守约": 3, "刘备": 3, "赵云": 3,
            "东皇太一": 3, "钟馗": 3, "廉颇": 3, "猪八戒": 3, "项羽": 3, "白起": 3,
            "干将莫邪": 5, "周瑜": 5, "弈星": 5, "鲁班七号": 5, "李元芳": 5, "马可波罗": 5,
            "曜": 5, "李白": 5, "娜可露露": 5, "兰陵王": 5, "瑶": 5, "赵怀真": 5, 
            "朵莉亚": 5, "刘禅": 5, "芈月": 5, "梦奇": 5, "李信": 5, 
            "王昭君": 8, "澜": 8,
            "武则天": 8, "上官婉儿": 8, "后羿": 8, "孙悟空": 8, "盘古": 8,
            "桑启": 8, "刘邦": 8, "鬼谷子": 8, "孙策": 8, "姬小满": 8, "达摩": 8,
            "高渐离": 10, "海诺": 10, "虞姬": 10, "苍": 10, "司马懿": 10, "典韦": 10, 
            "雅典娜": 10, "大司命": 10, "大禹": 10, "张良": 10, "鲁班大师": 10, 
            "墨子": 10, "花木兰": 10, "影": 10, "哪吒": 10,
            "孙权": 12, "铠": 12,
            "不知火舞": 12, "貂蝉": 12, "甄姬": 12, "小乔": 12, "狄仁杰": 12,
            "阿古朵": 12, "露娜": 12, "橘右京": 12, "杨戬": 12, "夏洛特": 12, 
            "曹操": 12, "老夫子": 12, "司空震": 12,
            "诸葛亮": 15, "杨玉环": 15, "西施": 15, "孙尚香": 15, "戈娅": 15, "艾琳": 15,
            "暃": 15, "云缨": 15, "韩信": 15, "百里玄策": 15, "宫本武藏": 15,
            "大乔": 15, "张飞": 15, "太乙真人": 15, "空空儿": 15, "蒙恬": 15, "关羽": 15, "狂铁": 15,
            "海月": 18, "嫦娥": 18, "沈梦溪": 18, "公孙离": 18, "敖隐": 18, "元流之子(射手)": 18,
            "裴擒虎": 18, "苏烈": 18, "元流之子(辅助)": 18, "元歌": 18, "马超": 18,
            "女娲": 20, "镜": 20, "盾山": 20, "少司缘": 20, "蚩奼": 20
        }

    def get_meta_score_by_name(self, hero_name):
        return self.tier_scores.get(hero_name, 5)

    def get_current_phase_weights(self, total_picked_count):
        if total_picked_count < 4:
            return {"meta": 1.2, "counter": 0.3, "synergy": 0.5}
        elif total_picked_count < 7:
            return {"meta": 0.5, "counter": 2.2, "synergy": 1.8}
        else:
            return {"meta": 0.1, "counter": 4.0, "synergy": 3.5}

    # 🌟 接收新增的 good_at_ids 和 bad_at_ids
    def recommend(self, my_team_ids, enemy_team_ids, banned_ids, good_at_ids, bad_at_ids):
        my_team_roles = set()
        for hid in my_team_ids:
            hero_roles = self.hero_map[str(hid)].get("roles", [])
            for r in hero_roles:
                my_team_roles.add(r)

        recommendations = []
        unavailable_ids = set(my_team_ids + enemy_team_ids + banned_ids)
        total_picked = len(my_team_ids) + len(enemy_team_ids)
        weights = self.get_current_phase_weights(total_picked)

        for hero in self.heroes:
            hid = str(hero["hero_id"])
            if hid in unavailable_ids:
                continue
                
            hero_roles = set(hero.get("roles", []))
            if not hero_roles or (hero_roles & my_team_roles):
                continue

            m_score = self.get_meta_score_by_name(hero["name"])
            
            c_score = 0
            relationships = hero.get("relationships", {})
            counters = relationships.get("counters", {})
            countered_by = relationships.get("countered_by", {})
            
            for enemy_id in enemy_team_ids:
                c_score += counters.get(str(enemy_id), 0)
                c_score -= countered_by.get(str(enemy_id), 0)
                
            s_score = 0
            synergies = relationships.get("synergies", {})
            for ally_id in my_team_ids:
                s_score += synergies.get(str(ally_id), 0)
                
            # 🌟 个人绝活赋分机制：擅长 +15分(跨阶跃升)，不擅长 -20分(打入冷宫)
            personal_score = 0
            if hid in good_at_ids:
                personal_score = 5
            elif hid in bad_at_ids:
                personal_score = -10
                
            final_score = (m_score * weights["meta"]) + (c_score * weights["counter"]) + (s_score * weights["synergy"]) + personal_score
                          
            recommendations.append({
                "hero_id": hid,
                "name": hero["name"],
                "avatar_url": hero["avatar_url"],
                "role": list(hero_roles)[0], 
                "is_good_at": hid in good_at_ids,  # 传给前端打上特殊标记
                "scores": {
                    "final": round(final_score, 2),
                    "meta": round(m_score, 2), 
                    "counter": round(c_score * weights["counter"], 2),
                    "synergy": round(s_score * weights["synergy"], 2)
                }
            })
            
        recommendations.sort(key=lambda x: x["scores"]["final"], reverse=True)
        
        # 🌟 修改为提取 10 个名额，前5个保证各位置不重样，后5个顺延
        diverse_recs = []
        seen_roles = set()
        for rec in recommendations:
            rec_main_role = rec["role"]
            if rec_main_role not in seen_roles:
                diverse_recs.append(rec)
                seen_roles.add(rec_main_role)
            if len(diverse_recs) == 10:
                break
                
        if len(diverse_recs) < 10:
            for rec in recommendations:
                if rec not in diverse_recs:
                    diverse_recs.append(rec)
                if len(diverse_recs) == 10:
                    break

        return diverse_recs

app = FastAPI(title="王者荣耀 BP 推荐 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bp_engine = BPEngine('hero_database_full.json')

@app.get("/")
async def get_index():
    path = os.path.join(BASE_DIR, 'index.html')
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "index.html not found", "checked_path": path}

# 🌟 新增偏好字段
class BPRequest(BaseModel):
    my_team_ids: List[str]
    enemy_team_ids: List[str]
    banned_ids: List[str]
    good_at_ids: List[str] = []
    bad_at_ids: List[str] = []

@app.get("/hero_database_full.json")
async def get_json():
    path = os.path.join(BASE_DIR, 'hero_database_full.json')
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "File not found", "checked_path": path}

@app.post("/api/recommend")
async def get_recommendations(req: BPRequest):
    recs = bp_engine.recommend(
        my_team_ids=req.my_team_ids,
        enemy_team_ids=req.enemy_team_ids,
        banned_ids=req.banned_ids,
        good_at_ids=req.good_at_ids,
        bad_at_ids=req.bad_at_ids
    )
    return {"status": "success", "data": recs}

if __name__ == "__main__":
    import uvicorn
    import os
    # 优先读取系统分配的端口，如果没有（比如在本地），则默认使用 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)