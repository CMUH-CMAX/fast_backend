OLD_SYMPTOMS = [
    {'name': '紅疹', 'visit': 1324},
    {'name': '發燒', 'visit': 3579},
    {'name': '下腹疼痛', 'visit': 1323},
    {'name': '頭暈', 'visit': 1296},
    {'name': '畏寒', 'visit': 1268},
    {'name': '腹瀉', 'visit': 1273},
    {'name': '皮膚過敏', 'visit': 1231},
    {'name': '流鼻水', 'visit': 1222},
    {'name': '打噴嚏', 'visit': 1123},
    {'name': '牙齦紅腫', 'visit': 991},
    {'name': '口臭', 'visit': 688},
]

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

def init_all(db):
    for s in SYMPTOMS:
        db.create('symptoms', s)
