import urllib3
import json

#お天気の情報を取得
def weather_infomation():
    http = urllib3.PoolManager()
    r = http.request('Get','http://weather.livedoor.com/forecast/webservice/json/v1?city=130010')
    r = json.loads(r._body)

    date = r['forecasts'][0]['date']
    weather = r['forecasts'][0]['telop']
    return date + "\n" + "東京のお天気は" + weather
