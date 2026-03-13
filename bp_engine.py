import json

class BPEngine:
    def __init__(self, db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            self.db = json.load(f)
        self.heroes = self.db.get("heroes", [])
        
        # 建立快速索引字典
        self.hero_map = {str(h["hero_id"]): h for h in self.heroes}
        
        # 官方的 6 大标准职业
        self.official_roles = {"战士", "法师", "坦克", "刺客", "射手", "辅助"}

    def calculate_meta_score(self, win_rate, pick_rate, ban_rate):
        """核心 1 & 2：计算英雄的绝对版本强度 (挤掉绝活哥水分)"""
        wr_score = (win_rate - 0.50) * 100 
        bp_rate = pick_rate + ban_rate
        bp_score = bp_rate * 15  

        if pick_rate < 0.03 and win_rate > 0.51:
            wr_score *= 0.4  

        return wr_score + bp_score

    def get_current_phase_weights(self, total_picked_count):
        """核心 3：动态调整权重 (前抢强度，后拿 Counter)"""
        if total_picked_count < 6:
            return {"meta": 1.0, "counter": 0.4, "synergy": 0.6}
        else:
            return {"meta": 0.7, "counter": 1.5, "synergy": 1.0}

    def recommend(self, my_team_ids, enemy_team_ids, banned_ids):
        # 1. 看看己方已经拿了哪些“主职业”
        my_team_roles = set()
        for hid in my_team_ids:
            hero_roles = self.hero_map[hid].get("roles", [])
            if hero_roles:
                # 记录该英雄的“第一定位”（主职业）
                my_team_roles.add(hero_roles[0])

        # 计算队伍还可以拿什么职业（一共 6 个职业，5 个人肯定会剩至少 1 个职业不拿，完全合理）
        missing_roles = self.official_roles - my_team_roles
        
        recommendations = []
        unavailable_ids = set(my_team_ids + enemy_team_ids + banned_ids)
        
        total_picked = len(my_team_ids) + len(enemy_team_ids)
        weights = self.get_current_phase_weights(total_picked)

        for hero in self.heroes:
            hid = str(hero["hero_id"])
            if hid in unavailable_ids:
                continue
                
            # 2. 检查这个英雄的主职业，如果是队伍已经选过的，为了阵容合理性直接跳过
            hero_main_role = hero.get("roles", [])[0] if hero.get("roles") else None
            if not hero_main_role or hero_main_role not in missing_roles:
                continue

            # 3. 计算得分
            meta_data = hero.get("meta_data", {})
            m_score = self.calculate_meta_score(
                meta_data.get("win_rate", 0.5), 
                meta_data.get("pick_rate", 0), 
                meta_data.get("ban_rate", 0)
            )
            
            c_score = 0
            relationships = hero.get("relationships", {})
            counters_dict = relationships.get("counters", {})
            countered_by_dict = relationships.get("countered_by", {})
            
            for enemy_id in enemy_team_ids:
                c_score += counters_dict.get(str(enemy_id), 0)
                c_score -= countered_by_dict.get(str(enemy_id), 0)
                
            s_score = 0
            synergy_dict = relationships.get("synergies", {})
            for ally_id in my_team_ids:
                s_score += synergy_dict.get(str(ally_id), 0)
                
            final_score = (m_score * weights["meta"]) + \
                          (c_score * weights["counter"]) + \
                          (s_score * weights["synergy"])
                          
            recommendations.append({
                "hero_id": hid,
                "name": hero["name"],
                "role": hero_main_role,
                "scores": {
                    "final": round(final_score, 2),
                    "meta": round(m_score, 2),
                    "counter": round(c_score, 2),
                    "synergy": round(s_score, 2)
                }
            })
            
        recommendations.sort(key=lambda x: x["scores"]["final"], reverse=True)
        return recommendations[:10]


if __name__ == '__main__':
    engine = BPEngine('hero_database_full.json')
    
    # 模拟 BP 测试
    # 己方：赵云(第一定位:战士), 马可波罗(第一定位:射手)
    # 敌方：貂蝉(法师), 蔡文姬(辅助), 吕布(战士)
    recs = engine.recommend(
        my_team_ids=['107', '132'], 
        enemy_team_ids=['141', '184', '123'], 
        banned_ids=['509', '191']
    )
    
    print("✨ 当前阵容推荐选人 ✨")
    for r in recs[:5]: 
        print(f"[{r['role']}] {r['name']} | 总分:{r['scores']['final']} (强度:{r['scores']['meta']}, 克制:{r['scores']['counter']}, 配合:{r['scores']['synergy']})")