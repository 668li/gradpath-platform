import json
from datetime import datetime


class SaveToJSONPipeline:
    def open_spider(self, spider):
        self.file = open(f'output/{spider.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w')
        self.items = []

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        json.dump(self.items, self.file, ensure_ascii=False, indent=2)
        self.file.close()
