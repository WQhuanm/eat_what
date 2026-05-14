"""
商家类型解析与向量化增强模块 V2

根据实际爬取的57个商家数据，建立更精准的分类映射
"""
from typing import Dict, List, Optional, Tuple


# ========== 1. 商家主营品类映射（基于实际数据） ==========
# 从商家名称中提取的核心品类关键词
SHOP_TYPE_KEYWORDS = {
    # === 面食类 ===
    "肉夹馍": {"categories": ["特色小吃", "面食"], "taste": ["咸"], "scene": "正餐/快餐"},
    "凉皮": {"categories": ["特色小吃", "面食"], "taste": ["咸", "辣"], "scene": "正餐/快餐"},
    "油泼面": {"categories": ["米粉面条", "地方菜系"], "taste": ["咸", "辣"], "scene": "正餐"},
    "小面": {"categories": ["米粉面条", "地方菜系"], "taste": ["麻辣", "咸"], "scene": "正餐/快餐"},
    "拉面": {"categories": ["米粉面条"], "taste": ["咸"], "scene": "正餐"},
    "牛肉面": {"categories": ["米粉面条"], "taste": ["咸", "辣"], "scene": "正餐"},
    "拌面": {"categories": ["米粉面条"], "taste": ["咸"], "scene": "正餐/快餐"},
    "米线": {"categories": ["米粉面条"], "taste": ["咸"], "scene": "正餐"},
    "米粉": {"categories": ["米粉面条"], "taste": ["咸"], "scene": "正餐"},
    "炒粉": {"categories": ["米粉面条"], "taste": ["咸"], "scene": "正餐/快餐"},
    "肠粉": {"categories": ["粥食点心", "特色小吃"], "taste": ["咸", "清淡"], "scene": "早餐/正餐"},
    
    # === 粥食早点 ===
    "粥": {"categories": ["粥食点心"], "taste": ["清淡", "咸"], "scene": "早餐/轻食"},
    "小笼包": {"categories": ["粥食点心", "饺子馄饨"], "taste": ["咸", "清淡"], "scene": "早餐/正餐"},
    "烧麦": {"categories": ["粥食点心"], "taste": ["咸"], "scene": "早餐"},
    "汤包": {"categories": ["粥食点心", "饺子馄饨"], "taste": ["咸"], "scene": "早餐/正餐"},
    "撒汤": {"categories": ["粥食点心"], "taste": ["咸"], "scene": "早餐"},
    "胡辣汤": {"categories": ["粥食点心", "地方菜系"], "taste": ["麻辣", "咸"], "scene": "早餐"},
    "疙瘩汤": {"categories": ["粥食点心"], "taste": ["咸", "清淡"], "scene": "早餐/轻食"},
    "早点": {"categories": ["粥食点心"], "taste": ["咸"], "scene": "早餐"},
    "糕点": {"categories": ["粥食点心", "甜品烘焙"], "taste": ["甜"], "scene": "早餐/下午茶"},
    
    # === 轻食健康 ===
    "轻食": {"categories": ["快餐便当"], "taste": ["清淡", "咸"], "scene": "轻食/减脂"},
    "沙拉": {"categories": ["快餐便当"], "taste": ["清淡", "咸"], "scene": "轻食/减脂"},
    "减脂": {"categories": ["快餐便当"], "taste": ["清淡", "咸"], "scene": "轻食/减脂"},
    "健康餐": {"categories": ["快餐便当"], "taste": ["清淡", "咸"], "scene": "轻食/减脂"},
    
    # === 饮品 ===
    "咖啡": {"categories": ["奶茶果汁"], "taste": ["苦", "甜"], "scene": "早餐/下午茶"},
    "奶茶": {"categories": ["奶茶果汁"], "taste": ["甜", "奶香"], "scene": "下午茶/夜宵"},
    "茶饮": {"categories": ["奶茶果汁"], "taste": ["甜", "清香"], "scene": "下午茶"},
    "果茶": {"categories": ["奶茶果汁"], "taste": ["甜", "酸"], "scene": "下午茶"},
    "果汁": {"categories": ["奶茶果汁"], "taste": ["甜", "酸"], "scene": "下午茶"},
    
    # === 甜品 ===
    "甜品": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶/夜宵"},
    "蛋糕": {"categories": ["奶茶果汁"], "taste": ["甜", "奶香"], "scene": "下午茶/生日"},
    "糖水": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "双皮奶": {"categories": ["奶茶果汁"], "taste": ["甜", "奶香"], "scene": "下午茶"},
    "巴斯克": {"categories": ["奶茶果汁"], "taste": ["甜", "奶香"], "scene": "下午茶"},
    "千层": {"categories": ["奶茶果汁"], "taste": ["甜", "奶香"], "scene": "下午茶"},
    
    # === 日韩料理 ===
    "寿司": {"categories": ["地方菜系"], "taste": ["咸", "鲜"], "scene": "正餐/轻食"},
    "日料": {"categories": ["地方菜系"], "taste": ["咸", "鲜"], "scene": "正餐"},
    "韩料": {"categories": ["地方菜系"], "taste": ["辣", "咸", "甜"], "scene": "正餐"},
    
    # === 快餐便当 ===
    "盖饭": {"categories": ["快餐便当"], "taste": ["咸"], "scene": "正餐/快餐"},
    "木桶饭": {"categories": ["快餐便当"], "taste": ["咸", "辣"], "scene": "正餐"},
    "猪脚饭": {"categories": ["快餐便当"], "taste": ["咸", "酱香"], "scene": "正餐"},
    "牛腩饭": {"categories": ["快餐便当"], "taste": ["咸", "酱香"], "scene": "正餐"},
    "拌饭": {"categories": ["快餐便当"], "taste": ["咸", "辣"], "scene": "正餐"},
    "盒饭": {"categories": ["快餐便当"], "taste": ["咸"], "scene": "正餐"},
    "简餐": {"categories": ["快餐便当"], "taste": ["咸"], "scene": "正餐/快餐"},
    "双拼": {"categories": ["快餐便当"], "taste": ["咸"], "scene": "正餐"},
    "套餐": {"categories": ["快餐便当"], "taste": ["咸"], "scene": "正餐"},
    "老乡鸡": {"categories": ["快餐便当"], "taste": ["咸", "清淡"], "scene": "正餐/快餐"},
    
    # === 地方菜系/炒菜 ===
    "酸菜鱼": {"categories": ["地方菜系"], "taste": ["酸", "辣", "咸"], "scene": "正餐"},
    "小炒": {"categories": ["地方菜系"], "taste": ["咸", "辣"], "scene": "正餐"},
    "炒菜": {"categories": ["地方菜系"], "taste": ["咸", "辣"], "scene": "正餐"},
    "沙县": {"categories": ["特色小吃"], "taste": ["咸", "清淡"], "scene": "正餐/快餐"},
    "家常菜": {"categories": ["地方菜系"], "taste": ["咸"], "scene": "正餐"},
    "江西": {"categories": ["地方菜系"], "taste": ["辣", "咸"], "scene": "正餐"},
    "湘菜": {"categories": ["地方菜系"], "taste": ["辣", "咸"], "scene": "正餐"},
    "川菜": {"categories": ["地方菜系"], "taste": ["麻辣", "咸"], "scene": "正餐"},
    "东北菜": {"categories": ["地方菜系"], "taste": ["咸", "酱香"], "scene": "正餐"},
    "猪蹄": {"categories": ["地方菜系", "特色小吃"], "taste": ["咸", "酱香"], "scene": "正餐"},
    "排骨": {"categories": ["地方菜系"], "taste": ["咸", "甜", "酱香"], "scene": "正餐"},
    "排骨锅": {"categories": ["地方菜系", "火锅干锅"], "taste": ["麻辣", "咸"], "scene": "正餐"},
    
    # === 烧烤烤肉 ===
    "烧烤": {"categories": ["烧烤烤肉"], "taste": ["咸", "辣", "孜然"], "scene": "夜宵/聚餐"},
    "烤肉": {"categories": ["烧烤烤肉"], "taste": ["咸", "辣", "孜然"], "scene": "正餐/聚餐"},
    "烤鸡": {"categories": ["烧烤烤肉"], "taste": ["咸", "香辣"], "scene": "正餐"},
    "烤鱼": {"categories": ["烧烤烤肉", "地方菜系"], "taste": ["麻辣", "咸", "鲜"], "scene": "正餐/聚餐"},
    "烤串": {"categories": ["烧烤烤肉"], "taste": ["咸", "辣", "孜然"], "scene": "夜宵"},
    "炭烤": {"categories": ["烧烤烤肉"], "taste": ["咸", "香"], "scene": "正餐"},
    "生蚝": {"categories": ["烧烤烤肉", "龙虾海鲜"], "taste": ["咸", "鲜", "蒜香"], "scene": "夜宵/聚餐"},
    "铁板烧": {"categories": ["烧烤烤肉"], "taste": ["咸", "酱香"], "scene": "正餐"},
    "烤肉筋": {"categories": ["烧烤烤肉"], "taste": ["咸", "辣"], "scene": "夜宵"},
    "荷叶烤鸡": {"categories": ["烧烤烤肉"], "taste": ["咸", "清香"], "scene": "正餐"},
    
    # === 炸鸡炸串 ===
    "鸡排": {"categories": ["炸鸡炸串"], "taste": ["咸", "香辣"], "scene": "正餐/快餐"},
    "炸鸡": {"categories": ["炸鸡炸串"], "taste": ["咸", "香辣"], "scene": "正餐/快餐"},
    "炸串": {"categories": ["炸鸡炸串"], "taste": ["咸", "辣"], "scene": "夜宵"},
    "香酥": {"categories": ["炸鸡炸串"], "taste": ["咸", "香"], "scene": "正餐"},
    "脆皮": {"categories": ["炸鸡炸串"], "taste": ["咸", "香"], "scene": "正餐"},
    "烧鸡": {"categories": ["炸鸡炸串", "烧烤烤肉"], "taste": ["咸", "五香"], "scene": "正餐"},
    
    # === 龙虾海鲜 ===
    "龙虾": {"categories": ["龙虾海鲜"], "taste": ["麻辣", "咸", "鲜"], "scene": "夜宵/聚餐"},
    "小龙虾": {"categories": ["龙虾海鲜"], "taste": ["麻辣", "咸", "鲜"], "scene": "夜宵/聚餐"},
    "大闸蟹": {"categories": ["龙虾海鲜"], "taste": ["咸", "鲜"], "scene": "正餐/聚餐"},
    "海鲜": {"categories": ["龙虾海鲜"], "taste": ["咸", "鲜"], "scene": "正餐/聚餐"},
    
    # === 火锅干锅 ===
    "火锅鸡": {"categories": ["火锅干锅"], "taste": ["麻辣", "咸", "酱香"], "scene": "正餐/聚餐"},
    "火锅": {"categories": ["火锅干锅"], "taste": ["麻辣", "咸"], "scene": "正餐/聚餐"},
    "干锅": {"categories": ["火锅干锅"], "taste": ["麻辣", "咸"], "scene": "正餐/聚餐"},
    "牛蛙": {"categories": ["火锅干锅"], "taste": ["麻辣", "咸", "鲜"], "scene": "正餐/聚餐"},
    
    # === 饺子馄饨 ===
    "饺子": {"categories": ["饺子馄饨"], "taste": ["咸"], "scene": "正餐"},
    "馄饨": {"categories": ["饺子馄饨"], "taste": ["咸", "清淡"], "scene": "正餐/早餐"},
    "抄手": {"categories": ["饺子馄饨"], "taste": ["麻辣", "咸"], "scene": "正餐"},
    "云吞": {"categories": ["饺子馄饨"], "taste": ["咸", "清淡"], "scene": "正餐/早餐"},
    "水饺": {"categories": ["饺子馄饨"], "taste": ["咸"], "scene": "正餐"},
    "瓦罐汤": {"categories": ["饺子馄饨", "粥食点心"], "taste": ["咸", "清淡", "鲜"], "scene": "正餐"},
    
    # === 披萨西餐 ===
    "披萨": {"categories": ["汉堡薯条"], "taste": ["咸", "奶香"], "scene": "正餐/聚餐"},
    "意面": {"categories": ["汉堡薯条"], "taste": ["咸", "酱香"], "scene": "正餐"},
    "焗饭": {"categories": ["汉堡薯条"], "taste": ["咸", "奶香"], "scene": "正餐"},
    "汉堡": {"categories": ["汉堡薯条"], "taste": ["咸", "香"], "scene": "正餐/快餐"},
    "薯条": {"categories": ["汉堡薯条"], "taste": ["咸", "香"], "scene": "正餐/快餐"},
    "三明治": {"categories": ["汉堡薯条"], "taste": ["咸"], "scene": "早餐/轻食"},
    "西餐": {"categories": ["汉堡薯条"], "taste": ["咸", "奶香"], "scene": "正餐"},
    "必胜客": {"categories": ["汉堡薯条"], "taste": ["咸", "奶香"], "scene": "正餐/聚餐"},
    "麦当劳": {"categories": ["汉堡薯条"], "taste": ["咸", "香"], "scene": "正餐/快餐"},
    "中国汉堡": {"categories": ["汉堡薯条"], "taste": ["咸", "香"], "scene": "正餐/快餐"},
    
    # === 麻辣烫冒菜 ===
    "麻辣烫": {"categories": ["麻辣烫冒菜"], "taste": ["麻辣", "咸"], "scene": "正餐/夜宵"},
    "冒菜": {"categories": ["麻辣烫冒菜"], "taste": ["麻辣", "咸"], "scene": "正餐"},
    "麻辣拌": {"categories": ["麻辣烫冒菜"], "taste": ["麻辣", "咸", "甜"], "scene": "正餐"},
    
    # === 叫花鸡/窑鸡/手撕鸡 ===
    "叫花鸡": {"categories": ["特色小吃", "烧烤烤肉"], "taste": ["咸", "香"], "scene": "正餐"},
    "窑鸡": {"categories": ["特色小吃", "烧烤烤肉"], "taste": ["咸", "香", "嫩"], "scene": "正餐"},
    "手撕鸡": {"categories": ["特色小吃", "烧烤烤肉"], "taste": ["咸", "麻辣", "香"], "scene": "正餐"},
}


