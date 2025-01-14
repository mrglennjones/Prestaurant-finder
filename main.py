#Prestaurant finder
#https://github.com/mrglennjones/Prestaurant-finder

from picovector import PicoVector, Polygon, Transform, ANTIALIAS_BEST
from presto import Presto
import urequests
import math
import secrets  # Import Wi-Fi credentials
import network
import time
import random
import qrcode  # Import for QR code generation
from touch import Button

# OpenStreetMap Overpass API URL
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# enter your latitude and longitute and meters radious for the serach
CENTER_LAT = 
CENTER_LON = 
RADIUS_METERS = 24140  # 15 miles in meters

# Initialize Presto and PicoVector
presto = Presto(full_res=False)
display = presto.display
vector = PicoVector(display)
transform = Transform()
vector.set_transform(transform)
vector.set_antialiasing(ANTIALIAS_BEST)

touch = presto.touch

WIDTH, HEIGHT = display.get_bounds()

# Colors
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
GREEN = display.create_pen(0, 255, 0)
BLUE = display.create_pen(0, 0, 255)

# Button constants
BUTTON_X = WIDTH - 80
BUTTON_Y = 10
BUTTON_WIDTH = 70
BUTTON_HEIGHT = 30
BUTTON_VISIBLE = False  # Track button visibility

# Create button instance
restart_button = Button(BUTTON_X, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)

# Variables for terminal text
display_lines = []
MAX_LINES = HEIGHT // 15  # Max number of lines that can fit on the screen

def update_terminal(message):
    global display_lines, BUTTON_VISIBLE
    display.set_pen(BLACK)
    display.clear()
    display.set_pen(GREEN)

    # Add the new message to the list
    display_lines.append(message)
    if len(display_lines) > MAX_LINES:
        display_lines.pop(0)  # Remove the oldest line

    # Display all lines
    for i, line in enumerate(display_lines):
        display.text(line, 10, i * 15, WIDTH - 20, 1)

    # Draw the restart button if visible
    if BUTTON_VISIBLE:
        draw_button()

    presto.update()

def draw_button():
    """Draws the restart button on the display."""
    display.set_pen(BLUE)
    display.rectangle(*restart_button.bounds)
    display.set_pen(WHITE)
    display.text("Restart", BUTTON_X + 5, BUTTON_Y + 5, BUTTON_WIDTH - 10, 1)
    presto.update()

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        ip_address = wlan.ifconfig()[0]
        update_terminal(f"Wi-Fi Already Connected! IP: {ip_address}")
        print(f"[Wi-Fi] Already Connected! IP: {ip_address}")
        return wlan

    update_terminal("Connecting to Wi-Fi...")
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)

    for _ in range(20):  # Try for ~10 seconds
        if wlan.isconnected():
            ip_address = wlan.ifconfig()[0]
            update_terminal(f"Wi-Fi Connected! IP: {ip_address}")
            print(f"[Wi-Fi] Connected! IP: {ip_address}")
            return wlan
        time.sleep(0.5)

    update_terminal("Wi-Fi connection failed!")
    print("[Wi-Fi] Failed to connect. Check your credentials.")
    raise RuntimeError("Wi-Fi connection failed.")

def fetch_pois(lat, lon, radius):
    update_terminal("Fetching points of interest...")
    query = f"""
    [out:json];
    node["amenity"~"fast_food|cafe|restaurant"](around:{radius},{lat},{lon});
    out;
    """
    try:
        response = urequests.post(OVERPASS_API_URL, data=query)
        if response.status_code == 200:
            update_terminal("Data fetched successfully!")
            print("[POI Fetch] Data fetched successfully!")
            return response.json()
        else:
            update_terminal(f"Error fetching data: {response.status_code}")
            print(f"[Error] Failed to fetch POIs: {response.status_code}")
            return None
    except Exception as e:
        update_terminal("Error querying Overpass API!")
        print(f"[Error] Error querying Overpass API: {e}")
        return None

def measure_qr_code(max_size, code):
    qr_width, qr_height = code.get_size()  # Ensure dimensions are properly unpacked
    if qr_width != qr_height:  # Validate that QR code is square
        raise ValueError(f"QR code size is not square: {qr_width}x{qr_height}.")
    module_size = max_size // qr_width  # Determine module size to fit display
    total_size = module_size * qr_width  # Calculate total size
    return total_size, module_size

def draw_qr_code(ox, oy, max_size, code):
    total_size, module_size = measure_qr_code(max_size, code)
    qr_width, qr_height = code.get_size()

    for x in range(qr_width):
        for y in range(qr_height):
            if code.get_module(x, y):  # Check if the module is black
                x_pos = ox + x * module_size
                y_pos = oy + y * module_size
                display.set_pen(BLACK)
                display.rectangle(x_pos, y_pos, module_size, module_size)
    presto.update()

def display_qrcode(name, text):
    global BUTTON_VISIBLE
    code = qrcode.QRCode()
    code.set_text(text)
    qr_size = 160  # Adjusted size for better fit
    total_size, _ = measure_qr_code(qr_size, code)
    qr_x = (WIDTH - total_size) // 2  # Center the QR code horizontally
    qr_y = (HEIGHT - total_size) // 2 + 40

    # Clear the screen and draw the QR code
    display.set_pen(WHITE)
    display.clear()
    draw_qr_code(qr_x, qr_y, qr_size, code)

    # Display restaurant name centered above the QR code
    display.set_pen(BLACK)
    wrapped_text = wrap_text(name, WIDTH - 20, font_size=2)
    text_y = qr_y - (len(wrapped_text) * 20 + 10)
    for line in wrapped_text:
        name_x = (WIDTH - display.measure_text(line, 2)) // 2
        display.text(line, name_x, text_y, WIDTH, 2)
        text_y += 20

    # Draw the restart button
    BUTTON_VISIBLE = True
    draw_button()
    presto.update()

def wrap_text(text, max_width, font_size):
    """Wrap text to fit within a specified width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if display.measure_text(test_line, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines

def display_random_restaurant(pois):
    if not pois or "elements" not in pois:
        update_terminal("No data found for POIs.")
        print("[POI Fetch] No data found.")
        return

    elements = pois["elements"]

    if not elements:
        update_terminal("No restaurants, cafes, or fast food found.")
        print("[POI Fetch] No restaurants, cafes, or fast food found.")
        return

    random_choice = random.choice(elements)
    name = random_choice.get("tags", {}).get("name", "Unnamed")
    lat = random_choice.get("lat")
    lon = random_choice.get("lon")

    # Generate a Google Maps link for the location
    location_url = f"https://www.google.com/maps?q={lat},{lon}"

    # Display the restaurant name and QR code
    print(f"[Random Pick] Selected: {name}, Location: {location_url}")
    display_qrcode(name, location_url)

def main(skip_wifi=False):
    global BUTTON_VISIBLE
    BUTTON_VISIBLE = False  # Ensure the button starts hidden
    if not skip_wifi:
        connect_to_wifi()

    # Fetch POIs within a 15-mile radius 
    pois = fetch_pois(CENTER_LAT, CENTER_LON, RADIUS_METERS)

    # Display a random restaurant
    display_random_restaurant(pois)

if __name__ == "__main__":
    wlan = None
    while True:
        main(skip_wifi=wlan and wlan.isconnected())
        while True:
            touch.poll()
            if BUTTON_VISIBLE and restart_button.is_pressed():
                update_terminal("Restarting script...")
                break
            time.sleep(0.1)

