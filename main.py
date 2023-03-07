from fastapi import FastAPI
import time
import requests
import json
import datetime as dt


app = FastAPI()

# origins = [
#     "https://flow-ashy.vercel.app",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


def chngdt(string):
    if string == "Jan":
        return "01"
    elif string == "Feb":
        return "02"
    elif string == "Mar":
        return "03"
    elif string == "Apr":
        return "04"
    elif string == "May":
        return "05"
    elif string == "Jun":
        return "06"
    elif string == "Jul":
        return "07"
    elif string == "Aug":
        return "08"
    elif string == "Sep":
        return "09"
    elif string == "Oct":
        return "10"
    elif string == "Nov":
        return "11"
    elif string == "Dec":
        return "12"


class DataProvider(object):
    def __init__(self):
        self.last_update = None
        self.data = None

    @staticmethod
    def getUrl(source):
        year_in_ms = 365 * 24 * 60 * 60 * 1000
        avg_200_correction = 200 * 24 * 60 * 60 * 1000

        eex_start_timestamp = time.time() * 1000 - year_in_ms - avg_200_correction
        eex_end_timestamp = time.time() * 1000

        source_urls = {
            "eex": f"https://api.awattar.de/v1/marketdata/?start={eex_start_timestamp}&end={eex_end_timestamp}"
        }

        return source_urls[source]

    @staticmethod
    def api(source):
        api_url = DataProvider.getUrl(source)
        raw_data = dict(json.loads(requests.get(api_url).text))

        data = raw_data["data"]
        data = data[::-1]

        all_prices = [x["marketprice"] for x in data]
        alltime_avg = sum(all_prices) / len(all_prices)
        print("alltime avg", alltime_avg)

        #### GROUPING DATA
        current_hour = dt.datetime.now().hour

        data_today = data[: current_hour + 1]
        data_this_day = [0] * 24

        for i in range(24):
            if i <= current_hour:
                hour_price = data_today[i]["marketprice"]

                key = current_hour - i
                data_this_day[key] = {
                    "Time": str(key) + ":00",
                    "Spot": hour_price,
                }
            else:
                key = 24 + current_hour - i
                data_this_day[key] = {
                    "Time": str(key) + ":00",
                    "Spot": None,
                }

        data_excl_today = data[current_hour:]

        proc_data = {}

        # construct new data
        for i in range(len(data_excl_today)):
            elem = data_excl_today[i]
            date = dt.datetime.fromtimestamp(elem["start_timestamp"] / 1000).strftime(
                "%d-%m-%y"
            )

            proc_data[date] = []

        for i in range(len(data_excl_today)):
            elem = data_excl_today[i]
            date = dt.datetime.fromtimestamp(elem["start_timestamp"] / 1000).strftime(
                "%d-%m-%y"
            )

            proc_data[date].append(elem["marketprice"])

            result = {}

            final = []

        for k in proc_data.keys():
            result[k] = {"Spot": sum(proc_data[k]) / len(proc_data[k])}

        # avg of last 200 days
        for k in range(365):
            key = list(proc_data.keys())[k]

            avg_200 = 0
            for x in range(200):
                x_key = list(proc_data.keys())[k + x]
                x_price = result[x_key]["Spot"]

                avg_200 += x_price

            avg_200 = avg_200 / 200

            avg_50 = 0
            for x in range(50):
                x_key = list(proc_data.keys())[k + x]
                x_price = result[x_key]["Spot"]
                avg_50 += x_price

            avg_50 = avg_50 / 50

            final.append(
                {
                    "date": key,
                    "Spot": round(result[key]["Spot"], 4),
                    "Avg 50": round(avg_50, 4),
                    "Avg 200": round(avg_200, 4),
                }
            )

        final = final[::-1]

        # CALC STATS
        def get_stats(data, value="", lookback=0):
            delta = data[len(data) - 1][value] / data[len(data) - 1 - lookback][value]
            perc = round((delta - 1) * 100, 2)
            valind = True
            if perc < 0:
                valind = False

            return {"perc": perc, "valind": valind}

        def get_day_stats(data, value="", lookback=0):
            delta = data[len(data) - 1][value] / data[len(data) - 1 - lookback][value]
            perc = round((delta - 1) * 100, 2)
            valind = True
            if perc < 0:
                valind = False

            avg_today = sum([x[value] for x in data]) / len(data)

            return {"perc": perc, "valind": valind, "avg": avg_today}

        # Assemble response
        stats_365 = {
            "Spot": {
                "Past 7 days": get_stats(final, value="Spot", lookback=7),
                "Past 30 days": get_stats(final, value="Spot", lookback=30),
                "YoY": get_stats(final, value="Spot", lookback=364),
            },
            "Avg 50": {
                "Past 7 days": get_stats(final, value="Avg 50", lookback=6),
                "Past 30 days": get_stats(final, value="Avg 50", lookback=29),
                "YoY": get_stats(final, value="Avg 50", lookback=364),
            },
            "Avg 200": {
                "Past 7 days": get_stats(final, value="Avg 200", lookback=6),
                "Past 30 days": get_stats(final, value="Avg 200", lookback=29),
                "YoY": get_stats(final, value="Avg 200", lookback=364),
            },
        }

        stats_today = {
            "Spot": {
                "Today": get_day_stats(
                    [x for x in data_this_day if x["Spot"] is not None],
                    value="Spot",
                    lookback=dt.datetime.now().hour,
                ),
            },
        }

        reponse = {
            "last_365": {"data": final, "stats": stats_365},
            "today": {"data": data_this_day, "stats": stats_today},
        }
        return reponse


