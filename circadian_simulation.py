import pygame, math, random
import urllib.request, json
from datetime import datetime

# ---------------- Global Realtime Sun Data ----------------
SUNRISE = 6.0
SUNSET = 18.0
LOCATION = "Unknown Location"

def fetch_realtime_sun_data():
    global SUNRISE, SUNSET, LOCATION
    try:
        # Add User-Agent to prevent 403 Forbidden block
        req_ip = urllib.request.Request("http://ip-api.com/json/", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_ip, timeout=5) as response:
            loc_data = json.loads(response.read().decode())
        
        lat = loc_data['lat']
        lon = loc_data['lon']
        city = loc_data.get('city', 'Unknown')
        country = loc_data.get('country', 'Unknown')
        LOCATION = f"{city}, {country}"
        
        sun_api_url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&formatted=0"
        req_sun = urllib.request.Request(sun_api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_sun, timeout=5) as response:
            data = json.loads(response.read().decode())['results']
        
        sr_str = data['sunrise'].replace('Z', '+00:00')
        ss_str = data['sunset'].replace('Z', '+00:00')
        
        local_sunrise = datetime.fromisoformat(sr_str).astimezone()
        local_sunset = datetime.fromisoformat(ss_str).astimezone()
        
        SUNRISE = local_sunrise.hour + local_sunrise.minute/60.0 + local_sunrise.second/3600.0
        SUNSET = local_sunset.hour + local_sunset.minute/60.0 + local_sunset.second/3600.0
        print(f"Location found: {LOCATION}")
        print(f"Dynamic Sunrise: {SUNRISE:.2f}h | Dynamic Sunset: {SUNSET:.2f}h")
    except Exception as e:
        print("Using defaults. Error:", e)

# Fetch data at startup
fetch_realtime_sun_data()
pygame.init()

# ---------------- Window ----------------
WIDTH, HEIGHT = 1200, 760
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Circadian Smart Lighting Simulator – Realistic Background")

# ---------------- Fonts ----------------
try:
    font_large = pygame.font.SysFont("segoeui", 28, bold=True)
    font = pygame.font.SysFont("segoeui", 18, bold=True)
    small_font = pygame.font.SysFont("segoeui", 13, bold=True)
except:
    font_large = pygame.font.SysFont("arial", 28, bold=True)
    font = pygame.font.SysFont("arial", 18, bold=True)
    small_font = pygame.font.SysFont("arial", 13, bold=True)
clock = pygame.time.Clock()

# ---------------- State ----------------
now = datetime.now()
hour = now.hour
fraction = now.minute / 60.0 + now.second / 3600.0
player_offset = 0
ai_enabled = True
NUM_STARS = 120
# (x, y, base_brightness, twinkle_speed)
stars_data = [(random.randint(420, WIDTH), random.randint(0, HEIGHT//2 + 50), 
               random.randint(150, 255), random.uniform(0.05, 0.2)) for _ in range(NUM_STARS)]
fps = 30
time_speed = 0.02
speed_factor = 1.0

# ---------------- Models ----------------
def ai_circadian(hour):
    mid_day = (SUNRISE + SUNSET) / 2
    angle = (hour - (mid_day - 6)) / 24 * 2 * math.pi
    return (math.sin(angle)+1)/2*100

def brightness_to_kelvin(brightness):
    return int(2700 + (brightness/100)*(6500-2700))

def kelvin_to_rgb(kelvin):
    temp = kelvin/100
    if temp <=66:
        red = 255
        green = 99.47*math.log(temp)-161.12
        blue = 0 if temp<=19 else 138.52*math.log(temp-10)-305.04
    else:
        red = 329.7*((temp-60)**-0.133)
        green = 288.12*((temp-60)**-0.075)
        blue = 255
    return (max(0,int(red)),max(0,int(green)),max(0,int(blue)))

def lerp_color(c1, c2, t):
    """Ομαλή μίξη χρωμάτων για το ρεαλιστικό gradient του ουρανού."""
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))

