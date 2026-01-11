import pygame
import random
import sys
import math
import os
import wave
import struct

# Inicialização
try:
    pygame.init()
except Exception:
    print("Erro: falha ao inicializar pygame.")
    sys.exit(1)

# Configurações da tela (pixel art)
PIXEL = 20
GRID_W = 40  # largura em blocos
GRID_H = 28  # altura em blocos
LARGURA = GRID_W * PIXEL
ALTURA = GRID_H * PIXEL

tela = None
try:
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Snake Pixel Art - Melhorado")
except Exception:
    print("Erro: falha ao criar a janela do jogo. Verifique o display ou execute em ambiente com GUI.")
    pygame.quit()
    sys.exit(1)

# Cores
PRETO = (10, 10, 12)
VERDE = (50, 220, 100)
VERDE_ESC = (20, 120, 60)
VERMELHO = (255, 80, 80)
BRANCO = (255, 255, 255)
AMARELO = (255, 200, 50)

clock = pygame.time.Clock()
RENDER_FPS = 60

# Inicializar áudio (tenta usar mixer)
try:
    pygame.mixer.init()
    AUDIO_READY = True
except Exception:
    AUDIO_READY = False

# Função para gerar tons simples em WAV (salva em arquivo)
def generate_tone(path, freq=440, duration_ms=200, volume=0.5, samplerate=44100):
    n_samples = int(samplerate * (duration_ms / 1000.0))
    amplitude = int(32767 * volume)
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        for i in range(n_samples):
            t = float(i) / samplerate
            sample = amplitude * math.sin(2.0 * math.pi * freq * t)
            wf.writeframes(struct.pack('<h', int(sample)))

# Garantir pasta de sons
SOUNDS_DIR = os.path.join(os.path.dirname(__file__), 'sounds')
if not os.path.exists(SOUNDS_DIR):
    try:
        os.makedirs(SOUNDS_DIR)
    except Exception:
        pass

# Paths para músicas (adicione seus arquivos aqui):
# Coloque a música do MENU em: sounds/menu.mp3  (ou menu.wav)
MENU_MUSIC_PATH = os.path.join(SOUNDS_DIR, 'menugame.mp3')
# Coloque a música de JOGATINA em: sounds/play.mp3  (ou play.wav)
PLAY_MUSIC_PATH = os.path.join(SOUNDS_DIR, 'jogatina.mp3')
# Coloque a música de GAME OVER em: sounds/over.mp3  (ou over.wav)
OVER_MUSIC_PATH = os.path.join(SOUNDS_DIR, 'gameover.mp3')

# Gerar sons básicos se possível
SOUND_EAT = None
SOUND_GAMEOVER = None
if AUDIO_READY:
    eat_path = os.path.join(SOUNDS_DIR, 'eat.wav')
    over_path = os.path.join(SOUNDS_DIR, 'gameover.wav')
    if not os.path.exists(eat_path):
        generate_tone(eat_path, freq=880, duration_ms=120, volume=0.5)
    if not os.path.exists(over_path):
        generate_tone(over_path, freq=150, duration_ms=700, volume=0.6)
    try:
        SOUND_EAT = pygame.mixer.Sound(eat_path)
        SOUND_GAMEOVER = pygame.mixer.Sound(over_path)
    except Exception:
        SOUND_EAT = None
        SOUND_GAMEOVER = None
    # fallback: se não houver arquivos de música o gerador simples de tom será usado quando necessário
    # (não o tocamos automaticamente aqui)

# Funções auxiliares globais para tocar/parar música (seguras se mixer não estiver pronto)
def play_music_file(path, loops=-1):
    if not AUDIO_READY:
        return False
    try:
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.45)
            pygame.mixer.music.play(loops)
            return True
    except Exception:
        pass
    return False

def stop_music():
    if not AUDIO_READY:
        return
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

# Fonte
fonte = pygame.font.SysFont("arial", 24)

# Helper para texto pixelado (render pequeno e escala)
def render_pixel_text(text, small_size=14, scale=3, color=BRANCO):
    small_font = pygame.font.SysFont("arial", small_size)
    surf = small_font.render(text, True, color)
    w, h = surf.get_size()
    surf = pygame.transform.scale(surf, (w*scale, h*scale))
    return surf