# ========== 2. 品牌映射 ==========
BRAND_TYPE_MAP = {
    "瑞幸咖啡": {"categories": ["奶茶果汁"], "taste": ["苦", "甜"], "scene": "早餐/下午茶"},
    "星巴克": {"categories": ["奶茶果汁"], "taste": ["苦", "甜"], "scene": "早餐/下午茶"},
    "麦当劳": {"categories": ["汉堡薯条"], "taste": ["咸", "香"], "scene": "正餐/快餐"},
    "肯德基": {"categories": ["汉堡薯条", "炸鸡炸串"], "taste": ["咸", "香辣"], "scene": "正餐/快餐"},
    "必胜客": {"categories": ["汉堡薯条"], "taste": ["咸", "奶香"], "scene": "正餐/聚餐"},
    "华莱士": {"categories": ["汉堡薯条", "炸鸡炸串"], "taste": ["咸", "香辣"], "scene": "正餐/快餐"},
    "塔斯汀": {"categories": ["汉堡薯条"], "taste": ["咸", "香"], "scene": "正餐/快餐"},
    "老乡鸡": {"categories": ["快餐便当"], "taste": ["咸", "清淡"], "scene": "正餐/快餐"},
    "沙县小吃": {"categories": ["特色小吃"], "taste": ["咸", "清淡"], "scene": "正餐/快餐"},
    "杨国福": {"categories": ["麻辣烫冒菜"], "taste": ["麻辣", "咸"], "scene": "正餐"},
    "张亮": {"categories": ["麻辣烫冒菜"], "taste": ["麻辣", "咸"], "scene": "正餐"},
    "蜜雪冰城": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "古茗": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "沪上阿姨": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "茶百道": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "喜茶": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "奈雪": {"categories": ["奶茶果汁"], "taste": ["甜"], "scene": "下午茶"},
    "正新鸡排": {"categories": ["炸鸡炸串"], "taste": ["咸", "香辣"], "scene": "正餐/快餐"},
    "久久鸭": {"categories": ["鸭脖卤味"], "taste": ["麻辣", "咸"], "scene": "零食/夜宵"},
    "绝味": {"categories": ["鸭脖卤味"], "taste": ["麻辣", "咸"], "scene": "零食/夜宵"},
    "周黑鸭": {"categories": ["鸭脖卤味"], "taste": ["麻辣", "甜", "咸"], "scene": "零食/夜宵"},
}


