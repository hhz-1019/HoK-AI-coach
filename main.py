import json
import os
import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BPEngine:
    def __init__(self, db_path):
        db_path = os.path.join(BASE_DIR, db_path)
        role_path = os.path.join(BASE_DIR, 'role.json')
        alias_path = os.path.join(BASE_DIR, 'hero_aliases.json')
        
        # 增加一个检查逻辑，方便在日志里看报错
        if not os.path.exists(db_path):
            print(f"CRITICAL ERROR: {db_path} 不存在！当前目录下文件有: {os.listdir(BASE_DIR)}")
            self.heroes = []
            self.hero_map = {}
            return
        with open(db_path, 'r', encoding='utf-8') as f:
            self.db = json.load(f)

        self.role_lane_map = {}
        if os.path.exists(role_path):
            with open(role_path, 'r', encoding='utf-8') as f:
                self.role_lane_map = json.load(f)

        self.heroes = self.db.get("heroes", [])
        self.hero_map = {str(h["hero_id"]): h for h in self.heroes}
        self.official_roles = {"战士", "法师", "坦克", "刺客", "射手", "辅助"}

        self.default_role_to_lanes = {
            "战士": ["对抗路"],
            "法师": ["中路"],
            "坦克": ["对抗路", "游走"],
            "刺客": ["打野"],
            "射手": ["发育路"],
            "辅助": ["游走"]
        }

        # 英雄别名映射已外置到 hero_aliases.json，便于持续维护
        self.hero_name_aliases = self.get_default_hero_aliases()
        if os.path.exists(alias_path):
            try:
                with open(alias_path, 'r', encoding='utf-8') as f:
                    loaded_aliases = json.load(f)
                if isinstance(loaded_aliases, dict):
                    self.hero_name_aliases.update(loaded_aliases)
            except Exception as e:
                print(f"WARN: hero_aliases.json 读取失败，将使用内置别名映射。错误: {e}")

        self.normalized_role_lane_map = {
            self.normalize_hero_name(name): lanes
            for name, lanes in self.role_lane_map.items()
        }
        
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

        # === 算法性能优化：预构建静态缓存（空间换时间），将嵌套寻址化为 O(1) 哈希查询 ===
        self.precalc_primary_role = {}
        self.precalc_lane_options = {}
        self.precalc_meta_norm = {}
        self.precalc_counters = {}
        self.precalc_countered_by = {}
        self.precalc_synergies = {}
        
        for h in self.heroes:
            hid = str(h["hero_id"])
            self.precalc_primary_role[hid] = self.get_primary_role(h)
            self.precalc_lane_options[hid] = self.get_hero_lane_options(h)
            
            # 提前归一化强度分，保证手动填写的英雄梯度机制不变，但是寻址和数学计算加速
            m_score = self.get_meta_score_by_name(h["name"])
            self.precalc_meta_norm[hid] = self.clamp((m_score - 5.0) / 15.0, -1.0, 1.0)
            
            rels = h.get("relationships", {})
            self.precalc_counters[hid] = rels.get("counters", {})
            self.precalc_countered_by[hid] = rels.get("countered_by", {})
            self.precalc_synergies[hid] = rels.get("synergies", {})

    def get_meta_score_by_name(self, hero_name):
        return self.tier_scores.get(hero_name, 5)

    def clamp(self, value, lower, upper):
        return max(lower, min(upper, value))

    def squash_score(self, raw_score, scale):
        # 使用 tanh 做饱和压缩，避免单项极值把总分拉爆
        return math.tanh(raw_score / scale)

    def signed_power_stretch(self, value, power):
        # 拉开高低分差距：中段更稳，强势与劣势更明显
        return math.copysign(abs(value) ** power, value)

    def get_primary_role(self, hero):
        roles = hero.get("roles", [])
        return roles[0] if roles else None

    def get_default_hero_aliases(self):
        return {
            "鲁班七号": "鲁班",
            "李元芳": "元芳",
            "马可波罗": "马可",
            "元流之子(法师)": "元法",
            "元流之子(坦克)": "元坦",
            "元流之子(射手)": "元射",
            "元流之子(辅助)": "元辅",
            "蚩奼": "蚩姹"
        }

    def normalize_hero_name(self, name):
        if not name:
            return ""
        text = str(name).strip()
        text = text.replace("（", "(").replace("）", ")")
        text = text.replace(" ", "")
        return text

    def get_lane_options_by_name(self, hero_name):
        if not hero_name:
            return []

        # 1) 先尝试原名/别名精确命中
        if hero_name in self.role_lane_map:
            return self.role_lane_map[hero_name]

        alias_name = self.hero_name_aliases.get(hero_name)
        if alias_name and alias_name in self.role_lane_map:
            return self.role_lane_map[alias_name]

        # 2) 归一化后再匹配
        normalized_name = self.normalize_hero_name(hero_name)
        if normalized_name in self.normalized_role_lane_map:
            return self.normalized_role_lane_map[normalized_name]

        if alias_name:
            normalized_alias = self.normalize_hero_name(alias_name)
            if normalized_alias in self.normalized_role_lane_map:
                return self.normalized_role_lane_map[normalized_alias]

        return []

    def get_hero_lane_options(self, hero):
        # 优先使用 role.json 的分路定义
        from_role_json = self.get_lane_options_by_name(hero.get("name"))
        if from_role_json:
            return from_role_json

        # role.json 未覆盖时，回退到 roles 推断
        lane_options = []
        for role in hero.get("roles", []):
            lane_options.extend(self.default_role_to_lanes.get(role, []))

        # 去重且保序
        return list(dict.fromkeys(lane_options))

    def get_occupied_lanes(self, my_team_ids):
        occupied_lanes = set()
        for hid in my_team_ids:
            options = self.precalc_lane_options.get(str(hid))
            if not options:
                continue

            picked_lane = None
            for lane in options:
                if lane not in occupied_lanes:
                    picked_lane = lane
                    break

            if not picked_lane:
                picked_lane = options[0]

            occupied_lanes.add(picked_lane)

        return occupied_lanes

    def get_team_composition_penalty(self, my_team_ids, candidate_hero):
        # 优化：不生成多余的实例列表，直接累加预计算的主职业
        candidate_hid = str(candidate_hero["hero_id"])
        primary_roles = [self.precalc_primary_role.get(str(hid)) for hid in my_team_ids]
        primary_roles.append(self.precalc_primary_role.get(candidate_hid))
        primary_roles = [r for r in primary_roles if r]
        
        role_counts = {}
        for role in primary_roles:
            role_counts[role] = role_counts.get(role, 0) + 1

        penalty = 0.0

        # 重复主职业会降低阵容稳定性
        for count in role_counts.values():
            if count > 1:
                penalty += (count - 1) * 4.0

        team_size = len(primary_roles)
        has_frontline = role_counts.get("坦克", 0) + role_counts.get("战士", 0) > 0
        has_support = role_counts.get("辅助", 0) > 0
        has_magic = role_counts.get("法师", 0) > 0
        has_marksman = role_counts.get("射手", 0) > 0

        if team_size >= 4 and not has_frontline:
            penalty += 6.0
        if team_size >= 5:
            if not has_support:
                penalty += 4.0
            if not has_magic:
                penalty += 3.0
            if not has_marksman:
                penalty += 3.0

        return penalty

    def get_current_phase_weights(self, total_picked_count):
        if total_picked_count < 4:
            return {"meta": 0.55, "counter": 0.15, "synergy": 0.30}
        elif total_picked_count < 7:
            return {"meta": 0.30, "counter": 0.40, "synergy": 0.30}
        else:
            return {"meta": 0.20, "counter": 0.50, "synergy": 0.30}

    # 🌟 接收新增的 good_at_ids 和 bad_at_ids
    def recommend(self, my_team_ids, enemy_team_ids, banned_ids, good_at_ids, bad_at_ids):
        # 按 role.json 推断已占分路：已占路不再推荐同路英雄
        occupied_lanes = self.get_occupied_lanes(my_team_ids)

        recommendations = []
        unavailable_ids = set(my_team_ids + enemy_team_ids + banned_ids)
        total_picked = len(my_team_ids) + len(enemy_team_ids)
        weights = self.get_current_phase_weights(total_picked)

        for hero in self.heroes:
            hid = str(hero["hero_id"])
            if hid in unavailable_ids:
                continue
                
            # 缓存优化读取
            hero_primary_role = self.precalc_primary_role.get(hid)
            if not hero_primary_role:
                continue

            lane_options = self.precalc_lane_options.get(hid, [])
            if lane_options and all(lane in occupied_lanes for lane in lane_options):
                continue
            
            # 使用预计算的结果衡量基础胜率强度，完全忠于您设定的 tier_scores 梯度排行
            meta_norm = self.precalc_meta_norm[hid]
            
            c_score = 0
            counters = self.precalc_counters[hid]
            countered_by = self.precalc_countered_by[hid]
            for enemy_id in enemy_team_ids:
                c_score += counters.get(str(enemy_id), 0)
                c_score -= countered_by.get(str(enemy_id), 0)
                
            s_score = 0
            synergies = self.precalc_synergies[hid]
            for ally_id in my_team_ids:
                s_score += synergies.get(str(ally_id), 0)
                
            # 个人偏好加权，避免绝活分过大导致结果失真
            personal_score = 0
            if hid in good_at_ids:
                personal_score = 0.08
            elif hid in bad_at_ids:
                personal_score = -0.15

            composition_penalty = self.get_team_composition_penalty(my_team_ids, hero)

            # 统一归一化：保留三维都参与，同时提高区分度
            counter_norm = self.squash_score(c_score, 3.2)
            synergy_norm = self.squash_score(s_score, 3.0)
            composition_penalty_norm = self.clamp(composition_penalty / 15.0, 0.0, 1.0)

            positive_factors = [v for v in [meta_norm, counter_norm, synergy_norm] if v > 0.35]
            negative_factors = [v for v in [meta_norm, counter_norm, synergy_norm] if v < -0.3]

            # 三项中至少两项同向优秀时给协同加成，避免“看起来都差不多”
            synergy_bonus = 0.0
            if len(positive_factors) >= 2:
                synergy_bonus = 0.18 * (sum(positive_factors) / len(positive_factors))

            # 若多项显著偏弱，则额外惩罚
            conflict_penalty = 0.0
            if len(negative_factors) >= 2:
                conflict_penalty = 0.16 * (abs(sum(negative_factors)) / len(negative_factors))
                
            final_norm = (
                meta_norm * weights["meta"]
                + counter_norm * weights["counter"]
                + synergy_norm * weights["synergy"]
                + synergy_bonus
                + personal_score
                - composition_penalty_norm
                - conflict_penalty
            )

            stretched_norm = self.signed_power_stretch(self.clamp(final_norm, -1.5, 1.5), 1.2)
            final_score = self.clamp(58 + stretched_norm * 42, 18, 98)
                          
            recommendations.append({
                "hero_id": hid,
                "name": hero["name"],
                "avatar_url": hero["avatar_url"],
                "role": hero_primary_role,
                "is_good_at": hid in good_at_ids,  # 传给前端打上特殊标记
                "scores": {
                    "final": round(final_score, 2),
                    "meta": round(meta_norm * 100, 2),
                    "counter": round(counter_norm * 100, 2),
                    "synergy": round(synergy_norm * 100, 2),
                    "composition_penalty": round(composition_penalty, 2),
                    "synergy_bonus": round(synergy_bonus * 100, 2),
                    "conflict_penalty": round(conflict_penalty * 100, 2)
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