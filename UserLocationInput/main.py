from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Column, Row, Label, WheelZoomTool, Button, CustomJS, TextInput, Paragraph
from bokeh.io import curdoc
from bokeh.events import DoubleTap
from bokeh.tile_providers import OSM, get_provider
import geoip2.database
from pyproj import transform
import psycopg2

# Database connection
conn = psycopg2.connect(dbname="worldborders", user="postgres", password=123456789)
cur = conn.cursor()

def get_user_ip():
    raise Exception

try:
    user_ip = get_user_ip()
    with geoip2.database.Reader(
            r'C:\Users\PC\PycharmProjects\LearnGeoDjango\geodjango\geodjango\geoip\GeoLite2-City.mmdb') as reader:
        response = reader.city(user_ip)
        user_coords = transform(4326, 3857, response.location.latitude, response.location.longitude)
    label_text = 'You are here'


except:
    user_coords = transform(4326, 3857, 42.36034, -71.0578633)
    label_text = 'Boston City Hall'

TOOLS = "tap,pan,reset"
p = figure(title='Double-click to select a location.',
           tools=TOOLS, width=700, height=500,
           x_range=(user_coords[0] - 10000, user_coords[0] + 10000),
           y_range=(user_coords[1] - 10000, user_coords[1] + 10000),
           background_fill_color='powderblue',
           border_fill_color='powderblue',
           )
p.toolbar.logo = None
p.toolbar_location = None
p.x_range.min_interval = 100
p.x_range.max_interval = 100000
p.add_tools(WheelZoomTool(zoom_on_axis=False))
p.toolbar.active_scroll = p.select_one(WheelZoomTool)
p.axis.visible = False
p.circle(x=user_coords[0], y=user_coords[1], line_color="black", fill_color="red", size=10)
cur.execute("""
    SELECT x, y FROM bins_binlocation;
""")
bin_coords = cur.fetchall()
for x, y in bin_coords:
    coord = transform(4326, 3857, y, x)
    p.circle(x=coord[0], y=coord[1], line_color="black", fill_color="lightgreen", size=8)

labels = Label(x=user_coords[0], y=user_coords[1], text=label_text,
               x_offset=5, y_offset=5, render_mode='canvas', background_fill_color='white', background_fill_alpha=.75)
p.add_layout(labels)
tile_provider = get_provider(OSM)
p.add_tile(tile_provider)

source = ColumnDataSource(data=dict(x=[], y=[], url=[], w=[], h=[]))
bin_image = p.image_url(source=source, x='x', y='y', url='url', w='w', h='h', w_units='screen', h_units='screen',
                        anchor='center')


coords_4326 = None


def drop_bin_callback(event):
    coords = (event.x, event.y)
    source.data = dict(x=[coords[0]], y=[coords[1]],
                       w=[25], h=[25],
                       url=[r'UserLocationInput\static\compost_bin_green.png']
                       )
    global coords_4326
    coords_4326 = transform(3857, 4326, coords[0], coords[1])
    print("map click:", coords_4326)
    input_validator('value', None, coords_4326)


p.on_event(DoubleTap, drop_bin_callback)

button = Button(label='Submit Bin Location', button_type='success', width=200, height=60)


def button_submit_callback():
    print("button click:", coords_4326)
    print(name_input.value)
    print(email_input.value)
    print(zip_input.value)
    coords_3857 = transform(4326, 3857, coords_4326[0], coords_4326[1])
    cur.execute(f"""
    INSERT INTO bin_location_votes(name, email, zip, vote_coords, vote_coords_webmercator) 
    VALUES ('{name_input.value}', '{email_input.value}', '{zip_input.value}', '{coords_4326}', '{coords_3857}');

    COMMIT
    """)


button_redirect = CustomJS(code="""
                                window.location = "https://talzaken.pythonanywhere.com/"
                                """)
button.on_click(button_submit_callback)
button.js_on_click(button_redirect)
button.disabled = True


def input_validator(attr, old, new):
    global name_input
    global email_input
    global zip_input
    global coords_4326
    global button
    if all([name_input.value, email_input.value, zip_input.value, coords_4326]):
        print("in the validator - valid")
        button.disabled = False
    else:
        print("in the validator - invalid")
        print(name_input)
        print(email_input)
        print(zip_input)
        print(coords_4326)
        button.disabled = True


name_input = TextInput(placeholder='Type your name here', title="Name:", max_length=200, id='name_input')
name_input.on_change("value", input_validator)
email_input = TextInput(placeholder='Type your email address here', title="Email:", max_length=200)
email_input.on_change("value", input_validator)
zip_input = TextInput(placeholder='Type your five-digit ZIP Code here', title="ZIP Code:", max_length=5)
zip_input.on_change("value", input_validator)

button_explainer_text = Paragraph(text="Please Note: All fields are required."
                                       "You must also select a location on the map above. "
                                       "Double-click to drop a compost bin, then click 'Submit Bin Location' "
                                       "to register your vote.")
button_row = Row(button, button_explainer_text)

layout = Column(p, name_input, email_input, zip_input, button_row, name='layout')
curdoc().add_root(layout)