# Highscore utilities
HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), 'highscore.txt')
def get_highscore():
    try:
        with open(HIGHSCORE_FILE, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return 0

def save_highscore(score):
    try:
        cur = get_highscore()
        if score > cur:
            with open(HIGHSCORE_FILE, 'w') as f:
                f.write(str(score))
    except Exception:
        pass

# Utilitários
def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))

def desenhar_bloco(cor, x, y, size=PIXEL):
    pygame.draw.rect(tela, cor, (int(x), int(y), int(size), int(size)))

# Partículas para efeito ao comer
class Particle:
    def __init__(self, pos, color):
        self.x, self.y = pos
        ang = random.uniform(0, math.tau)
        speed = random.uniform(1, 4)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.life = random.uniform(400, 900)
        self.age = 0
        self.color = color

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt/16
        self.y += self.vy * dt/16

    def draw(self, surf):
        t = max(0, 1 - self.age / self.life)
        if t <= 0: return
        alpha = int(255 * t)
        r = max(1, int(3 * t))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x - r), int(self.y - r)))

# Cenas (temas) e decoração animada simples
SCENES = [
    {"bg": (12, 18, 30), "deco": "stars"},
    {"bg": (8, 40, 20), "deco": "leaves"},
    {"bg": (30, 12, 18), "deco": "embers"}
]

def draw_scene(scene, t):
    bg = scene["bg"]
    tela.fill(bg)
    deco = scene["deco"]
    if deco == "stars":
        for i in range(25):
            x = (i * 47 + int(t*30)) % LARGURA
            y = (i * 71 + int(math.sin((i+t)*0.3)*20)) % ALTURA
            c = (200, 220, 255) if (i%7==0) else (150, 180, 220)
            pygame.draw.circle(tela, c, (x, y), 1)
    elif deco == "leaves":
        for i in range(12):
            x = (i * 120 + int(t*10)) % LARGURA
            y = (50 + (i*23) + (math.sin(t*0.5 + i)*20)) % ALTURA
            pygame.draw.ellipse(tela, (30, 100, 40), (x, y, 6, 3))
    elif deco == "embers":
        for i in range(20):
            x = (i * 83 + int(t*50)) % LARGURA
            y = ALTURA - (10 + (i*3) + abs(math.sin(t*0.8 + i)))
            c = (255, 140, 60) if i%3==0 else (200, 80, 40)
            pygame.draw.circle(tela, c, (x, int(y)), 2)


def generate_obstacles(level, avoid_positions=None):
    """Gera obstáculos com base no level; retorna lista de posições (alinhadas ao grid)."""
    avoid_positions = avoid_positions or []
    obstacles = []
    # número de obstáculos cresce com o nível
    count = min(30, 1 + level * 2)
    tries = 0
    while len(obstacles) < count and tries < count * 10:
        tries += 1
        gx = random.randrange(0, GRID_W) * PIXEL
        gy = random.randrange(0, GRID_H) * PIXEL
        pos = (gx, gy)
        if pos in obstacles or pos in avoid_positions:
            continue
        obstacles.append(pos)
    return obstacles


def draw_obstacles(obstacles):
    for ox, oy in obstacles:
        pygame.draw.rect(tela, (60, 60, 70), (ox, oy, PIXEL, PIXEL))
        # pequeno destaque
        pygame.draw.rect(tela, (100, 100, 110), (ox+2, oy+2, PIXEL-4, PIXEL-4), 1)

