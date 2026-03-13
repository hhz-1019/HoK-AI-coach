import json
import requests
import time
import random
import os

# ==============================================================================
# 🛑 第一部分：配置区
# ==============================================================================

# 1. 真实的 API 地址 (固定不变)
API_URL = "https://kohcamp.qq.com/hero/getheroextrainfo"

# 2. 抓包获取的 Headers (⚠️请去 Reqable 的“请求头”里把关键鉴权信息补全)
HEADERS = {
    "cclientversioncode": "9999999999",
    "cclientversionname": "999.999.9999",
    "ssobusinessid": "mini",
    "cgameid": "20001",
    "snsplatform": "wx",
    "xweb_xhr": "1",
    "gameid": "20001",
    "encryptversion": "5",
    "ssotoken": "YOUR_SSOTOKEN_HERE",
    "encodeparam": "YOUR_ENCODEPARAM_HERE",
    "kohdimgender": "2",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541721) XWEB/19027",
    "ssoappid": "campMiniProgram",
    "content-type": "application/json",
    "ssoopenid": "YOUR_OPENID_HERE",
    "referer": "https://servicewechat.com/wx898cb4b08963dccb/332/page-frame.html"
}

# ==============================================================================
# 🛠 第二部分：核心解析逻辑
# ==============================================================================

def parse_and_update_hero(hero_node, api_response_data):
    """
    提取克制与协同特征
    """
    try:
        real_data = api_response_data.get("data", {})
        if not real_data:
            return False

        rels = hero_node.setdefault("relationships", {"counters": {}, "countered_by": {}, "synergies": {}})

        # 1. 我克制谁 (kzInfo)
        for item in real_data.get("kzInfo", {}).get("list", []):
            rels["counters"][str(item.get("kzHeroId"))] = float(item.get("kzParam", 0))

        # 2. 谁克制我 (bkzInfo)
        for item in real_data.get("bkzInfo", {}).get("list", []):
            rels["countered_by"][str(item.get("bkzHeroId"))] = float(item.get("bkzParam", 0))

        # 3. 最佳搭档 (dfInfo)
        my_id = str(hero_node["hero_id"])
        for item in real_data.get("dfInfo", {}).get("list", []):
            hero_id_1, hero_id_2 = str(item.get("dfHeroId1")), str(item.get("dfHeroId2"))
            partner_id = hero_id_2 if hero_id_1 == my_id else hero_id_1
            rels["synergies"][partner_id] = float(item.get("dfParam", 0))

        return True
    except Exception as e:
        print(f"  [-] 解析数据时发生错误: {e}")
        return False

# ==============================================================================
# 🚀 第三部分：主调度程序 (POST 请求版)
# ==============================================================================

def main():
    input_file = 'hero_database_with_meta.json' 
    output_file = 'hero_database_full.json'
    
    if not os.path.exists(input_file):
        print(f"找不到带有胜率的骨架文件 {input_file}，请确认上一步是否执行成功！")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    heroes = db.get("heroes", [])
    total_heroes = len(heroes)
    
    print(f"开始爬取 {total_heroes} 个英雄的克制深度数据...\n")
    
    for index, hero in enumerate(heroes):
        hero_id = hero["hero_id"]
        hero_name = hero["name"]
        print(f"[{index + 1}/{total_heroes}] 正在获取 {hero_name} (ID: {hero_id}) 的克制数据...")
        
        # ⚠️ 构建 POST 请求的 Body 参数（你截图里发现的秘密就在这里）
        payload = {
            "heroId": str(hero_id)
        }
        
        success = False
        for attempt in range(3):
            try:
                # ⚠️ 这里改成了 requests.post，并且传入了 json=payload
                response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
                
                if response.status_code in [401, 403]:
                    print("  [!] 身份验证失败，请检查 Headers！")
                    return
                    
                response.raise_for_status()
                api_data = response.json()
                
                if api_data.get("returnCode") != 0:
                     print(f"  [-] 接口返回异常: {api_data.get('returnMsg')}")
                     break
                
                if parse_and_update_hero(hero, api_data):
                    success = True
                    break 
                    
            except Exception as e:
                print(f"  [-] 第 {attempt + 1} 次请求失败: {e}")
                time.sleep(2)
                
        if not success:
            print(f"  [!] {hero_name} 数据获取彻底失败，跳过。")
            
        sleep_time = random.uniform(1.5, 3.5)
        time.sleep(sleep_time)
        
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 爬取完毕！包含属性、胜率、克制矩阵的终极数据已保存至 {output_file}")

if __name__ == '__main__':
    main()