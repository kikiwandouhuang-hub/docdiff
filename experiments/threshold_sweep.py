import difflib

# 样本格式: (旧文本, 新文本, 期望标签, dist段落偏移距离)
DATASET = [
    # --- 真实修改 (就地或近距离编辑, dist <= 2) ---
    ("我今天去超市买了苹果", "我今天去超市买了香蕉", "modified", 0),
    ("Python 是一门很好的语言", "Python 是一门极好的语言", "modified", 0),
    ("这辆车的外观是红色的", "这辆车的外观是蓝色的", "modified", 0),
    ("如果你喜欢这首歌，请给我点赞转发", "如果你喜欢这首歌，记得分享给身边的朋友", "modified", 0),
    ("他昨天去了北京出差，明天下午就回来", "他昨天去了北京出差，估计下周才能回来", "modified", 0),
    ("人工智能改变了世界，带来了很多便利", "人工智能改变了世界，同时也引发了伦理争议", "modified", 1),
    ("他今天十分开心", "他今天非常高兴", "modified", 0),     # 危险：相似度 0.43
    ("这件衣服真的很贵", "这件衣裳价格不菲", "modified", 0),   # 危险：相似度 0.38
    ("我们必须立刻行动", "大家得马上动手", "modified", 0),     # 极度危险：相似度 0.13
    
    # --- 远距离模板句 (真实文档中最易引发误配的刺客, dist > 2) ---
    ("第三章 实施细则", "第七章 附则", "unrelated", 8),
    ("1. 姓名：张三", "5. 部门：技术部", "unrelated", 4),
    ("本条款自签署之日起生效。", "本协议自盖章之日起生效。", "unrelated", 15),
    ("甲方：北京科技有限公司", "乙方：上海商贸有限公司", "unrelated", 3),
    ("项目编号：2023-A-001", "项目编号：2024-B-002", "unrelated", 7),
    ("联系人：王经理，电话：13800000000", "联系人：李总，电话：13911111111", "unrelated", 5)
]

THRESHOLDS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 0.9]
POSITION_WINDOW = 2

def run_experiment():
    print("### 引入位置约束 (POSITION_WINDOW = 2) 后的全新扫参聚合表\n")
    print("| 阈值 | 配对对数 | 漏配(该合并没合并) | 误配(不该合并却合并) |")
    print("|---|---|---|---|")
    
    for th in THRESHOLDS:
        paired_count = 0
        misses = 0
        false_alarms = 0
        
        for old_txt, new_txt, exp, dist in DATASET:
            # 【核心逻辑】：如果物理距离超过窗口，直接视为 unrelated，不看相似度！
            if dist > POSITION_WINDOW:
                predicted = "unrelated"
            else:
                r = difflib.SequenceMatcher(None, old_txt, new_txt).ratio()
                predicted = "modified" if r >= th else "unrelated"
            
            if predicted == "modified":
                paired_count += 1
                
            if exp == "modified" and predicted == "unrelated":
                misses += 1
            elif exp == "unrelated" and predicted == "modified":
                false_alarms += 1
                
        print(f"| {th:.2f} | {paired_count} | {misses} | {false_alarms} |")

if __name__ == "__main__":
    run_experiment()