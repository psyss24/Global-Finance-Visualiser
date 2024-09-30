from ctypes import *
import yfinance as yf
import requests
from lxml import html
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, 'backend_library.so')
lib = cdll.LoadLibrary(lib_path)

#setup c structs
class PriceIndexData(Structure):
    _fields_ = [
        ("date", c_char * 11),
        ("value", c_double)
    ]

class url_mem(Structure):
    _fields_ = [("memory", POINTER(c_char)),
                ("size", c_size_t)]

class StockHistoricalData(Structure):
    _fields_ = [
        ("date", c_char * 11),
        ("open", c_double),
        ("high", c_double),
        ("low", c_double),
        ("close", c_double),
        ("volume", c_double)
    ]

class HistoricalData(Structure):
    _fields_ = [("rates", POINTER(c_double)),
                ("dates", POINTER(c_char_p)),
                ("size", c_int)]

class EconomicData(Structure):
    _fields_ = [("year", c_char * 5),
                ("value", c_double)]


class EconomicData(Structure):
    _fields_ = [("year", c_char * 5),
                ("value", c_double)]

class InterestRateData(Structure):
    _fields_ = [("date", c_char * 11),
                ("value", c_double)]

#setup c functions

lib.get_price_index_data.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p, POINTER(c_int)]
lib.get_price_index_data.restype = POINTER(PriceIndexData)
lib.convert_currency.argtypes = [c_char_p, c_char_p, c_double]
lib.convert_currency.restype = c_double

lib.get_supported_currencies.argtypes = [c_int]
lib.get_supported_currencies.restype = c_char_p

lib.get_supported_exchanges.argtypes = []
lib.get_supported_exchanges.restype = POINTER(c_char_p)

lib.fetch_data.argtypes = [c_char_p, POINTER(url_mem)]
lib.fetch_data.restype = c_int
lib.parse_html.argtypes = [c_char_p, c_char_p, POINTER(POINTER(c_char_p)), POINTER(c_int)]
lib.parse_html.restype = None
lib.free_tickers.argtypes = [POINTER(c_char_p), c_int]
lib.free_tickers.restype = None
lib.free_memory.argtypes = [c_void_p]
lib.free_memory.restype = None

lib.fetch_stock_historical_data.argtypes = [c_char_p, c_char_p, POINTER(c_int)]
lib.fetch_stock_historical_data.restype = POINTER(StockHistoricalData)


lib.get_economic_data.argtypes = [c_char_p, c_char_p, c_char_p, c_char_p, POINTER(c_int)]
lib.get_economic_data.restype = POINTER(EconomicData)

lib.get_interest_rate_data.argtypes = [c_char_p, c_char_p, c_char_p, POINTER(c_int)]
lib.get_interest_rate_data.restype = POINTER(InterestRateData)


lib.fetch_historical_data.argtypes = [c_char_p, c_char_p, c_char_p]
lib.fetch_historical_data.restype = POINTER(HistoricalData)

lib.free_historical_data.argtypes = [POINTER(HistoricalData)]
lib.free_historical_data.restype = None

def get_price_index_data(indicator, country_code, start_year, end_year):
    # setup arguments
    indicator = indicator.encode('utf-8')
    country_code = country_code.encode('utf-8')
    start_year = start_year.encode('utf-8')
    end_year = end_year.encode('utf-8')
    data_count = c_int()

    # get interest rate data
    data_ptr = lib.get_price_index_data(indicator, country_code, start_year, end_year, byref(data_count))
    
    if not data_ptr:
        print("Error fetching price index data")
        return []

    # convert data to python list
    data_list = []
    for i in range(data_count.value):
        data = data_ptr[i]
       
        date = data.date.decode('utf-8') + "-01"
        data_list.append({
            "date": date,
            "value": data.value
        })

    
    lib.free_memory(data_ptr)

    return data_list

import yfinance as yf
from requests.exceptions import HTTPError

