"""
호환성을 위한 entry-point 래퍼 스크립트입니다.
실제 링커리어 수집 로직은 crawlers.linkareer_crawler 모듈에서 실행됩니다.
"""
from crawlers.linkareer_crawler import *
from crawlers.linkareer_crawler import main

if __name__ == "__main__":
    main()