# ---------------- Σχεδίαση Background ----------------
def draw_sky_gradient(h):
    points = [
        (0.0,  (5, 5, 20),   (10, 10, 30)),
        (max(0.01, SUNRISE - 1.5),  (20, 30, 60), (100, 60, 40)),
        (max(0.02, SUNRISE + 0.5),  (70, 130, 190), (255, 180, 100)),
        ((SUNRISE+SUNSET)/2, (30, 110, 200), (135, 206, 235)),
        (min(23.97, SUNSET - 1.5), (70, 130, 190), (255, 160, 80)),
        (min(23.98, SUNSET + 0.5), (20, 30, 80),  (255, 80, 20)),
        (min(23.99, SUNSET + 2.0), (10, 10, 40),  (20, 20, 50)),
        (24.0, (5, 5, 20),   (10, 10, 30))
    ]
    points.sort(key=lambda x: x[0])
    
    c1_top, c1_bott, c2_top, c2_bott = points[0][1], points[0][2], points[-1][1], points[-1][2]
    t = 0
    for i in range(len(points)-1):
        if points[i][0] <= h <= points[i+1][0]:
            p1, p2 = points[i], points[i+1]
            c1_top, c1_bott = p1[1], p1[2]
            c2_top, c2_bott = p2[1], p2[2]
            if p2[0] - p1[0] > 0:
                t = (h - p1[0]) / (p2[0] - p1[0])
            break

    top_color = lerp_color(c1_top, c2_top, t)
    bott_color = lerp_color(c1_bott, c2_bott, t)

    # Gradient Scaling για καλύτερη απόδοση
    grad = pygame.Surface((1, 2))
    pygame.draw.line(grad, top_color, (0, 0), (0, 0))
    pygame.draw.line(grad, bott_color, (0, 1), (0, 1))
    screen.blit(pygame.transform.smoothscale(grad, (WIDTH, HEIGHT)), (0, 0))

def draw_sun_moon(hour_fraction):
    # Προσάρμοσα λίγο το X για να μην κρύβονται πίσω από το UI panel
    horizon_y = 450
    left_x = 450
    right_x = 1100
    arc_h = 280
    glow_surface = pygame.Surface((200, 200), pygame.SRCALPHA)

    if SUNRISE <= hour_fraction < SUNSET: # Ήλιος
        day_length = SUNSET - SUNRISE
        t = (hour_fraction - SUNRISE) / day_length
        x = left_x + t * (right_x - left_x)
        y = horizon_y - math.sin(math.pi * t) * arc_h
        
        # Glow Effect
        pygame.draw.circle(glow_surface, (255, 200, 60, 50), (100, 100), 70)
        pygame.draw.circle(glow_surface, (255, 220, 100, 90), (100, 100), 40)
        screen.blit(glow_surface, (x - 100, y - 100))
        
        pygame.draw.circle(screen, (255, 255, 220), (int(x), int(y)), 26)
    else: # Φεγγάρι
        night_len = 24.0 - SUNSET + SUNRISE
        if hour_fraction >= SUNSET:
            t = (hour_fraction - SUNSET) / night_len
        else:
            t = (hour_fraction + 24.0 - SUNSET) / night_len
            
        x = left_x + t * (right_x - left_x)
        y = horizon_y - math.sin(math.pi * t) * arc_h
        
        # Glow Effect
        pygame.draw.circle(glow_surface, (180, 180, 255, 30), (100, 100), 60)
        pygame.draw.circle(glow_surface, (200, 220, 255, 60), (100, 100), 35)
        screen.blit(glow_surface, (x - 100, y - 100))
        
        # Το δικό σου κόλπο με τους δύο κύκλους για να φαίνεται σαν μισοφέγγαρο
        pygame.draw.circle(screen, (220, 220, 235), (int(x), int(y)), 22)
        pygame.draw.circle(screen, (190, 190, 210), (int(x + 8), int(y)), 22)

def draw_stars(hour_fraction):
    if hour_fraction >= SUNSET or hour_fraction < SUNRISE:
        for sx, sy, base_b, t_speed in stars_data:
            # Απλό εφέ τρεμοπαίγματος
            twinkle = (math.sin(pygame.time.get_ticks() * t_speed * 0.01) + 1) / 2
            b = int(base_b * (0.6 + twinkle * 0.4))
            b = max(100, min(255, b))
            pygame.draw.circle(screen, (b, b, b), (sx, sy), 2)

