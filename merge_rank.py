import json

def merge_rank_data(init_db_path, rank_json_path, output_path):
    print("读取基础英雄骨架...")
    with open(init_db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    print("读取抓包获取的胜率排名数据...")
    with open(rank_json_path, 'r', encoding='utf-8') as f:
        rank_data = json.load(f)

    # 将 rank_data 转化为以 heroId 为 key 的字典，方便快速查找
    stats_map = {}
    hero_list = rank_data.get('data', {}).get('list', [])
    for item in hero_list:
        hero_id = item.get('heroId')
        stats_map[hero_id] = {
            "win_rate": item.get('winRate', 0),
            "ban_rate": item.get('banRate', 0),
            "pick_rate": item.get('showRate', 0),
            "tier": item.get('tRank', "T3")
        }

    print("开始将胜率注入数据库...")
    update_count = 0
    for hero in db.get("heroes", []):
        hid = hero.get("hero_id")
        # 如果能在抓到的数据里找到这个英雄的 ID
        if hid in stats_map:
            # 更新 meta_data
            hero["meta_data"]["win_rate"] = stats_map[hid]["win_rate"]
            hero["meta_data"]["ban_rate"] = stats_map[hid]["ban_rate"]
            hero["meta_data"]["pick_rate"] = stats_map[hid]["pick_rate"]
            hero["meta_data"]["tier"] = stats_map[hid]["tier"]
            update_count += 1

    # 保存新的文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
        
    print(f"合并完成！成功更新了 {update_count} 个英雄的数据。")
    print(f"最新数据已保存至: {output_path}")

if __name__ == '__main__':
    # 填入你本地的文件名
    INIT_DB_FILE = 'hero_database_init.json'  # 我们第一步生成的带头像骨架的文件
    RANK_DATA_FILE = 'rank_data.json'         # 你刚刚抓包保存下来的胜率文件
    FINAL_OUTPUT_FILE = 'hero_database_with_meta.json' # 合并后的输出文件

    merge_rank_data(INIT_DB_FILE, RANK_DATA_FILE, FINAL_OUTPUT_FILE)