# Tela de Game Over
def game_over(score):
    # parar qualquer música de jogatina e tocar música de game over (adicione sounds/over.mp3)
    try:
        stop_music()
    except Exception:
        pass
    try:
        play_music_file(OVER_MUSIC_PATH, loops=0)
    except Exception:
        pass
    # tocar efeito sonoro de game over curto, se disponível
    if SOUND_GAMEOVER:
        try:
            SOUND_GAMEOVER.play()
        except Exception:
            pass
    texto = fonte.render(f"GAME OVER  -  Score: {score}", True, VERMELHO)
    tela.blit(texto, (LARGURA//2 - texto.get_width()//2, ALTURA//2 - 12))
    pygame.display.update()
    pygame.time.delay(2000)
    save_highscore(score)
    try:
        if AUDIO_READY:
            pygame.mixer.music.stop()
    except Exception:
        pass
    pygame.quit()
    sys.exit()

def clamp_dir(new, old):
    # impede reversão instantânea
    if (new[0] == -old[0] and new[1] == -old[1]):
        return old
    return new

def jogo():
    # estado inicial
    cobra = [(5*PIXEL, 5*PIXEL), (4*PIXEL, 5*PIXEL), (3*PIXEL, 5*PIXEL)]
    direcao = (PIXEL, 0)
    pending_dir = direcao

    comida = (
        random.randrange(0, LARGURA, PIXEL),
        random.randrange(0, ALTURA, PIXEL)
    )

    # nível inicial e obstáculos (gera alguns obstáculos iniciais)
    level = 1
    obstacles = generate_obstacles(level, avoid_positions=cobra + [comida])

    particles = []

    score = 0
    scene_index = 0
    scene = SCENES[scene_index]
    transitioning = False
    trans_alpha = 0

    move_delay = START_MOVE_DELAY if 'START_MOVE_DELAY' in globals() else 140  # ms por passo (reduz com score)
    move_timer = 0

    running = True
    while running:
        dt = clock.tick(RENDER_FPS)
        move_timer += dt
        t = pygame.time.get_ticks() / 1000.0

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_w, pygame.K_UP):
                    pending_dir = clamp_dir((0, -PIXEL), direcao)
                if evento.key in (pygame.K_s, pygame.K_DOWN):
                    pending_dir = clamp_dir((0, PIXEL), direcao)
                if evento.key in (pygame.K_a, pygame.K_LEFT):
                    pending_dir = clamp_dir((-PIXEL, 0), direcao)
                if evento.key in (pygame.K_d, pygame.K_RIGHT):
                    pending_dir = clamp_dir((PIXEL, 0), direcao)

        # passo lógico da cobra (quando timer atingir delay)
        if move_timer >= move_delay:
            move_timer = 0
            direcao = pending_dir
            nova_cabeca = (
                cobra[0][0] + direcao[0],
                cobra[0][1] + direcao[1]
            )

            # Wrapping nas bordas (não dá game over ao bater na lateral)
            nx = nova_cabeca[0] % LARGURA
            ny = nova_cabeca[1] % ALTURA
            nova_cabeca = (nx, ny)

            # Colisão com o próprio corpo
            if nova_cabeca in cobra:
                game_over(score)

            # Colisão com obstáculos -> fim de jogo
            if nova_cabeca in obstacles:
                game_over(score)

            cobra.insert(0, nova_cabeca)

            # Comer comida
            if nova_cabeca == comida:
                score += 1
                # partículas
                for _ in range(18):
                    particles.append(Particle((comida[0]+PIXEL/2, comida[1]+PIXEL/2), AMARELO))
                # som de comer
                if SOUND_EAT:
                    try:
                        SOUND_EAT.play()
                    except Exception:
                        pass
                # nova comida
                while True:
                    comida = (
                        random.randrange(0, LARGURA, PIXEL),
                        random.randrange(0, ALTURA, PIXEL)
                    )
                    if comida not in cobra and comida not in obstacles:
                        break

                # ajustar dificuldade e mudança de cena a cada 5 pontos
                if score % 5 == 0:
                    move_delay = max(60, move_delay - 10)
                    scene_index = (scene_index + 1) % len(SCENES)
                    transitioning = True
                    trans_alpha = 0
                    # aumentar nível e gerar novos obstáculos
                    level += 1
                    obstacles = generate_obstacles(level, avoid_positions=cobra + [comida])
            else:
                cobra.pop()

        # atualizar partículas
        for p in particles[:]:
            p.update(dt)
            if p.age >= p.life:
                particles.remove(p)

        # desenhar cena com possível transição
        draw_scene(SCENES[scene_index], t)

        # Desenhar comida com pulso
        pulse = 1 + 0.15 * math.sin(t * 8)
        comida_rect_size = PIXEL * pulse
        comida_x = comida[0] + (PIXEL - comida_rect_size) / 2
        comida_y = comida[1] + (PIXEL - comida_rect_size) / 2
        s = pygame.Surface((int(comida_rect_size), int(comida_rect_size)), pygame.SRCALPHA)
        pygame.draw.rect(s, VERMELHO, (0, 0, int(comida_rect_size), int(comida_rect_size)), border_radius=4)
        tela.blit(s, (int(comida_x), int(comida_y)))

        # desenhar obstáculos
        draw_obstacles(obstacles)

        # desenhar cobra com gradiente
        for i, parte in enumerate(cobra):
            tseg = i / max(1, len(cobra)-1)
            cor = lerp_color(VERDE, VERMELHO if i==0 else VERDE_ESC, 1 - tseg*0.6)
            desenhar_bloco(cor, parte[0], parte[1])

        # olhos na cabeça
        head = cobra[0]
        hx, hy = head[0], head[1]
        eye_offset = 6
        ex = hx + (PIXEL//2) + (direcao[0]//PIXEL)*eye_offset - 4
        ey = hy + (PIXEL//2) + (direcao[1]//PIXEL)*eye_offset - 4
        pygame.draw.circle(tela, BRANCO, (int(ex), int(ey)), 3)
        pygame.draw.circle(tela, (30,30,30), (int(ex+1), int(ey)), 1)

        # desenhar partículas
        for p in particles:
            p.draw(tela)

        # HUD: score e dicas
        txt = fonte.render(f"Score: {score}", True, BRANCO)
        tela.blit(txt, (8, 8))
        lvl = fonte.render(f"Speed: {round(1000/move_delay)}", True, BRANCO)
        tela.blit(lvl, (8, 36))
        level_txt = fonte.render(f"Level: {level}", True, BRANCO)
        tela.blit(level_txt, (8, 64))

        # transição de cena (fade)
        if transitioning:
            trans_alpha += dt / 4
            if trans_alpha >= 255:
                trans_alpha = 255
                transitioning = False
            fade = pygame.Surface((LARGURA, ALTURA))
            fade.set_alpha(int(trans_alpha))
            fade.fill((0,0,0))
            tela.blit(fade, (0,0))

        pygame.display.update()

def menu_dificuldade():
    # opções: (nome, grid_w, grid_h, move_delay_start)
    options = [
        ("Bebe Chorao", 30, 20, 180),
        ("Normal", 40, 28, 140),
        ("Tomei no Butico", 50, 36, 90)
    ]
    selected = 1
    while True:
        dt = clock.tick(RENDER_FPS)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                if evento.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                if evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return options[selected]

        # desenhar menu simples
        tela.fill((8,8,12))
        titulo = fonte.render("SNAKE - Escolha a dificuldade", True, BRANCO)
        tela.blit(titulo, (LARGURA//2 - titulo.get_width()//2, 40))
        for i, opt in enumerate(options):
            name = opt[0]
            color = AMARELO if i == selected else BRANCO
            txt = fonte.render(name, True, color)
            tela.blit(txt, (LARGURA//2 - txt.get_width()//2, 120 + i*48))

        hint = fonte.render("Use ↑/↓ e Enter para escolher", True, (180,180,180))
        tela.blit(hint, (LARGURA//2 - hint.get_width()//2, ALTURA - 60))
        pygame.display.update()

def menu_recorde():
    hs = get_highscore()
    showing = True
    while showing:
        dt = clock.tick(RENDER_FPS)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if evento.type == pygame.KEYDOWN:
                showing = False

        tela.fill((4,4,8))
        title = render_pixel_text("RECORDES", small_size=12, scale=4, color=AMARELO)
        tela.blit(title, (LARGURA//2 - title.get_width()//2, 40))
        txt = fonte.render(f"Melhor score: {hs}", True, BRANCO)
        tela.blit(txt, (LARGURA//2 - txt.get_width()//2, 160))
        hint = fonte.render("Pressione qualquer tecla para voltar", True, (180,180,180))
        tela.blit(hint, (LARGURA//2 - hint.get_width()//2, ALTURA - 60))
        pygame.display.update()

def menu_principal():
    options = ["Iniciar", "Recorde", "Dificuldade", "Sair"]
    selected = 0
    # difficulty state
    global CURRENT_DIFFICULTY
    if 'CURRENT_DIFFICULTY' not in globals():
        CURRENT_DIFFICULTY = ("Normal", 40, 28, 140)

    # toca música do menu ao entrar no menu (adicione sounds/menu.mp3)
    try:
        play_music_file(MENU_MUSIC_PATH, loops=-1)
    except Exception:
        pass

    t0 = 0
    while True:
        dt = clock.tick(RENDER_FPS)
        t = pygame.time.get_ticks() / 1000.0
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                if evento.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                if evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    choice = options[selected]
                    if choice == "Iniciar":
                        return "start"
                    if choice == "Recorde":
                        menu_recorde()
                    if choice == "Dificuldade":
                        nome, gw, gh, sd = menu_dificuldade()
                        CURRENT_DIFFICULTY = (nome, gw, gh, sd)
                    if choice == "Sair":
                        pygame.quit(); sys.exit()

        # fundo retro com barras e scanlines
        tela.fill((6,6,12))
        for i in range(0, LARGURA, 8):
            col_val = 20 + int(30 * math.sin((t + i*0.01)))
            # garantir 0-255
            c1 = max(0, min(255, int(col_val)))
            c2 = max(0, min(255, c1 // 2))
            c3 = max(0, min(255, c1 // 3))
            pygame.draw.line(tela, (c1, c2, c3), (i, ALTURA//3), (i, ALTURA), 1)

        # title Atari style
        title_text = "Snake's Eat"
        title_surf = render_pixel_text(title_text, small_size=18, scale=6, color=(255,200,60))
        bob = int(math.sin(t*2) * 6)
        tela.blit(title_surf, (LARGURA//2 - title_surf.get_width()//2, 20 + bob))

        # subtitle pac-man style (pixel feel)
        sub = render_pixel_text("estilo retro", small_size=10, scale=3, color=(200,200,255))
        tela.blit(sub, (LARGURA//2 - sub.get_width()//2, 20 + title_surf.get_height() + bob + 6))

        # painel central para opções
        panel_w, panel_h = 520, 260
        panel_x = LARGURA//2 - panel_w//2
        panel_y = 120
        panel_s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_s.fill((12, 12, 18, 200))
        tela.blit(panel_s, (panel_x, panel_y))
        # opções com animação de destaque
        for i, opt in enumerate(options):
            y = 160 + i*56
            is_sel = (i == selected)
            color = AMARELO if is_sel else BRANCO
            scale = 1.0 + (0.08 * math.sin(t*6 + i)) if is_sel else 1.0
            txt = fonte.render(opt, True, color)
            Tw, Th = txt.get_size()
            txt_s = pygame.transform.rotozoom(txt, 0, scale)
            tela.blit(txt_s, (LARGURA//2 - txt_s.get_width()//2, y))

        # show current difficulty
        diff_txt = fonte.render(f"Dificuldade: {CURRENT_DIFFICULTY[0]}", True, (180,180,180))
        tela.blit(diff_txt, (LARGURA - diff_txt.get_width() - 12, ALTURA - 40))

        # footer
        footer = fonte.render("Fazido por Dante | Made by Dante", True, (150,150,150))
        tela.blit(footer, (LARGURA//2 - footer.get_width()//2, ALTURA - 32))

        pygame.display.update()

def main():
    # menu principal
    while True:
        action = menu_principal()
        if action == 'start':
            # pegar seleção atual
            nome, gw, gh, start_delay = CURRENT_DIFFICULTY
            global PIXEL, GRID_W, GRID_H, LARGURA, ALTURA, tela, START_MOVE_DELAY
            PIXEL = 20
            GRID_W = gw
            GRID_H = gh
            LARGURA = GRID_W * PIXEL
            ALTURA = GRID_H * PIXEL
            tela = pygame.display.set_mode((LARGURA, ALTURA))
            START_MOVE_DELAY = start_delay
            # trocar para música de jogatina (adicione sounds/play.mp3)
            try:
                play_music_file(PLAY_MUSIC_PATH, loops=-1)
            except Exception:
                pass
            jogo()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        try:
            with open(os.path.join(os.path.dirname(__file__), 'error.log'), 'w', encoding='utf-8') as ef:
                traceback.print_exc(file=ef)
        except Exception:
            pass
        sys.exit(1)