def draw_horizon():
    # Σιλουέτα βουνών στο βάθος (ξεκινάει από x=0 αλλά θα καλυφθεί από το UI στα αριστερά)
    mountains = [
        (0, HEIGHT), (0, 400), (250, 320), (500, 420),
        (700, 300), (900, 410), (1050, 340), (1200, 390), (1200, HEIGHT)
    ]
    pygame.draw.polygon(screen, (15, 20, 30), mountains)

# ---------------- Σχεδίαση Γραφήματος ----------------
def get_smooth_curve(points, segments=4):
    """Μετατρέπει γωνιακά σημεία σε μία ομαλή καμπύλη με Catmull-Rom Splines."""
    if len(points) < 4:
        return points
    
    smooth_points = []
    # Προσθέτουμε dummy σημεία στην αρχή και στο τέλος
    p = [points[0]] + points + [points[-1]]
    
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i-1], p[i], p[i+1], p[i+2]
        for t in range(segments):
            t_frac = t / float(segments)
            t_sq = t_frac ** 2
            t_cub = t_frac ** 3
            
            # Catmull-Rom splines math
            q0 = -t_cub + 2*t_sq - t_frac
            q1 = 3*t_cub - 5*t_sq + 2
            q2 = -3*t_cub + 4*t_sq + t_frac
            q3 = t_cub - t_sq
            
            x = 0.5 * (p0[0]*q0 + p1[0]*q1 + p2[0]*q2 + p3[0]*q3)
            y = 0.5 * (p0[1]*q0 + p1[1]*q1 + p2[1]*q2 + p3[1]*q3)
            # Περιορίζουμε το y για να μην βγαίνει εκτός του γραφήματος
            smooth_points.append((x, max(0, y)))
            
    smooth_points.append(points[-1])
    return smooth_points