def get_stock_name(symbol):
    try:
        stock = yf.Ticker(symbol)
        stock_info = stock.info
        
        # check  'shortName' is available
        stock_name = stock_info.get('shortName')
        
        if stock_name:
            return stock_name
        else:
            # if not, get fast_info if available
            fast_info = stock.fast_info
            return fast_info.get('shortName', 'Unknown Stock')
    except HTTPError as http_err:
        if http_err.response.status_code == 401:
            print(f"Unauthorized access for symbol {symbol}: {http_err}")
            return 'Unauthorized Access'
        else:
            print(f"HTTP error occurred for symbol {symbol}: {http_err}")
            return 'Unknown Stock'
    except Exception as e:
        print(f"Error fetching stock name for symbol {symbol}: {e}")
        return 'Unknown Stock'

def fetch_stock_data(symbol, period):
    data_count = c_int()
    symbol_bytes = symbol.encode('utf-8')
    period_bytes = period.encode('utf-8')
    data_ptr = lib.fetch_stock_historical_data(symbol_bytes, period_bytes, byref(data_count))
    if not data_ptr:
        print("Error fetching historical data")
        return []

    data_list = []
    for i in range(data_count.value):
        data = data_ptr[i]
        try:
            date = data.date.decode('utf-8', errors='ignore')  # Handle decoding errors
        except UnicodeDecodeError:
            print(f"Error decoding date for record {i}")
            continue
        
        data_list.append({
            "date": date,
            "open": round(data.open, 4),   
            "high": round(data.high, 4),   
            "low": round(data.low, 4),     
            "close": round(data.close, 4), 
            "volume": data.volume
        })

    return data_list

# eod do not offer data on compostite indices, so we will use yfinance  
def fetch_historical_index_data(index, date_range, interval):
    index_map = {
        "FTSE 100": "^FTSE",
        "NASDAQ 100": "^NDX",
        "S&P 500": "^GSPC",
        "Dow Jones": "^DJI",
        "DAX": "^GDAXI"
    }

    index_ticker = index_map.get(index)
    if not index_ticker:
        print(f"Error: Invalid index name '{index}'")
        return []

    valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    if date_range not in valid_periods:
        print(f"Error: Invalid period '{date_range}', must be one of {valid_periods}")
        return []

    try:
        ticker = yf.Ticker(index_ticker)
        hist = ticker.history(period=date_range, interval=interval)
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return []

    data_list = []
    for date, row in hist.iterrows():
        data_list.append({
            "date": date.strftime('%Y-%m-%d'),
            "open": round(row['Open'], 2),
            "high": round(row['High'], 2),
            "low": round(row['Low'], 2),
            "close": round(row['Close'], 2),
            "volume": row['Volume']
        })

    return data_list

def fetch_currency_data(currency_pair, period):
    from_currency, to_currency = currency_pair.split('/')
    from_currency = from_currency.encode('utf-8')
    to_currency = to_currency.encode('utf-8')
    period = period.encode('utf-8')

    data_ptr = lib.fetch_historical_data(from_currency, to_currency, period)
    if not data_ptr:
        result_label.config(text="Error fetching historical currency data")
        return None 

    # place data in  dictionary
    data = data_ptr.contents
    historical_data = {
        "dates": [data.dates[i].decode('utf-8') for i in range(data.size)],
        "rates": [data.rates[i] for i in range(data.size)]
    }

    lib.free_historical_data(data_ptr)

    return historical_data

def get_supported_exchanges():
    exchanges = []
    exchanges_ptr = lib.get_supported_exchanges()
    i = 0
    while exchanges_ptr[i]:
        exchanges.append(exchanges_ptr[i].decode('utf-8'))
        i += 1
    return exchanges

def get_supported_currencies():
    currencies = []
    i = 0
    while True:
        currency = lib.get_supported_currencies(i)
        if currency:
            currencies.append(currency.decode('utf-8'))
            i += 1
        else:
            break
    return currencies

