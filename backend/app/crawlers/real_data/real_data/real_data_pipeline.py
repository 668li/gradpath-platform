# -*- coding: utf-8 -*-
"""真实数据爬取 - 从考研帮获取真实文章并保存"""
import sys, json, time, os, urllib.request, re
sys.stdout.reconfigure(encoding='utf-8')

REAL_URLS = [
    ("这4个专业难到破防", "https://www.kaoyan.com/article/1/9370/b1e62fa61d2c467caeffce554046810f", "专业分析"),
    ("26考研如何判断学校是否难考", "https://www.kaoyan.com/article/1/9370/09823affe8384c3ea46729402ba911ce", "择校指南"),
    ("83个硕博点撤销学硕将成历史", "https://www.kaoyan.com/article/1/9370/fd76e22c078447d4b0acedd6f88ce5d4", "政策解读"),
    ("专硕没有学硕含金量高", "https://www.kaoyan.com/article/1/9370/80fafeafa6174ef380a40d61ca785bac", "专业分析"),
    ("教育部这类研究生再扩招", "https://www.kaoyan.com/article/1/9370/b6aeaaa197364aab8547694b331e112e", "政策解读"),
    ("考研初试阅卷潜规则大揭秘", "https://www.kaoyan.com/article/1/9370/cf06b61e51554497aee28b02628116d4", "考试技巧"),
    ("27考研全年备考规划大公开", "https://www.kaoyan.com/article/1/9370/1ed1389dd81c4eeb84e2cc446f42600e", "备考规划"),
    ("26考研人记好这8点踩坑总结", "https://www.kaoyan.com/article/1/9370/2a2e8182c7ef42758310a224d49fc68f", "经验分享"),
    ("二战三战是否告知复试导师", "https://www.kaoyan.com/article/1/9370/c96ce0448f524c619ae95a8f87dd4564", "复试经验"),
    ("双非研究生真的不好吗", "https://www.kaoyan.com/article/1/9370/694a0dd466624e8fb87f40f05f2a191d", "择校指南"),
    ("考研加点钝感力更容易上岸", "https://www.kaoyan.com/article/1/9370/f8c953e34573453c8f89f62eca26d3d0", "心态调整"),
    ("那些闷声赚大钱的小众专业", "https://www.kaoyan.com/article/1/3949/bfabefb205c445d5aa70d9ad7013d972", "专业分析"),
    ("背不完这5大专业要背太多", "https://www.kaoyan.com/article/1/3949/1214c7395daa4709ae0739484531fd4d", "专业分析"),
    ("考研热门城市前10名", "https://www.kaoyan.com/article/1/3949/02a7e74babe441ae92022c32b8cf833c", "择校指南"),
    ("这6大专业能跨考就业好", "https://www.kaoyan.com/article/1/3949/4743cd60a9034698a1763ac8a336adf6", "专业分析"),
    ("分数线较低适合捡漏考研院校", "https://www.kaoyan.com/article/1/3949/d16c859fbaf74e5aa7dd1e23d2d2d04a", "择校指南"),
    ("这些院校进面等于拟录取", "https://www.kaoyan.com/article/1/3949/aac56da0dfbe47c1b39993cd692db222", "复试经验"),
    ("最难调剂的5大专业第一名卷哭了", "https://www.kaoyan.com/article/1/3949/36977af94be04dca88a1c77887268004", "调剂经验"),
    ("暴跌70分报考这所211的有福了", "https://www.kaoyan.com/article/1/3949/eef381bb418c48baab4856117c1b86d6", "择校指南"),
    ("91校25考研复试分数线汇总", "https://www.kaoyan.com/article/1/3949/dbcb08a9dcae432f95c40a1c758d8c40", "分数线"),
    ("好多双非比985奖学金还高", "https://www.kaoyan.com/article/1/3949/796b5bbfdc1c4552a473aca3b7fd8e64", "择校指南"),
    ("考研真的越来越高考化了吗", "https://www.kaoyan.com/article/1/3946/562fcb93769a44cf88837626607d4555", "政策解读"),
    ("26考研如何选好专业和院校", "https://www.kaoyan.com/article/1/3946/8fd45abb7ecb43d1bfeb5054a24183a0", "择校指南"),
    ("考研10问扫除你的迷茫", "https://www.kaoyan.com/article/1/3946/6a1a9ccdae7c46b294db137a8e1175f9", "备考规划"),
    ("速看26考研7月详尽规划", "https://www.kaoyan.com/article/1/3946/bc1f7ea89a794198ba2d22709ebac357", "备考规划"),
    ("26考研英语如何学", "https://www.kaoyan.com/article/1/3946/b4fc12a7b6024480b5f6755cfeaa6b0d", "备考方法"),
    ("考研后悔行为大赏", "https://www.kaoyan.com/article/1/3946/7a36d92c55c6415eb102ee2f8e70b43f", "经验分享"),
    ("26考研风向标三大变化", "https://www.kaoyan.com/article/1/3946/d6e2a9c7106a4487b1b6a49af6dfc9bd", "政策解读"),
    ("选专业择校复习保姆级教程", "https://www.kaoyan.com/article/1/3946/7ba9774c17cf4914a6bdd66a56092bb3", "备考规划"),
    ("26考研避坑秘籍", "https://www.kaoyan.com/article/1/3946/166aaf87f1ec489f9707bc3101abd99d", "经验分享"),
    ("调剂新传中南大学到黑龙江大学", "https://www.kaoyan.com/adjust/5/5101/2032e22e44ae4628879921c7b980fdf5", "调剂经验"),
    ("调剂上岸河北传媒学院", "https://www.kaoyan.com/adjust/5/5101/eb67d98ae09a43db8d8d19285527782a", "调剂经验"),
    ("一志愿复试两次被刷后选择调剂", "https://www.kaoyan.com/adjust/5/5101/1160346c09fb43d6979f3d67d525cb7c", "调剂经验"),
    ("南中医到广东药科大学调剂", "https://www.kaoyan.com/adjust/5/5101/6b87de0128034c8d856a09db449fbb90", "调剂经验"),
    ("调剂211陕师大", "https://www.kaoyan.com/adjust/5/5101/240884d863d04f3db7f1f8ffebce0e46", "调剂经验"),
    ("预调剂系统今日开通", "https://www.kaoyan.com/adjust/1/9/39b5cf936b234b4e83a3335d99e21219", "调剂指南"),
    ("出分后这几件事一定要做", "https://www.kaoyan.com/adjust/1/9/e3c5ad5d50d7407cb50edacce1091a6b", "调剂指南"),
    ("调剂前这几个问题必须知道", "https://www.kaoyan.com/adjust/1/9/90ea5dff8831468dbb3a74bebc0427f4", "调剂指南"),
    ("怎样打破考研调剂信息差", "https://www.kaoyan.com/adjust/1/9/33caa5ccd30341b6bcb4ea4504641507", "调剂指南"),
    ("四类复试调剂黑名单院校速避雷", "https://www.kaoyan.com/adjust/1/9/336d2a3080054b838d4098624911c4ae", "调剂指南"),
    ("调剂去了双非到底要不要读", "https://www.kaoyan.com/adjust/1/9/94e0e7d2f67747919b2ee854c06323da", "调剂经验"),
]

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:3000]
    except:
        return ""

def main():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_articles.json")
    results = []
    for i, (title, url, cat) in enumerate(REAL_URLS):
        content = fetch(url)
        results.append({"title": title, "url": url, "category": cat, "source": "kaoyan.com", "content": content})
        print(f"[{i+1}/{len(REAL_URLS)}] {title} ({len(content)} chars)")
        time.sleep(0.3)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nTotal: {len(results)} real articles saved to {output_path}")

if __name__ == "__main__":
    main()
