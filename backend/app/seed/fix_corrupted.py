import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix entry 1: 概率论中随机变量的期望和方差怎么求？
old1 = '''        "answers": [
            ",
            "数学复习关键是打好基础，多做题多总结。推荐建立错题本，定期回顾易错知识点。"离散型期望：E(X)=sum(xi*pi)。连续型期望：E(X)=积分xf(x)dx。方差：D(X)=E(X^2)-[E(X)]^2。",
            "常用公式：E(aX+b)=aE(X)+b、D(aX+b)=a^2D(X)。独立时E(XY)=E(X)E(Y)、D(X+Y)=D(X)+D(Y)。",
            "常见分布的期望方差要记住：正态分布E(X)=mu、D(X)=sigma^2；泊松分布E(X)=D(X)=lambda。常考期望方差的计算。",
        ],'''

new1 = '''        "answers": [
            "离散型期望：E(X)=sum(xi*pi)。连续型期望：E(X)=积分xf(x)dx。方差：D(X)=E(X^2)-[E(X)]^2。",
            "常用公式：E(aX+b)=aE(X)+b、D(aX+b)=a^2D(X)。独立时E(XY)=E(X)E(Y)、D(X+Y)=D(X)+D(Y)。",
            "常见分布的期望方差要记住：正态分布E(X)=mu、D(X)=sigma^2；泊松分布E(X)=D(X)=lambda。常考期望方差的计算。",
        ],'''

content = content.replace(old1, new1, 1)

# Fix entry 2: 408 数据结构 KMP 算法 next 数组怎么
old2 = '''        "answers": [
            ",
            "建议结合王道辅导书和真题来复习，重点理解核心概念，多做练习题巩固。祝复习顺利！"next 数组记录每个位置前子串的最长相等前后缀长度。next[0]=-1，特殊处理。",
            "手动算法：从第二个字符开始，逐位比较当前字符与前缀匹配长度。匹配则长度+1，不匹配则回退。",
            "408 考 next 数组多考 nextval 数组的求法。记住 nextval 是 next 数组的优化版。",
        ],'''

new2 = '''        "answers": [
            "next 数组记录每个位置前子串的最长相等前后缀长度。next[0]=-1，特殊处理。",
            "手动算法：从第二个字符开始，逐位比较当前字符与前缀匹配长度。匹配则长度+1，不匹配则回退。",
            "408 考 next 数组多考 nextval 数组的求法。记住 nextval 是 next 数组的优化版。",
        ],'''

content = content.replace(old2, new2, 1)

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed 2 corrupted entries!")
