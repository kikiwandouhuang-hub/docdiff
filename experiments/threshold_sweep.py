import difflib

DATASET = [
    ("我今天去超市买了苹果", "我今天去超市买了香蕉", "modified"),
    ("Python 是一门很好的语言", "Python 是一门极好的语言", "modified"),
    ("这辆车的外观是红色的", "这辆车的外观是蓝色的", "modified"),
    ("如果你喜欢这首歌，请给我点赞转发", "如果你喜欢这首歌，记得分享给身边的朋友", "modified"),
    ("他昨天去了北京出差，明天下午就回来", "他昨天去了北京出差，估计下周才能回来", "modified"),
    ("人工智能改变了世界，带来了很多便利", "人工智能改变了世界，同时也引发了伦理争议", "modified"),
    ("他今天十分开心", "他今天非常高兴", "modified"),
    ("这件衣服真的很贵", "这件衣裳价格不菲", "modified"),
    ("我们必须立刻行动", "大家得马上动手", "modified"),
    
    ("第三章 实施细则", "第七章 附则", "unrelated"),
    ("1. 姓名：张三", "5. 部门：技术部", "unrelated"),
    ("本条款自签署之日起生效。", "本协议自盖章之日起生效。", "unrelated"),
    ("甲方：北京科技有限公司", "乙方：上海商贸有限公司", "unrelated"),
    ("项目编号：2023-A-001", "项目编号：2024-B-002", "unrelated"),
    ("联系人：王经理，电话：13800000000", "联系人：李总，电话：13911111111", "unrelated")
]

THRESHOLDS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 0.9]

def run_experiment():
    details = []
    for old_txt, new_txt, expected in DATASET:
        r = difflib.SequenceMatcher(None, old_txt, new_txt).ratio()
        details.append((r, expected, old_txt, new_txt))
    
    details.sort(key=lambda x: x[0], reverse=True)
    
    print("### 1. 逐对明细表 (按 Ratio 降序)\n")
    print("| Ratio | 期望 | 旧文本前20字 | 新文本前20字 |")
    print("|---|---|---|---|")
    for r, exp, old_txt, new_txt in details:
        print(f"| {r:.2f} | {exp} | {old_txt[:20]} | {new_txt[:20]} |")
        
    print("\n### 2. 扫参聚合表\n")
    print("| 阈值 | 配对对数 | 漏配(该合并没合并) | 误配(不该合并却合并) |")
    print("|---|---|---|---|")
    
    for th in THRESHOLDS:
        paired_count = 0
        misses = 0
        false_alarms = 0
        
        for r, exp, _, _ in details:
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