def draw_graph(surface, ai_vals, player_vals, start_x, start_y, width, height, current_time):
    # --- Υπόβαθρο Γραφήματος (Premium Glassmorphism / iOS Widget Style) ---
    bg_rect = pygame.Rect(start_x, start_y, width, height)
    # Πολύ διαφανές, βαθύ μπλε/μαύρο φόντο (Frosted Glass Illusion)
    pygame.draw.rect(surface, (15, 20, 30, 160), bg_rect, border_radius=18)
    # Λεπτό, ημιδιάφανο λευκό περίγραμμα για την αίσθηση του γυαλιού
    pygame.draw.rect(surface, (255, 255, 255, 25), bg_rect, width=1, border_radius=18)
    # Inner glow
    pygame.draw.rect(surface, (255, 255, 255, 5), bg_rect.inflate(-2, -2), width=1, border_radius=17)

    # ---------------- 1. Αέρινο Πλέγμα (Subtle Glass Grid) ----------------
    for i in range(1, 4):
        gy = start_y + i * (height // 4)
        # Γραμμές που ίσα που διακρίνονται, σαν χάραγμα στο γυαλί
        pygame.draw.line(surface, (255, 255, 255, 12), (start_x + 15, gy), (start_x + width - 40, gy), 1)
        
        # Ποσοστά με μοντέρνα, απαλή γραμματοσειρά
        val_pct = 100 - (i * 25)
        lbl = small_font.render(f"{val_pct}%", True, (140, 150, 170))
        surface.blit(lbl, (start_x + width - 35, gy - 8))

    # ---------------- 2. Ομαλές Καμπύλες Δεδομένων (Splines) ----------------
    num_points = len(ai_vals)
    dx = (width - 45) / (num_points - 1)
    
    raw_ai = [(start_x + i * dx, start_y + height - val * height / 100) for i, val in enumerate(ai_vals)]
    raw_pl = [(start_x + i * dx, start_y + height - val * height / 100) for i, val in enumerate(player_vals)]
    
    smooth_ai = get_smooth_curve(raw_ai, segments=5)
    smooth_pl = get_smooth_curve(raw_pl, segments=5)

    # ---------------- 3. Γέμισμα Περιοχής (Vibrant Gradient Fills) ----------------
    fill_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    def to_local(pts):
        return [(x - start_x, y - start_y) for x, y in pts]
    
    local_ai = to_local(smooth_ai)
    local_pl = to_local(smooth_pl)
    
    ai_poly = [(0, height)] + local_ai + [(width-45, height)]
    pl_poly = [(0, height)] + local_pl + [(width-45, height)]
    
    # Ζωντανά χρώματα, αλλά με διαφάνεια (Cyan & Coral)
    pygame.draw.polygon(fill_surface, (0, 230, 255, 25), ai_poly)   # Electric Cyan base
    pygame.draw.polygon(fill_surface, (255, 90, 70, 25), pl_poly)   # Soft Orange-Red base
    surface.blit(fill_surface, (start_x, start_y))

    # ---------------- 4. Gorgeous Luminous Curves (Γραμμές σαν φως) ----------------
    ai_color = (0, 240, 255) # Bright Cyan
    pl_color = (255, 120, 90) # Soft Light Orange-Red (Coral)
    
    # Απαλή, χρωματιστή σκιά για βάθος (όχι θολό neon, αλλά clean drop shadow)
    for offset in range(1, 4):
        pygame.draw.aalines(surface, (0, 100, 150, 80), False, [(x, min(start_y+height, y + offset)) for x, y in smooth_ai])
        pygame.draw.aalines(surface, (180, 50, 30, 80), False, [(x, min(start_y+height, y + offset)) for x, y in smooth_pl])

    # Κεντρικές, υπέρλαμπρες γραμμές
    pygame.draw.aalines(surface, ai_color, False, smooth_ai)
    pygame.draw.aalines(surface, (255, 255, 255, 180), False, [(x, max(start_y, y - 0.5)) for x, y in smooth_ai]) # Λευκό highlight
    
    pygame.draw.aalines(surface, pl_color, False, smooth_pl)
    pygame.draw.aalines(surface, (255, 255, 255, 180), False, [(x, max(start_y, y - 0.5)) for x, y in smooth_pl])

    # ---------------- 5. Elegant Μινιμαλιστικοί Δείκτες Ήλιου & Σελήνης ----------------
    sr_x = start_x + (SUNRISE / 24.0) * (width - 45)
    ss_x = start_x + (SUNSET / 24.0) * (width - 45)
    
    # Ημιδιάφανες γυάλινες στήλες
    sr_bar = pygame.Surface((2, height), pygame.SRCALPHA)
    sr_bar.fill((255, 220, 100, 70))
    surface.blit(sr_bar, (sr_x, start_y))
    
    ss_bar = pygame.Surface((2, height), pygame.SRCALPHA)
    ss_bar.fill((200, 150, 255, 70))
    surface.blit(ss_bar, (ss_x, start_y))

    # Διακριτικά εικονίδια στον άξονα
    surface.blit(small_font.render("☀", True, (255, 220, 150)), (sr_x - 6, start_y + height - 16))
    surface.blit(small_font.render("☾", True, (200, 180, 255)), (ss_x - 6, start_y + height - 16))

    # ---------------- 6. Playhead Indicator (Floating Glass Needle) ----------------
    current_x = start_x + (current_time / 24.0) * (width - 45)
    current_ai_val = ai_circadian(current_time)
    current_y = start_y + height - (current_ai_val * height / 100)
    
    # Λευκή, καθαρή γραμμή
    pygame.draw.line(surface, (255, 255, 255, 180), (current_x, start_y), (current_x, start_y + height), 1)
    pygame.draw.line(surface, (255, 255, 255, 40), (current_x-1, start_y), (current_x-1, start_y + height), 1)

    # Δαχτυλίδι στόχευσης (Clean HUD)
    pygame.draw.circle(surface, (255, 255, 255, 80), (int(current_x), int(current_y)), 7, 1)
    pygame.draw.circle(surface, ai_color, (int(current_x), int(current_y)), 4)
    pygame.draw.circle(surface, (255, 255, 255), (int(current_x), int(current_y)), 2)

    # Glassmorphism Tooltip (Ένα "παγάκι" πάνω από τη γραμμή)
    time_str = f" {int(current_time):02d}:{int((current_time%1)*60):02d} "
    tt_surf = small_font.render(time_str, True, (240, 250, 255))
    tt_rect = tt_surf.get_rect(midbottom=(int(current_x), start_y - 10))
    
    bg_rect = tt_rect.inflate(14, 8)
    bg_rect.y += 2
    
    # Drop Shadow 
    pygame.draw.rect(surface, (0, 0, 0, 60), bg_rect.move(0, 4), border_radius=8)
    # Frosted Panel
    pygame.draw.rect(surface, (40, 50, 70, 200), bg_rect, border_radius=8)
    # White Glass Edge
    pygame.draw.rect(surface, (255, 255, 255, 40), bg_rect, width=1, border_radius=8)
    
    # Glass Pointer
    t_pts = [(current_x - 4, start_y - 8), (current_x + 4, start_y - 8), (current_x, start_y - 4)]
    pygame.draw.polygon(surface, (40, 50, 70, 200), t_pts)
    pygame.draw.aalines(surface, (255, 255, 255, 40), False, [(current_x - 4, start_y - 8), (current_x, start_y - 4), (current_x + 4, start_y - 8)])
    
    surface.blit(tt_surf, tt_rect)

    # ---------------- Υπόμνημα (Floating Glow Legends) ----------------
    lx, ly = start_x + 15, start_y + 12
    # Dot & Text
    pygame.draw.circle(surface, ai_color, (lx, ly + 6), 4)
    pygame.draw.circle(surface, (255, 255, 255), (lx, ly + 6), 1)
    surface.blit(small_font.render("AI Plan", True, (200, 220, 240)), (lx + 10, ly))
    
    lx += 80
    pygame.draw.circle(surface, pl_color, (lx, ly + 6), 4)
    pygame.draw.circle(surface, (255, 255, 255), (lx, ly + 6), 1)
    surface.blit(small_font.render("User", True, (200, 220, 240)), (lx + 10, ly))

# ---------------- Init ----------------
ai_values=[ai_circadian(h) for h in range(24)]
player_values=[ai_values[h] for h in range(24)]
fraction = 0.0
running = True

while running:
    clock.tick(fps)
    fraction += time_speed * speed_factor
    while fraction >=1:
        fraction -=1
        hour = (hour + 1) % 24
    while fraction <0:
        fraction +=1
        hour = (hour - 1) % 24

    animated_hour = hour + fraction

    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_UP: player_offset+=5
            if event.key==pygame.K_DOWN: player_offset-=5
            if event.key==pygame.K_a: ai_enabled=not ai_enabled
            if event.key==pygame.K_r: player_offset=0
            if event.key==pygame.K_f: speed_factor=5.0
            if event.key==pygame.K_s: speed_factor=1.0
            if event.key==pygame.K_w: speed_factor=-2.0

    ai_brightness = ai_circadian(animated_hour)
    final_brightness = ai_brightness+player_offset if ai_enabled else player_offset
    final_brightness = max(0,min(100,final_brightness))
    player_values[int(hour)] = final_brightness

    kelvin = brightness_to_kelvin(final_brightness)
    rgb = kelvin_to_rgb(kelvin)

    # ---------------- Σχεδίαση Background ----------------
    draw_sky_gradient(animated_hour)
    draw_stars(animated_hour)
    draw_sun_moon(animated_hour)
    draw_horizon()

    # ---------------- UI Dashboard (Glassmorphism) ----------------
    panel_width = 480
    panel_height = HEIGHT - 40
    panel_x, panel_y = 20, 20
    
    # Floating panel surface
    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (25, 28, 32, 220), (0, 0, panel_width, panel_height), border_radius=16)
    pygame.draw.rect(panel, (60, 65, 75, 255), (0, 0, panel_width, panel_height), width=1, border_radius=16)
    
    # Header
    title = font_large.render("Circadian Simulator", True, (255, 255, 255))
    panel.blit(title, (30, 20))
    pygame.draw.line(panel, (80, 85, 95), (30, 65), (panel_width - 30, 65), 1)

    if kelvin<3500: light_type="WARM"
    elif kelvin<5000: light_type="NEUTRAL"
    else: light_type="COOL"
    circ_error = abs(final_brightness - ai_brightness)

    sr_h, sr_m = int(SUNRISE), int((SUNRISE%1)*60)
    ss_h, ss_m = int(SUNSET), int((SUNSET%1)*60)
    
    # Formatted Info Map
    info_data = [
        ("Location", LOCATION),
        ("Sun", f"▲ {sr_h:02d}:{sr_m:02d}   ▼ {ss_h:02d}:{ss_m:02d}"),
        ("Sim Time", f"{int(animated_hour):02d}:{int((animated_hour%1)*60):02d}"),
        ("AI Target Brightness", f"{ai_brightness:.1f} %"),
        ("User Adjustment", f"{player_offset:+} %"),
        ("Final Output Brightness", f"{final_brightness:.1f} %"),
        ("Color Temp.", f"{kelvin} K  ({light_type})"),
        ("Automated Mode", "ACTIVE" if ai_enabled else "MANUAL"),
        ("Circadian Error", f"{circ_error:.1f} %")
    ]
    
    y_offset = 80
    for label, val in info_data:
        lbl_surf = font.render(label, True, (160, 165, 175))
        if str(val) == "ACTIVE":
            val_color = (100, 255, 100)
        elif str(val) == "MANUAL":
            val_color = (255, 150, 50)
        else:
            val_color = (240, 240, 245)
        val_surf = font.render(str(val), True, val_color)
        
        panel.blit(lbl_surf, (30, y_offset))
        panel.blit(val_surf, (250, y_offset))
        y_offset += 28

    # -- Smart Lamp Bars --
    bar_start_y = y_offset + 30
    bar_height = 12
    bar_width = panel_width - 60
    
    def draw_bar(surf, label, y, pct, color):
        surf.blit(small_font.render(label, True, (200, 205, 215)), (30, y - 18))
        pygame.draw.rect(surf, (40, 45, 55), (30, y, bar_width, bar_height), border_radius=bar_height//2)
        filled = max(bar_height, int(bar_width * pct))
        if pct > 0:
            pygame.draw.rect(surf, color, (30, y, filled, bar_height), border_radius=bar_height//2)

    # Brightness Bar
    draw_bar(panel, "Lamp Brightness", bar_start_y, final_brightness/100, (255, 230, 100))
    
    # Temp Bar
    temp_perc = max(0.01, min(1.0, (kelvin-2700)/(6500-2700)))
    draw_bar(panel, "Color Temperature (Warm → Cool)", bar_start_y + 50, temp_perc, (120, 200, 255))
    
    # RGB Preview
    panel.blit(small_font.render("Light Output Color", True, (200, 205, 215)), (30, bar_start_y + 100 - 18))
    pygame.draw.rect(panel, rgb, (30, bar_start_y + 100, bar_width, bar_height*2), border_radius=6)
    pygame.draw.rect(panel, (255, 255, 255, 100), (30, bar_start_y + 100, bar_width, bar_height*2), width=1, border_radius=6)

    # -- Keybinds --
    keybinds = [
        "Controls:  [↑/↓] Adjust Offset  |  [A] Toggle AI  |  [R] Reset",
        "                 [F] Fast Forward  |  [W] Rewind  |  [S] Normal Speed"
    ]
    controls_y = bar_start_y + 145
    for i, line in enumerate(keybinds):
        panel.blit(small_font.render(line, True, (130, 135, 145)), (30, controls_y + i*18))

    # ---------------- Graph ----------------
    # (Προσθήκη του `animated_hour` στο draw_graph)
    draw_graph(panel, ai_values, player_values, 30, panel_height - 135, bar_width, 100, animated_hour)

    screen.blit(panel, (panel_x, panel_y))

    pygame.display.flip()

pygame.quit()
