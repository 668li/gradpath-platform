#!/usr/bin/env python3
"""测试所有数据源可达性和解析效果"""
import httpx
import json
import time
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# 按域分类测试
SOURCES = {
    # 考研
    "yanzhao": ("研招网", "https://yz.chsi.com.cn/kyzx/kydt/"),
    "kaoyan": ("考研帮", "https://www.kaoyan.com/experience/"),
    "eol_kaoyan": ("EOL考研", "https://kaoyan.eol.cn/"),
    
    # 考公
    "offcn": ("中公教育", "https://www.offcn.com/gwy/"),
    "huatu": ("华图教育", "https://www.huatu.com/guojia/"),
    "fenbi": ("粉笔", "https://www.fenbi.com/page/guokao"),
    "hqwx": ("环球网校", "https://www.hqwx.com/gjgwy-kaoshi/"),
    
    # 就业
    "51job": ("前程无忧", "https://www.51job.com/"),
    "boss": ("BOSS直聘", "https://www.zhipin.com/"),
    
    # 新闻/教育
    "sina_edu": ("新浪教育", "https://edu.sina.com.cn/"),
    "xinhua_edu": ("新华网教育", "http://www.xinhuanet.com/edu/"),
    "eol": ("中国教育在线", "https://www.eol.cn/kaoyan/"),
    "163_edu": ("网易教育", "https://edu.163.com/"),
    "sohu_edu": ("搜狐教育", "https://learning.sohu.com/"),
    
    # 培训
    "mofangge": ("魔方格", "https://www.mofangge.com/"),
}

def test_source(key, name, url):
    """测试单个数据源"""
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            soup = BeautifulSoup(r.text, 'lxml')
            
            # 统计链接数
            links = soup.select('a[href]')
            article_links = [a for a in links if len(a.get_text(strip=True)) > 10]
            
            return {
                "key": key,
                "name": name,
                "status": r.status_code,
                "size": len(r.text),
                "links": len(links),
                "articles": len(article_links),
                "sample": [a.get_text(strip=True)[:40] for a in article_links[:3]],
            }
    except Exception as e:
        return {
            "key": key,
            "name": name,
            "status": "ERROR",
            "error": str(e)[:60],
        }

if __name__ == "__main__":
    print("GradPath 数据源可达性测试")
    print("=" * 60)
    
    results = []
    for key, (name, url) in SOURCES.items():
        result = test_source(key, name, url)
        results.append(result)
        
        if result["status"] == "ERROR":
            print(f"  ❌ {name}: {result.get('error', '')}")
        elif result["status"] == 200:
            print(f"  ✅ {name}: {result['status']} | {result['size']//1024}KB | {result['articles']}篇文章")
            if result.get("sample"):
                for s in result["sample"][:2]:
                    print(f"     → {s}")
        else:
            print(f"  ⚠️ {name}: HTTP {result['status']}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("汇总:")
    working = [r for r in results if r["status"] == 200]
    failed = [r for r in results if r["status"] == "ERROR"]
    print(f"  可用: {len(working)}/{len(results)}")
    print(f"  失败: {len(failed)}")
    for f in failed:
        print(f"    - {f['name']}: {f.get('error', '')[:50]}")
