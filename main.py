from urllib3 import HTTPSConnectionPool
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from bs4 import BeautifulSoup
import urllib3
import folium
import codecs
import json
import time
import re

geolocator = Nominatim(user_agent="sample app")


def def_requester(host) -> tuple[HTTPSConnectionPool, dict]:
    # Initialize HTTP Settings
    pool = HTTPSConnectionPool(host, maxsize=1)
    USER_AGENT = 'Mozilla/5.0'
    headers = urllib3.make_headers(user_agent=USER_AGENT)
    return (pool, headers)


def requester(pool, path, headers, fields):
    return (pool.request(method='GET', url=path, headers=headers, fields = fields))


def get_sulets_accommodations() -> list:
    # Initial set to 0
    page = 0
    pool, headers = def_requester(host='www.sulets.com')

    accommodations = []
    while (True):
        page += 1
        path = f'/search-results/page/{page}/'
        fields = {'sort': 'price-asc'}
        resp = requester (
            pool = pool,
            path = path, 
            headers = headers, 
            fields = fields
        )
        web_data = resp.data
        soup = BeautifulSoup(web_data, 'html.parser')

        # Display Name
        card_title = soup.find_all(attrs={"class":"card__title"})
        titles = []
        for each in card_title:
            titles.append(str(each.get_text()).strip())
        # print(titles)
        # print()

        # Display Price
        card_price = soup.find_all(attrs={"class":"card__price"})
        prices = []
        for each in card_price:
            prices.append(str(each.get_text()).strip())
        # print(prices)
        # print()

        # Links
        card = soup.find_all(attrs={"class":"card"})
        links = []
        for each in card:
            links.append(each.get('href'))
        # print(links)
        # print()


        accommodations_paged = []
        for i in range(len(titles)):
            accommodations_paged.append({'title': titles[i], 'price': prices[i], 'price_number': int(prices[i][1:4]), 'url': links[i]})

        if accommodations_paged:
            accommodations += accommodations_paged
        else:
            break
    return accommodations


def map_sulets_accommodation(sulets_accommodations=None) -> list:

    accommodations = []
    pool, headers = def_requester(host='www.sulets.com')

    for accommodation in sulets_accommodations:
        temp_accommodation = accommodation
        # temp_accommodation = []

        path = f'/accpmmodation/{accommodation["url"][36:]}'
        fields = {}
        resp = requester (
            pool = pool,
            path = path, 
            headers = headers, 
            fields = fields
        )
        web_data = resp.data

        soup = BeautifulSoup(web_data, 'html.parser')

        # Property Features
        propertyFeatures = soup.find_all(attrs={"class":"property-features__list-item"})
        property_features = []
        for each in propertyFeatures:
            property_features.append(str(each.get_text()).strip())
        # print(property_features)

        # Location Data
        pattern = re.compile('var sul_acc_location = (.*?);')
        scripts = soup.find_all('script')
        for script in scripts:
            if(pattern.match(str(script.string))):
                data = pattern.match(script.string)
                location = data.groups()[0].strip('\'')
        # print(location)

        # Additional Location Data
        lists = soup.find('ul', 'no-bullet')
        additional_location_data = []
        for li in lists.find_all("li"):
            additional_location_data.append(li.text.strip())
        # print(additional_location_data)

        temp_accommodation['location_data'] = {'location': location, 'additional_location_data': additional_location_data}
        temp_accommodation['rent_information'] = property_features
        accommodations.append(temp_accommodation)
    return accommodations


def bing_mapper(accommodations):
    # api = 'https://www.bing.com/maps?sp=adr.<>~adr.<>'
    api = 'https://www.bing.com/maps?sp='

    for accommodation in accommodations['data']:
        api += f'adr.{accommodation["location_data"]["location"]}~'
    print(api)
    print(api[-1])


def opensm_html_sulets(accommodation):
    location_list_item = '<ul style="margin:5px">'
    for item in accommodation['location_data']['additional_location_data']:
        location_list_item += f'<li>{item}</li>'
    location_list_item += '</ul>'

    rent_list_item = '<ul style="margin:5px">'
    for item in accommodation['rent_information']:
        rent_list_item += f'<li>{item}</li>'
    rent_list_item += '</ul>'

    html = f"""
        <h4 style="margin:6px"><a href="{accommodation['url']}" style="color:blue; text-decoration:underline;">{accommodation['title']}</a></h4>
        <h4 style="margin:6px">{accommodation['location_data']['location']}</h4>
        <h4 style="margin:6px">Price: <span style="font-weight:normal; background-color:#F4FF33; color:red">{accommodation['price']}</span></h4>
        <h4>
            <span style="font-weight:normal;">
                <p style="margin:5px"><b>Location Details:</b></p>
                {location_list_item}
                <p style="margin:5px"><b>Rent Details:</b></p>
                {rent_list_item}
            </span>
        </h4>
    """
    return html 


def opensm_mapper(accommodations):
    accommodations_data = []
    m = folium.Map(location=[52.6322236,-1.1315009], zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)

    for accommodation in accommodations['data']:
        temp_accommodation = accommodation
        location = accommodation['location_data']['location']
        try:
            data = geolocator.geocode(location)
            lat = data.raw.get('lat')
            lon = data.raw.get('lon')
            temp_accommodation['location_data']['map']=  {'lat': lat, 'lon': lon}

            iframe_html = opensm_html_sulets(accommodation=accommodation)

            iframe = folium.IFrame(html=iframe_html, width=315, height=400)
            popup = folium.Popup(iframe, max_width=2650) 

            circle_color = ''
            rect_color = ''

            if accommodation['price_number'] > 105:
                circle_color = 'orange'
                rect_color = 'red'
            else:
                circle_color = 'lime'
                rect_color = 'green'

            icon_html = f"""
                    <div><svg>
                        <circle cx="50" cy="50" r="40" fill="{circle_color}" opacity=".6"/>
                        <rect x="35", y="35" width="30" height="30", fill="{rect_color}"/>
                    </svg></div>
            """

            folium.Marker(
                location = (lat, lon), 
                popup = popup, 
                icon = folium.DivIcon(html=icon_html),
                tooltip = f'{accommodation["title"]} | {accommodation["price"]}')\
                .add_to(marker_cluster)
        except:
            lat, lon = None, None
            temp_accommodation['location_data']['map']=  {'lat': lat, 'lon': lon}
        accommodations_data.append(temp_accommodation)

    m.save('map.html')

    accommodations['data'] = accommodations_data
    return accommodations




start = time.time()

sulets_accommodations = get_sulets_accommodations()
sulets_accommodations = map_sulets_accommodation(sulets_accommodations=sulets_accommodations)

accommodations = {}
accommodations['count'] = len(sulets_accommodations)
accommodations['data'] = sulets_accommodations

with open("accommodations.json", "wb") as f:
    json.dump(accommodations, codecs.getwriter('utf-8')(f), ensure_ascii=False, indent=4)

# bing_mapper(accomodations=accomodations)
accommodations = opensm_mapper(accommodations=accommodations)

with open("accommodations.json", "wb") as f:
    json.dump(accommodations, codecs.getwriter('utf-8')(f), ensure_ascii=False, indent=4)


end = time.time()
display_time = round(end-start, 2)
print(f'Total Time Taken: {display_time} seconds')
