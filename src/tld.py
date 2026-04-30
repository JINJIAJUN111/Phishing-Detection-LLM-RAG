import tldextract

# 禁用在线更新PSL，避免首次运行卡住（特别是校园网/无外网环境）
EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=None)