def get_economic_data(country_code, data_type, start_year, end_year):
    data_count = c_int()
    result = lib.get_economic_data(
        country_code.encode('utf-8'),
        data_type.encode('utf-8'),
        start_year.encode('utf-8'),
        end_year.encode('utf-8'),
        byref(data_count)
    )
    
    if not result:
        return None
    
    economic_data = []
    for i in range(data_count.value):
        economic_data.append({
            'date': result[i].year.decode('utf-8').strip('\x00'),
            'value': result[i].value
        })
    
    lib.free(result)
    
    return economic_data

def get_interest_rate_data(series_id, start_date, end_date):
    data_count = c_int()
    result = lib.get_interest_rate_data(
        series_id.encode('utf-8'),
        start_date.encode('utf-8'),
        end_date.encode('utf-8'),
        byref(data_count)
    )
    
    if not result:
        print("Error: get_interest_rate_data returned NULL")
        return None
    
    try:
        interest_rate_data = []
        for i in range(data_count.value):
            interest_rate_data.append({
                'date': result[i].date.decode('utf-8').strip('\x00'),
                'value': result[i].value
            })
    except Exception as e:
        print(f"Error processing interest rate data: {str(e)}")
        lib.free_memory(result)
        return None
    
    lib.free_memory(result)
    return interest_rate_data


# webscraping functions
def fetch_and_parse(url, xpath):
    chunk = url_mem()
    result = lib.fetch_data(url.encode('utf-8'), byref(chunk))
    if result != 0:
        raise RuntimeError(f'Failed to fetch data from {url}')
    html_data = string_at(chunk.memory, chunk.size)
    count = c_int()
    tickers = POINTER(c_char_p)()
    lib.parse_html(html_data, xpath.encode('utf-8'), byref(tickers), byref(count))
    tickers_list = [tickers[i].decode('utf-8').strip() for i in range(count.value)]
    lib.free_tickers(tickers, count)
    lib.free_memory(chunk.memory)
    return tickers_list

def scrape_index(index_info, filter_func=None):
    response = requests.get(index_info['url'])
    tree = html.fromstring(response.content)
    
    names = tree.xpath(index_info['xpath_name'])
    tickers = tree.xpath(index_info['xpath_ticker'])
    
    companies = list(zip(names, tickers))
    
    if filter_func:
        companies = filter_func(companies)
    
    return companies

def dax_filter(companies):
    return [(name, ticker) for name, ticker in companies if ticker.endswith('.DE')]



indices = {
    "S&P 500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "xpath_name": "//table[contains(@class, 'wikitable')]/tbody/tr/td[2]/a/text()",
        "xpath_ticker": "//table[contains(@class, 'wikitable')]/tbody/tr/td[1]/a/text()"
    },
    "Dow Jones": {
        "url": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        "xpath_name": "//table[contains(caption, 'DJIA component companies')]/tbody/tr/th[@scope='row']/a/text()",
        "xpath_ticker": "//table[contains(caption, 'DJIA component companies')]/tbody/tr/td[2]/a/text()"
    },
    "FTSE 100": {
        "url": "https://en.wikipedia.org/wiki/FTSE_100_Index",
        "xpath_name": "//table[contains(@class, 'wikitable')][4]/tbody/tr/td[1]/a/text()",
        "xpath_ticker": "//table[contains(@class, 'wikitable')][4]/tbody/tr/td[2]/text()"
    },
    "DAX": {
        "url": "https://en.wikipedia.org/wiki/DAX",
        "xpath_name": "//table[contains(@class, 'wikitable')]/tbody/tr/td[2]/a/text()",
        "xpath_ticker": "//table[contains(@class, 'wikitable')]/tbody/tr/td[4]/a/text()"
    },
    "NASDAQ 100": {
        "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "xpath_name": "//table[contains(@class, 'wikitable')][4]/tbody/tr/td[1]/a/text()",
        "xpath_ticker": "//table[contains(@class, 'wikitable')][4]/tbody/tr/td[2]/text()"
    }
}

all_tickers = {}
for index_name, index_info in indices.items():
    if index_name == "DAX":
        all_tickers[index_name] = scrape_index(index_info, dax_filter)
    else:
        all_tickers[index_name] = scrape_index(index_info)
