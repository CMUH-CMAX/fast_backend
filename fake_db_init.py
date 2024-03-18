
SYMPTOMS = [
    {
      "name": '發燒',
      "academic": 'pyrexia',
      "visit": 3579
    },
    {
      "name": '紅疹',
      "academic": 'rash',
      "visit": 1324
    },
    {
      "name": '下腹疼痛',
      "academic": 'abdominal-pain',
      "visit": 1223
    },
    {
      "name": '頭暈',
      "academic": 'vertigo',
      "visit": 1139
    },
    {
      "name": '畏寒',
      "academic": 'rigor',
      "visit": 1024
    },
    {
      "name": '腹瀉',
      "academic": 'diarrhea',
      "visit": 1591
    },
    {
      "name": '皮膚過敏',
      "academic": 'allergic-dermatitis',
      "visit": 1234
    },
    {
      "name": '流鼻水',
      "academic": 'rhinorrhea',
      "visit": 1842
    },
    {
      "name": '打噴嚏',
      "academic": 'sneeze',
      "visit": 924
    },
    {
      "name": '偏頭痛',
      "academic": 'migraine',
      "visit": 434
    },
    {
      "name": '牙齦紅腫',
      "academic": 'gingivitis',
      "visit": 124
    },
    {
      "name": '口臭',
      "academic": 'halitosis',
      "visit": 324
    },
]
BIG_DICK_MAN_NEWS = [{
  "class": "warning",
  "user_id": 1,
  "title": "驚爆！！！大屌男出沒中央大學！",
  "content": "城市驚現超級大屌男，引起市民熱議和媒體關注，成為社交媒體熱門話題。",
  "update_at": "2024/03/18 22:47:14",
  "create_at": "2024/03/18 22:47:14"
}]
def init_all(db):
    for s in SYMPTOMS:
        db.create('symptoms', s)
    for every_big_dick_man in BIG_DICK_MAN_NEWS:
        db.create("bulletins", every_big_dick_man)