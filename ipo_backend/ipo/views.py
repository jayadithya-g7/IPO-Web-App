from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
import requests
# from nsetools import Nse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache  # To cache and avoid hitting API rate limits
from datetime import datetime, timedelta


from .models import Company, IPO, Document, User, Application
from .serializers import (
    CompanySerializer,
    IPOSerializer,
    DocumentSerializer,
    UserSerializer,
    ApplicationSerializer,
)


#  Home Page View
def home(request):
    return render(request, 'ipo/home.html')


#  API ViewSets

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class IPOViewSet(viewsets.ModelViewSet):
    queryset = IPO.objects.all()
    serializer_class = IPOSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'issue_type']
    search_fields = ['company__company_name']


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    filterset_fields = ['ipo']


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer



class MarketMoverData(APIView):
    def get(self, request):
        stock_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK', 'BAJFINANCE', 'KOTAKBANK', 'SBIN', 'LT',
            'HDFC', 'ITC', 'AXISBANK', 'BHARTIARTL', 'MARUTI', 'TITAN', 'SUNPHARMA', 'M&M', 'ULTRACEMCO', 'WIPRO',
            'ADANIGREEN', 'HCLTECH', 'NTPC', 'ASIANPAINT', 'INDUSINDBK', 'TATAMOTORS', 'POWERGRID', 'DIVISLAB', 'SBILIFE',
            'BAJAJ-AUTO', 'TECHM', 'EICHERMOT', 'DRREDDY', 'TATACONSUM', 'GRASIM', 'BRITANNIA', 'UPL', 'COALINDIA',
            'IOC', 'HEROMOTOCO', 'BPCL', 'JSWSTEEL', 'MCDOWELL-N', 'ONGC', 'SHREECEM', 'MARICO', 'CIPLA', 'TATAPOWER'
        ]

        api_key = 'DNJQ574FZAKW4MEF'
        base_url = 'https://www.alphavantage.co/query'

        # Use cache to reduce API calls
        cached_data = cache.get('nifty_52w_data')
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        high_list = []
        low_list = []

        for symbol in stock_symbols:
            # 1. Get historical data for 52-week high/low
            daily_params = {
                'function': 'TIME_SERIES_DAILY_ADJUSTED',
                'symbol': symbol,
                'apikey': api_key,
                'outputsize': 'full'
            }

            daily_resp = requests.get(base_url, params=daily_params)
            if daily_resp.status_code != 200:
                continue
            daily_data = daily_resp.json().get("Time Series (Daily)", {})
            if not daily_data:
                continue

            sorted_dates = sorted(daily_data.keys(), reverse=True)
            last_252_days = sorted_dates[:252]

            highs = [float(daily_data[day]["2. high"]) for day in last_252_days]
            lows = [float(daily_data[day]["3. low"]) for day in last_252_days]

            high_52w = max(highs)
            low_52w = min(lows)

            # 2. Get real-time intraday data for latest price & day high
            intraday_params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'interval': '1min',
                'apikey': api_key
            }

            intraday_resp = requests.get(base_url, params=intraday_params)
            if intraday_resp.status_code != 200:
                continue

            intraday_data = intraday_resp.json().get("Time Series (1min)", {})
            if not intraday_data:
                continue

            latest_time = sorted(intraday_data.keys())[-1]
            latest_info = intraday_data[latest_time]

            current_price = float(latest_info["4. close"])
            day_high = float(latest_info["2. high"])

            # Threshold: within 1% of 52-week high/low
            if current_price >= high_52w * 0.99:
                high_list.append({
                    "symbol": symbol,
                    "current_price": current_price,
                    "day_high": day_high,
                    "52_week_high": high_52w
                })

            if current_price <= low_52w * 1.01:
                low_list.append({
                    "symbol": symbol,
                    "current_price": current_price,
                    "day_high": day_high,
                    "52_week_low": low_52w
                })

        result = {
            "highs": high_list,
            "lows": low_list
        }

        # Cache for 60 seconds
        cache.set('nifty_52w_data', result, timeout=60)
        return Response(result, status=status.HTTP_200_OK)




# from NSE INDIA 
# class MarketMoverData(APIView):
#     def get(self, request):
#         # List of stock symbols for NSE (Indian Stock Market)
#         stock_symbols = [
#             'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK', 'BAJFINANCE', 'KOTAKBANK', 'SBIN', 'LT',
#             'HDFC', 'ITC', 'AXISBANK', 'BHARTIARTL', 'MARUTI', 'TITAN', 'SUNPHARMA', 'M&M', 'ULTRACEMCO', 'WIPRO',
#             'ADANIGREEN', 'HCLTECH', 'NTPC', 'ASIANPAINT', 'INDUSINDBK', 'TATAMOTORS', 'POWERGRID', 'DIVISLAB', 'SBILIFE',
#             'BAJAJ-AUTO', 'TECHM', 'EICHERMOT', 'DRREDDY', 'TATACONSUM', 'GRASIM', 'BRITANNIA', 'UPL', 'COALINDIA',
#             'IOC', 'HEROMOTOCO', 'BPCL', 'JSWSTEEL', 'MCDOWELL-N', 'ONGC', 'SHREECEM', 'MARICO', 'CIPLA', 'TATAPOWER'
#         ]

#         # Initialize NSE object from nsetools
#         nse = Nse()

#         # Check if data is in cache to avoid repeated API calls
#         cached_data = cache.get('market_mover_data')
#         if cached_data:
#             return Response(cached_data, status=status.HTTP_200_OK)

#         stock_data = []

#         # Fetch data for each stock in the list
#         for symbol in stock_symbols:
#             try:
#                 # Fetch real-time data for the symbol
#                 quote = nse.get_quote(symbol)
#                 if quote:
#                     stock_data.append({
#                         "symbol": symbol,
#                         "company": quote['companyName'],
#                         "last_price": quote['lastPrice'],
#                         "change": quote['priceInfo']['change'],
#                         "percent_change": quote['priceInfo']['changePercent'],
#                         "volume": quote['quantityTraded']
#                     })
#             except Exception as e:
#                 continue  # Skip the stock if there is an error in fetching data

#         # Cache the data for 30 seconds to avoid repeated API calls
#         cache.set('market_mover_data', stock_data, timeout=30)

#         return Response({"stock_data": stock_data}, status=status.HTTP_200_OK)
