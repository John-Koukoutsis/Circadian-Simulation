import pygame, math, random

pygame.init()

# ---------------- Window ----------------
WIDTH, HEIGHT = 1200, 760
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Circadian Smart Lighting Simulator – Realistic Background")

# ---------------- Fonts ----------------
font = pygame.font.SysFont("arial", 24)
small_font = pygame.font.SysFont("arial", 18)
clock = pygame.time.Clock()

# ---------------- State ----------------
hour = 0
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
    angle = (hour-6)/24*2*math.pi
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
    # Ρεαλιστικά χρώματα ανάλογα με την ώρα
    points = [
        (0,  (5, 5, 20),   (10, 10, 30)),     # Μεσάνυχτα
        (5,  (20, 30, 60), (100, 60, 40)),    # Πριν την αυγή
        (7,  (70, 130, 190), (255, 180, 100)),# Αυγή
        (12, (30, 110, 200), (135, 206, 235)),# Μεσημέρι
        (17, (70, 130, 190), (255, 160, 80)), # Απόγευμα
        (19, (20, 30, 80),  (255, 80, 20)),   # Δύση
        (22, (10, 10, 40),  (20, 20, 50)),    # Βράδυ
        (24, (5, 5, 20),   (10, 10, 30))      # Τέλος ημέρας
    ]
    
    c1_top, c1_bott, c2_top, c2_bott = None, None, None, None
    t = 0
    for i in range(len(points)-1):
        if points[i][0] <= h <= points[i+1][0]:
            p1, p2 = points[i], points[i+1]
            c1_top, c1_bott = p1[1], p1[2]
            c2_top, c2_bott = p2[1], p2[2]
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

    if 6 <= hour_fraction < 18: # Ήλιος
        t = (hour_fraction - 6) / 12
        x = left_x + t * (right_x - left_x)
        y = horizon_y - math.sin(math.pi * t) * arc_h
        
        # Glow Effect
        pygame.draw.circle(glow_surface, (255, 200, 60, 50), (100, 100), 70)
        pygame.draw.circle(glow_surface, (255, 220, 100, 90), (100, 100), 40)
        screen.blit(glow_surface, (x - 100, y - 100))
        
        pygame.draw.circle(screen, (255, 255, 220), (int(x), int(y)), 26)
    else: # Φεγγάρι (η λογική σου για να εμφανίζεται τη νύχτα)
        t = ((hour_fraction - 18) % 24) / 12 if hour_fraction >= 18 else (hour_fraction + 6) / 12
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
    if hour_fraction >= 18 or hour_fraction < 6:
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

def draw_graph(ai_vals,player_vals):
    start_x = 10
    start_y = HEIGHT-120
    width = 400
    height = 100
    pygame.draw.rect(screen,(30,30,30),(start_x,start_y,width,height))
    for i in range(23):
        pygame.draw.line(screen,(0,100,255),
                         (start_x+i*width/24, start_y+height-ai_vals[i]*height/100),
                         (start_x+(i+1)*width/24,start_y+height-ai_vals[i+1]*height/100),2)
        pygame.draw.line(screen,(255,100,0),
                         (start_x+i*width/24, start_y+height-player_vals[i]*height/100),
                         (start_x+(i+1)*width/24,start_y+height-player_vals[i+1]*height/100),2)
    screen.blit(small_font.render("Blue=AI Brightness",True,(0,100,255)),(start_x,start_y-25))
    screen.blit(small_font.render("Orange=Player Brightness",True,(255,100,0)),(start_x+180,start_y-25))

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

    # ---------------- Info Panel (Ακριβώς το δικό σου) ----------------
    panel_width = 420
    panel = pygame.Surface((panel_width, HEIGHT))
    panel.set_alpha(230)
    panel.fill((30,30,30))
    screen.blit(panel, (0,0))

    if kelvin<3500: light_type="WARM LIGHT"
    elif kelvin<5000: light_type="NEUTRAL LIGHT"
    else: light_type="COOL LIGHT"
    circ_error = abs(final_brightness - ai_brightness)

    # -- General Info --
    line_height = 28
    info_lines = [
        f"Time: {int(animated_hour)}:{int((animated_hour%1)*60):02d}",
        f"AI Brightness: {ai_brightness:.1f} %",
        f"Player Offset: {player_offset:+} %",
        f"Final Brightness: {final_brightness:.1f} %",
        f"Color Temp: {kelvin} K",
        f"Light Type: {light_type}",
        f"AI Mode: {'ON' if ai_enabled else 'OFF'}",
        f"Circadian Error: {circ_error:.1f} %"
    ]
    for i, line in enumerate(info_lines):
        screen.blit(font.render(line, True, (255,255,255)), (20, 20 + i*line_height))

    # -- Smart Lamp Bars --
    bar_x = 20
    bar_start_y = 20 + len(info_lines)*line_height + 20
    bar_height = 20
    bar_width = panel_width - 40

    # Brightness
    pygame.draw.rect(screen,(50,50,50),(bar_x, bar_start_y, bar_width, bar_height))
    pygame.draw.rect(screen,(255,255,0),(bar_x, bar_start_y, bar_width*final_brightness/100,bar_height))
    screen.blit(small_font.render("Brightness",True,(255,255,255)), (bar_x, bar_start_y - 22))

    # Temp
    temp_perc = (kelvin-2700)/(6500-2700)*100
    pygame.draw.rect(screen,(50,50,50),(bar_x, bar_start_y+60, bar_width, bar_height))
    pygame.draw.rect(screen,(0,200,255),(bar_x, bar_start_y+60, bar_width*temp_perc/100,bar_height))
    screen.blit(small_font.render("Warm → Cool",True,(255,255,255)),(bar_x, bar_start_y+38))

    # RGB
    pygame.draw.rect(screen,(50,50,50),(bar_x, bar_start_y+100, bar_width, bar_height))
    pygame.draw.rect(screen,rgb,(bar_x, bar_start_y+100, bar_width, bar_height))
    screen.blit(small_font.render("RGB Color",True,(255,255,255)),(bar_x, bar_start_y+78))

    # -- Keybinds --
    keybinds = [
        "Controls:",
        "↑ ↓ Adjust Player Brightness",
        "A Toggle AI",
        "R Reset Player Offset",
        "F Fast Forward",
        "W Rewind",
        "S Normal Speed"
    ]
    keybind_start_y = bar_start_y + 150
    for i, line in enumerate(keybinds):
        screen.blit(small_font.render(line, True, (255,255,255)), (bar_x, keybind_start_y + i*line_height))

    # ---------------- Graph ----------------
    draw_graph(ai_values,player_values)

    pygame.display.flip()

pygame.quit()