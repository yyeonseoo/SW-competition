"""
호환성을 위한 entry-point 래퍼 스크립트입니다.
실제 광운대 공지사항 수집 로직은 crawlers.kw_crawler 모듈에서 실행됩니다.
"""
from crawlers.kw_crawler import *
from crawlers.kw_crawler import main

if __name__ == "__main__":
    main()
