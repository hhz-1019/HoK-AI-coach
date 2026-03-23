import json
from datetime import datetime

def process_hero_data(input_file, output_file):
    # 1. 定义职业映射字典
    role_mapping = {
        1: "战士",
        2: "法师",
        3: "坦克",
        4: "刺客",
        5: "射手",
        6: "辅助"
    }

    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # 准备新的数据结构
    processed_db = {
        "update_time": datetime.now().strftime("%Y-%m-%d"),
        "version": "最新版本", 
        "heroes": []
    }

    # 2. 遍历清洗数据
    for hero in raw_data:
        hero_id = hero.get("ename")
        name = hero.get("cname")
        
        # 处理多职业 (组合成一个列表)
        roles = []
        if "hero_type" in hero:
            roles.append(role_mapping[hero["hero_type"]])
        if "hero_type2" in hero:
            roles.append(role_mapping[hero["hero_type2"]])

        # 拼接头像 URL
        avatar_url = f"https://game.gtimg.cn/images/yxzj/img201606/heroimg/{hero_id}/{hero_id}.jpg"

        # 3. 构建标准化的单体英雄结构
        hero_node = {
            "hero_id": hero_id,
            "name": name,
            "roles": roles,
            "avatar_url": avatar_url,
            # 初始化预留字段，供后续数据抓取或算法模拟填充
            "meta_data": {
                "win_rate": 0.50,   # 默认 50%
                "ban_rate": 0.0,
                "pick_rate": 0.0,
                "meta_score": 50    # 版本强度初始得分
            },
            "attributes": {
                "survivability": 5, 
                "damage": 5,
                "utility": 5,
                "difficulty": 5
            },
            "relationships": {
                "counters": {},      # 克制谁
                "countered_by": {},  # 被谁克制
                "synergies": {}      # 与谁配合好
            }
        }
        
        processed_db["heroes"].append(hero_node)

    # 将处理后的数据写入新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_db, f, ensure_ascii=False, indent=2)
    
    print(f"成功处理了 {len(raw_data)} 个英雄的数据，并已保存至 {output_file}。")

# 运行脚本 (假设你把上面的数据保存为 raw_herolist.json)
process_hero_data('raw_herolist.json', 'hero_database_init.json')