# ========== 3. 辅助函数 ==========

def extract_shop_type_info(shop_name: str) -> Dict[str, any]:
    """
    从商家名称提取完整的类型信息
    
    Returns:
        {
            "categories": ["米粉面条", "地方菜系"],  # 12大分类映射
            "taste_context": ["咸", "辣"],           # 口味上下文提示
            "scene": "正餐/快餐",                    # 用餐场景
            "specialties": ["油泼面", "肉夹馍"],     # 主营单品
        }
    """
    if not shop_name:
        return {"categories": [], "taste_context": [], "scene": "正餐", "specialties": []}
    
    categories = []
    taste_context = []
    scene = "正餐"
    specialties = []
    
    # 1. 按分隔符拆分名称
    parts = []
    for sep in ["·", "•", "-", "–", "&"]:
        if sep in shop_name:
            parts = [p.strip() for p in shop_name.split(sep)]
            break
    if not parts:
        parts = [shop_name]
    
    # 2. 从拆分后的部分提取关键词
    for part in parts:
        for keyword, info in SHOP_TYPE_KEYWORDS.items():
            if keyword in part and keyword not in specialties:
                specialties.append(keyword)
                # 合并分类（去重）
                for cat in info["categories"]:
                    if cat not in categories:
                        categories.append(cat)
                # 合并口味上下文
                for t in info["taste"]:
                    if t not in taste_context:
                        taste_context.append(t)
                # 更新场景（取最具体的）
                if info["scene"] and len(info["scene"]) > len(scene):
                    scene = info["scene"]
    
    # 3. 品牌匹配（如果前面没有匹配到）
    if not categories:
        for brand, info in BRAND_TYPE_MAP.items():
            if brand in shop_name:
                categories = info["categories"].copy()
                taste_context = info["taste"].copy()
                scene = info["scene"]
                specialties = [brand]
                break
    
    return {
        "categories": categories,
        "taste_context": taste_context,
        "scene": scene,
        "specialties": specialties,
    }


