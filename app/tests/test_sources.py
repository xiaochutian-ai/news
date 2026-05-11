from datetime import datetime

from app.sources.cctv import parse_cctv_rss
from app.sources.people_daily import parse_people_daily_index


def test_parse_people_daily_index_extracts_articles() -> None:
    html = """
    <html><body>
      <a href="/rmrb/20260510/1/abc123">各地办理“全国通办”68.2万件</a>
      <a href="/rmrb/20260510/1/def456">网上商品和服务零售额同比增8%</a>
    </body></html>
    """

    articles = parse_people_daily_index(html, article_date="2026-05-10")

    assert len(articles) == 2
    assert articles[0].title == "各地办理“全国通办”68.2万件"
    assert articles[0].url == "https://data.people.com.cn/rmrb/20260510/1/abc123"


def test_parse_cctv_rss_extracts_items() -> None:
    xml = """<?xml version="1.0" encoding="GBK"?>
    <rss version="2.0">
      <channel>
        <item>
          <title><![CDATA[多地发放消费券带动假日消费]]></title>
          <link>https://news.cctv.com/2026/05/10/ARTI123.shtml</link>
          <pubDate>Sat, 10 May 2026 20:05:00 GMT</pubDate>
          <description><![CDATA[群众消费获得直接带动。]]></description>
        </item>
      </channel>
    </rss>
    """

    articles = parse_cctv_rss(xml)

    assert len(articles) == 1
    assert articles[0].title == "多地发放消费券带动假日消费"
    assert isinstance(articles[0].published_at, datetime)
