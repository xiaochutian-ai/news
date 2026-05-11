from datetime import datetime

from app.sources.cctv import (
    CCTVAdapter,
    parse_cctv_channel_page,
    parse_cctv_feed,
    parse_cctv_rss,
)
from app.sources.people_daily import parse_people_daily_index
from app.sources.registry import build_source_adapters, list_available_sources
from app.sources.xinhua import XinhuaAdapter, parse_xinhua_channel_page, parse_xinhua_rss
from app.config import AppConfig


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


def test_parse_cctv_channel_page_extracts_current_links() -> None:
    html = """
    <html><body>
      <a href="https://news.cctv.com/2026/05/10/ARTI123.shtml">社区食堂更方便了</a>
      <a href="https://news.cctv.com/2026/05/10/ARTI456.shtml">稳就业政策持续加力</a>
      <a href="https://news.cctv.com/2026/05/11/ARTI789.shtml">次日文章</a>
    </body></html>
    """

    links = parse_cctv_channel_page(html, source_day_compact="20260510")

    assert links == [
        ("社区食堂更方便了", "https://news.cctv.com/2026/05/10/ARTI123.shtml"),
        ("稳就业政策持续加力", "https://news.cctv.com/2026/05/10/ARTI456.shtml"),
    ]


def test_parse_cctv_feed_extracts_current_links() -> None:
    payload = """news({"data":{"list":[
        {"title":"全面扩围 我国加快建设一刻钟便民生活圈","url":"https://news.cctv.com/2026/05/10/ARTIht6BUNpPGJerfHAfuHgu260510.shtml"},
        {"title":"次日文章","url":"https://news.cctv.com/2026/05/11/ARTI999.shtml"}
    ]}})"""

    links = parse_cctv_feed(payload, source_day_compact="20260510")

    assert links == [
        ("全面扩围 我国加快建设一刻钟便民生活圈", "https://news.cctv.com/2026/05/10/ARTIht6BUNpPGJerfHAfuHgu260510.shtml"),
    ]


def test_parse_xinhua_rss_extracts_articles() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title><![CDATA[提高青年求职能力 就业实训密集推出]]></title>
          <link>http://www.news.cn/local/2026-05/10/c_123456.htm</link>
          <pubDate>Sun, 10 May 2026 12:30:00 GMT</pubDate>
          <description><![CDATA[
            <a href="http://www.news.cn/local/2026-05/10/c_123456.htm">围绕就业创业推出新举措。</a>
          ]]></description>
        </item>
      </channel>
    </rss>
    """

    articles = parse_xinhua_rss(xml, source="xinhua_local")

    assert len(articles) == 1
    assert articles[0].source == "xinhua"
    assert articles[0].title == "提高青年求职能力 就业实训密集推出"
    assert articles[0].url == "http://www.news.cn/local/2026-05/10/c_123456.htm"
    assert articles[0].summary == "围绕就业创业推出新举措。"
    assert isinstance(articles[0].published_at, datetime)


def test_parse_xinhua_channel_page_extracts_current_links() -> None:
    html = """
    <html><body>
      <a href="https://www.news.cn/politics/20260510/abc123/c.html">养老服务再升级</a>
      <a href="https://www.news.cn/local/20260510/def456/c.html">社区卫生服务暖民心</a>
      <a href="https://www.news.cn/world/20260510/zzz999/c.html">国际新闻</a>
      <a href="https://www.news.cn/politics/20260511/ghi789/c.html">次日文章</a>
    </body></html>
    """

    links = parse_xinhua_channel_page(html, source_day_compact="20260510")

    assert links == [
        ("养老服务再升级", "https://www.news.cn/politics/20260510/abc123/c.html"),
        ("社区卫生服务暖民心", "https://www.news.cn/local/20260510/def456/c.html"),
    ]


def test_parse_xinhua_rss_falls_back_to_link_date_when_pubdate_missing() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title><![CDATA[办好共享用电这件民生实事]]></title>
          <link>http://www.news.cn/local/2026-05/10/c_654321.htm</link>
          <description><![CDATA[民生服务进一步下沉。]]></description>
        </item>
      </channel>
    </rss>
    """

    articles = parse_xinhua_rss(xml, source="xinhua_local")

    assert len(articles) == 1
    assert articles[0].published_at == datetime(2026, 5, 10, 21, 0, 0)


def test_cctv_adapter_uses_public_feed_links(monkeypatch) -> None:
    adapter = CCTVAdapter()
    feed_text = """news({"data":{"list":[
        {"title":"社区食堂更方便了","url":"https://news.cctv.com/2026/05/10/ARTI123.shtml"}
    ]}})"""
    detail_html = "<html><body><p>社区食堂让老年人吃饭更方便。</p></body></html>"

    def fake_get_text(url: str, *, encoding: str | None = None) -> str:
        if url in adapter.feed_urls:
            return feed_text
        return detail_html

    monkeypatch.setattr(adapter, "get_text", fake_get_text)

    articles = adapter.fetch("20260510")

    assert len(articles) == 1
    assert articles[0].summary == "社区食堂让老年人吃饭更方便。"


def test_xinhua_adapter_uses_channel_page_links(monkeypatch) -> None:
    adapter = XinhuaAdapter()
    channel_html = '<a href="https://www.news.cn/local/20260510/def456/c.html">社区卫生服务暖民心</a>'
    detail_html = "<html><body><p>基层医疗服务进一步下沉。</p></body></html>"

    def fake_get_text(url: str, *, encoding: str | None = None) -> str:
        if url in adapter.channel_urls:
            return channel_html
        return detail_html

    monkeypatch.setattr(adapter, "get_text", fake_get_text)

    articles = adapter.fetch("20260510")

    assert len(articles) == 1
    assert articles[0].summary == "基层医疗服务进一步下沉。"


def test_build_source_adapters_uses_selected_sources() -> None:
    config = AppConfig()

    adapters = build_source_adapters(config, selected_sources=["people_daily", "xinhua"])

    assert [adapter.source_name for adapter in adapters] == ["people_daily", "xinhua"]


def test_list_available_sources_includes_xinhua() -> None:
    keys = [item["key"] for item in list_available_sources()]

    assert keys == ["people_daily", "cctv", "xinhua"]