def get_primary_cuisine(shop_name: str, *texts: str) -> str:
    """
    获取商家的主分类（12大分类之一）
    """
    info = extract_shop_type_info(shop_name)
    
    # 优先返回第一个有效的12大分类
    valid_cuisines = [
        "烧烤烤肉", "奶茶果汁", "炸鸡炸串", "鸭脖卤味", "特色小吃",
        "米粉面条", "快餐便当", "汉堡薯条", "粥食点心", "地方菜系",
        "麻辣烫冒菜", "饺子馄饨"
    ]
    
    for cat in info["categories"]:
        if cat in valid_cuisines:
            return cat
    
    # 回退到关键词匹配
    text = " ".join([t for t in texts if t])
    for cuisine in valid_cuisines:
        keywords = []
        if cuisine == "烧烤烤肉":
            keywords = ["烧烤", "烤肉", "烤", "串", "炭烤", "烤鱼"]
        elif cuisine == "奶茶果汁":
            keywords = ["奶茶", "果汁", "茶饮", "果茶", "咖啡", "甜品", "蛋糕"]
        elif cuisine == "炸鸡炸串":
            keywords = ["炸鸡", "炸串", "鸡排", "香酥", "脆皮"]
        elif cuisine == "鸭脖卤味":
            keywords = ["鸭脖", "卤味", "卤", "凤爪"]
        elif cuisine == "特色小吃":
            keywords = ["小吃", "特色", "煎饼", "肉夹馍", "臭豆腐", "凉皮", "叫花鸡", "窑鸡", "手撕鸡"]
        elif cuisine == "米粉面条":
            keywords = ["米粉", "面条", "米线", "拉面", "牛肉面", "拌面", "炒粉", "小面"]
        elif cuisine == "快餐便当":
            keywords = ["便当", "套餐", "快餐", "盖饭", "炒饭", "简餐", "饭", "双拼", "轻食", "沙拉"]
        elif cuisine == "汉堡薯条":
            keywords = ["汉堡", "薯条", "披萨", "意面", "三明治", "西餐"]
        elif cuisine == "粥食点心":
            keywords = ["粥", "点心", "包子", "烧麦", "小笼包", "汤包", "肠粉", "早点", "糕点"]
        elif cuisine == "地方菜系":
            keywords = ["川菜", "湘菜", "粤菜", "江浙菜", "家常菜", "小炒", "酸菜鱼", "江西", "东北菜", "寿司", "日料"]
        elif cuisine == "麻辣烫冒菜":
            keywords = ["麻辣烫", "冒菜", "麻辣拌", "火锅鸡"]
        elif cuisine == "饺子馄饨":
            keywords = ["饺子", "馄饨", "抄手", "云吞", "水饺"]
        
        if any(k in text for k in keywords):
            return cuisine
    
    return "快餐便当"