class EexData(object):
    def __init__(self):
        self.last_update = None
        self.data = None


eexdata = EexData()

dataProv = DataProvider()


@app.get("/eexdata")
async def root():
    if eexdata.last_update is None and eexdata.data is None:
        eexdata.data = DataProvider.api("eex")
        eexdata.last_update = dt.datetime.now().hour

    elif eexdata.last_update is not None and eexdata.data is not None:
        if (eexdata.last_update - dt.datetime.now().hour) == 1:
            eexdata.data = DataProvider.api("eex")
            eexdata.last_update = dt.datetime.now().hour
        else:
            print("cached")
            eexdata.data = DataProvider.api("eex")
            eexdata.last_update = dt.datetime.now().hour

    return eexdata.data


@app.get("/eua")
async def root():
    header = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "de-DE,de;q=0.9",
        "Connection": "keep-alive",
        "Cookie": "BIGipServerice.com=1191587082.30986.0000",
        "Host": "www.theice.com",
        # "If-Modified-Since": "Thu, 29 Sep 2022 20:50:05 GMT",
        "Referer": "https://www.theice.com/products/18709519/EUA-Daily-Future/data?marketId=400431&span=3",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    }

    url = "https://www.theice.com/marketdata/DelayedMarkets.shtml?getHistoricalChartDataAsJson=&marketId=400431&historicalSpan=3"

    data = dict(json.loads(requests.get(url).text))["bars"]

    data = data[::-1]

    proc_data = {}

    # construct new data
    for i in range(len(data)):
        elem = data[i]
        date = elem[0][4:].replace(" 00:00:00", "")
        date = date.split(" ")
        date = ("-").join([date[1], chngdt(date[0]), date[2]])

        proc_data[date] = []

    for i in range(len(data)):
        elem = data[i]
        date = elem[0][4:].replace(" 00:00:00", "")
        date = date.split(" ")
        date = ("-").join([date[1], chngdt(date[0]), date[2]])

        proc_data[date].append(elem[1])

    result = {}

    final = []

    for k in proc_data.keys():
        result[k] = {"Spot": proc_data[k][0]}

    # avg of last 200 days
    for k in range(365):
        key = list(proc_data.keys())[k]

        avg_200 = 0
        for x in range(len(proc_data) - 365):

            x_key = list(proc_data.keys())[k + x]
            x_price = result[x_key]["Spot"]

            avg_200 += x_price

        avg_200 = avg_200 / (len(proc_data) - 365)

        avg_50 = 0
        for x in range(50):
            x_key = list(proc_data.keys())[k + x]
            x_price = result[x_key]["Spot"]
            avg_50 += x_price

        avg_50 = avg_50 / 50

        final.append(
            {
                "date": key,
                "Spot": round(result[key]["Spot"], 4),
                "Avg 50": round(avg_50, 4),
                "Avg 200": round(avg_200, 4),
            }
        )

    final = final[::-1]

    # final = {"last_365": final, "today": data_this_day}

    return final


@app.get("/ttf")
async def root():
    header = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "de-DE,de;q=0.9",
        "Connection": "keep-alive",
        "Cookie": "BIGipServerice.com=1191587082.30986.0000",
        "Host": "www.theice.com",
        # "If-Modified-Since": "Thu, 29 Sep 2022 20:50:05 GMT",
        "Referer": "https://www.theice.com/products/18709519/EUA-Daily-Future/data?marketId=400431&span=3",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    }

    url = "https://www.theice.com/marketdata/DelayedMarkets.shtml?getHistoricalChartDataAsJson=&marketId=5439161&historicalSpan=3"

    data = dict(json.loads(requests.get(url).text))["bars"]

    result = []

    for i in range(len(data)):
        elem = data[i]
        date_time = elem[0][4:]

        price = elem[1]

        month = chngdt(date_time[:3].strip())

        new_date_time = month + " " + date_time[4:]
        timestamp = dt.datetime.strptime(new_date_time, "%m %d %H:%M:%S %Y")
        time = timestamp.time()

        item = {"date": str(time), "price": price, "yindex": i}

        result.append(item)

    return result
