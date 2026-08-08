from difflib import SequenceMatcher

# 样本结构: (old, new, expect, dist)
SAMPLES = [
    # --- 1-9 组: 就地编辑，不移动 (dist=0) ---
    ("我今天去超市买了苹果", "我今天去超市买了香蕉", "modified", 0),
    ("Python 是一门很好的语言", "Python 是一门极好的语言", "modified", 0),
    ("这辆车的外观是红色的", "这辆车的外观是蓝色的", "modified", 0),
    ("如果你喜欢这首歌，请给我点赞转发", "如果你喜欢这首歌，记得分享给身边的朋友", "modified", 0),
    ("他昨天去了北京出差，明天下午就回来", "他昨天去了北京出差，估计下周才能回来", "modified", 0),
    ("人工智能改变了世界，带来了很多便利", "人工智能改变了世界，同时也引发了伦理争议", "modified", 0),
    ("他今天十分开心", "他今天非常高兴", "modified", 0),
    ("这件衣服真的很贵", "这件衣裳价格不菲", "modified", 0),
    ("我们必须立刻行动", "大家得马上动手", "modified", 0),

    # --- 新增 2 组: 修改 + 小幅移动 (dist > 2，注定会被位置约束误杀的代价) ---
    ("他昨天去了北京出差，明天下午就回来", "他昨天去了北京出差，估计下周才能回来", "modified", 3),
    ("这件衣服真的很贵", "这件衣裳价格不菲", "modified", 4),

    # --- A-F 组: unrelated 模板句 (依据真实文档结构填入真实物理距离) ---
    ("项目编号：2023-A-001", "项目编号：2024-B-002", "unrelated", 5),  # 不同章节的编号字段
    ("本条款自签署之日起生效", "本协议自盖章之日起生效", "unrelated", 2),  # 相邻条款
    ("第三章 实施细则", "第七章 附则", "unrelated", 4),                 # 章标题之间隔着正文
    ("甲方：北京科技有限公司", "乙方：上海商贸有限公司", "unrelated", 1),   # 合同抬头，紧挨着
    ("联系人：王经理，电话：13800000000", "联系人：李总，电话：13911111111", "unrelated", 1), # 相邻字段
    ("1. 姓名：张三", "5. 部门：技术部", "unrelated", 1)                 # 相邻列表项
]

POSITION_WINDOW = 2

def judge(old, new, dist, threshold, use_position):
    """返回 True = 判为 modified(配对)"""
    sim = SequenceMatcher(None, old, new).ratio()
    # 硬拦截，和 refine.py 里的语义保持一致
    if use_position and dist > POSITION_WINDOW:
        return False
    return sim >= threshold

def run(use_position):
    """跑一组配置,返回 {阈值: (漏配, 误配)}"""
    results = {}
    for th in [0.3, 0.4, 0.5, 0.55, 0.6, 0.7, 0.8]:
        misses = 0
        false_alarms = 0
        for old, new, expect, dist in SAMPLES:
            is_match = judge(old, new, dist, th, use_position)
            
            # 漏配 = expect==modified 但 judge 返回 False
            if expect == "modified" and not is_match:
                misses += 1
            # 误配 = expect==unrelated 但 judge 返回 True
            elif expect == "unrelated" and is_match:
                false_alarms += 1
                
        results[th] = (misses, false_alarms)
    return results

if __name__ == "__main__":
    res_no_pos = run(use_position=False)
    res_pos = run(use_position=True)
    
    print("### 阈值扫参实验对照表 (并排版)\n")
    print("| 阈值 | 无约束 漏/误 | 有约束 漏/误 | 误配减少 | 漏配代价 |")
    print("|------|--------------|--------------|----------|----------|")
    
    for th in [0.3, 0.4, 0.5, 0.55, 0.6, 0.7, 0.8]:
        miss_no, false_no = res_no_pos[th]
        miss_pos, false_pos = res_pos[th]
        
        # 计算差值：负数代表减少（优化），正数代表增加（代价）
        false_diff = false_pos - false_no
        miss_diff = miss_pos - miss_no
        
        # 格式化输出，保持对齐，差值强制显示 +/- 符号
        print(f"| {th:.2f} |    {miss_no:>2} / {false_no:<2}  |    {miss_pos:>2} / {false_pos:<2}  |    {false_diff:>4}  |    {miss_diff:>+4}  |")