def enhance_taste_scores(shop_name: str, base_scores: Dict[str, float]) -> Dict[str, float]:
    """
    根据商家类型增强口味分数
    
    Args:
        shop_name: 商家名称
        base_scores: 基础口味分数（从 infer_taste_scores 获得）
    
    Returns:
        增强后的口味分数
    """
    info = extract_shop_type_info(shop_name)
    scores = base_scores.copy()
    
    # 根据商家类型的口味上下文调整分数
    taste_boost = {
        "麻辣": {"辣": 1.5, "咸": 0.5},
        "辣": {"辣": 1.0},
        "咸": {"咸": 0.8},
        "甜": {"甜": 1.2},
        "酸": {"酸": 0.8},
        "清淡": {"清淡": 1.0, "辣": -0.5, "咸": -0.3},
        "苦": {"苦": 0.5},
        "奶香": {"甜": 0.5},
        "鲜": {"咸": 0.3},
        "孜然": {"咸": 0.3, "辣": 0.3},
        "蒜香": {"咸": 0.3},
        "五香": {"咸": 0.5},
        "酱香": {"咸": 0.5, "甜": 0.3},
    }
    
    for taste in info["taste_context"]:
        if taste in taste_boost:
            for dim, boost in taste_boost[taste].items():
                if dim in scores:
                    scores[dim] = min(5.0, scores[dim] + boost)
    
    return scores


if __name__ == "__main__":
    # 测试
    test_names = [
        "杜小姐在西北·肉夹馍·凉皮·油泼面",
        "祁姥姥家现熬疙瘩汤",
        "星选老师傅龙虾馆·冰镇龙虾(九堡旗舰店)",
        "瑞幸咖啡",
        "正新鸡排·炸鸡烧烤",
        "杨国福麻辣烫·麻辣拌",
        "遇见村上千层蛋糕·现烤巴斯克",
        "唐小研叫花鸡·窑鸡·手撕鸡",
        "蜀美人·牛蛙·烤鱼",
        "冒大仙成都火锅冒菜·天水麻辣烫",
    ]
    
    for name in test_names:
        info = extract_shop_type_info(name)
        cuisine = get_primary_cuisine(name)
        print(f"{name}")
        print(f"  主分类: {cuisine}")
        print(f"  所有分类: {info['categories']}")
        print(f"  口味上下文: {info['taste_context']}")
        print(f"  主营单品: {info['specialties']}")
        print(f"  场景: {info['scene']}")
        print()
