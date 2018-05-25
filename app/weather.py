import urllib3
import json

#お天気の情報を取得
def weather_information():
    http = urllib3.PoolManager()
    r = http.request('Get','http://weather.livedoor.com/forecast/webservice/json/v1?city=130010')
    r = json.loads(r._body)

    date = r['forecasts'][0]['dateLabel']
    weather = r['forecasts'][0]['telop']
    temp = r['forecasts'][0]['temperature']['max']['celsius']
    return date + "の東京の天気は" + weather + "\n" + "最高気温は" + temp + "度"
