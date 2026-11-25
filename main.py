import math, random, wave, array, os
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label 
from kivy.core.window import Window 
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Triangle

RATE = 22050
PTS = {'ast': 10, 'sct': 20, 'shr': 50}

# -------------SOUND SYNTHESIS--------------
def wv(kind, phase):
    p = phase % 1
    if kind == 'sq':
        return 1 if p < 0.5 else -1
    if kind == 'tri':
        return 4 * abs(p - 0.5) - 1
    if kind == 'noise':
        return random.uniform(-1, 1)
    return math.sin(2 * math.pi * p)
    
def fx(f0, f1, dur, vol, kind):
    n = int(RATE * dur)
    out, ph = [], 0
    for i in range(n):
        t = i / n
        ph += (f0 + (f1 - f0) * t) / RATE
        out.append(wv(kind, ph) * (1 - t) * vol)
    return out
    
def build_music():
    step, steps = 0.18, 32
    n = int(RATE * step * steps)
    mix = [0.0] * n
    bass = [110, 87.31, 130.81, 98]
    chords = [(220, 261.63, 329.63), (174.61, 220, 261.63),
              (261.63, 329.63, 392), (196, 246.94, 293.66)]
              
    def note(s, f, dur, vol, kind):
        st, m = int(s * step * RATE), int(dur * RATE)
        for i in range(m):
            if st + i >= n:
                break 
            mix[st + i] += wv(kind, i * f / RATE) * (1 - i / m) * vol
            
    for s in range(steps):
        bar = s // 8
        if s % 2 == 0:
            note(s, bass[bar], step * 2, 0.3, 'tri')
        note(s, chords[bar][s % 3], step, 0.12, 'sq')
    return mix
    
def save_wav(path, samples):
    buf = array.array('h', (int(max(-1, min(1, v)) * 32767) for v in samples))
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())
        
def make_sounds(folder):
    specs = {
        'shoot': lambda: fx(900, 300, 0.12, 0.15, 'sq'),
        'boom': lambda: fx(200, 40, 0.35, 0.5, 'noise'),
        'hit': lambda: fx(300, 80, 0.25, 0.4, 'sq'),
        'over': lambda: fx(400, 60, 0.9, 0.4, 'tri'),
        'music': build_music,
    }
    for name, fn in specs.items():
        p = os.path.join(folder, name + '.wav')
        if not os.path.exists(p):
            save_wav(p, fn())
            
# -----------GAME----------
class Game(Widget):
    def __init__(self, folder, **kw):
        super().__init__(**kw)
        self.snd = {}
        for n in ('shoot', 'boom', 'hit', 'over', 'music'):
            self.snd[n] = SoundLoader.load(os.path.join(folder, n + '.wav'))
        self.hi = 0
        self.touching = False
        self.tx = self.ty = 0
        self.time = 0
        self.over_t = 0
        W, H = Window.size 
        self.stars = [[random.random() * W, random.random() * H,
                       random.choice((1, 2, 3))] for _ in range(60)]
        self.score_lbl = Label(size_hint=(None, None), halign='left', valign='middle')
        self.over_lbl = Label(size_hint=(None, None), halign='center', valign='middle')
        self.add_widget(self.score_lbl)
        self.add_widget(self.over_lbl)
        m = self.snd['music']
        if m:
            m.loop = True
        self.reset()
        Clock.schedule_interval(self.update, 1 / 60)
        
    def sfx(self, name):
        s = self.snd.get(name)
        if s:
            s.stop()
            s.play()
            
    def music_vol(self, v):
        m = self.snd.get('music')
        if m:
            m.volume = v
            
    def pause_music(self):
        m = self.snd.get('music')
        if m:
            m.stop()
            
    def resume_music(self):
        m = self.snd.get('music')
        if m:
            m.play()
            
    def reset(self):
        W, H = Window.size 
        self.px, self.py = W / 2, H * 0.75
        self.tx, self.ty = self.px, self.py
        self.bul, self.ebul, self.en, self.parts = [], [], [], []
        self.score, self.lives, self.state = 0, 3, 'play'
        self.spawn, self.last, self.inv = 1.0, 0, 0
        self.over_lbl.text = ''
        self.music_vol(0.5)
        self.resume_music()
        
    def burst(self, x, y, col, n=12):
        S = Window.width / 480
        for _ in range(n):
            a, s = random.random() * 6.28, random.uniform(60, 260) * S
            self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s, 0.5, col])
            
    def spawn_enemy(self, W, S):
        r = random.random()
        x = random.uniform(40 * S, W - 40 * S)
        if self.score < 150 or r < 0.5:
            rad = random.uniform(20, 38) * S
            self.en.append(dict(k='ast', x=x, x0=x, y=-50, r=rad, t=0, cd=0,
                                vy=random.uniform(140, 240) * S,
                                hp=2 if rad > 30 * S else 1))
        elif r < 0.8:
            self.en.append(dict(k='sct', x=x, x0=min(max(x, 100 * S), W - 100 * S),
                                y=-50, r=20 * S, t=0, cd=0, vy=170 * S, hp=1))
        else:
            self.en.append(dict(k='shr', x=x, x0=x, y=-50, r=28 * S, t=0, cd=1,
                                vy=80 * S, hp=3))
    
    def hurt(self):
        self.lives -= 1
        self.inv = 1.5
        self.sfx('hit')
        self.burst(self.px, self.py, (0.31, 0.78, 1), 20)
        if self.lives <= 0:
            self.state = 'over'
            self.hi = max(self.hi, self.score)
            self.sfx('over')
            self.music_vol(0.15)
            self.over_t = self.time 
            
    # ----touch----
    def on_touch_down(self, t):
        self.touching = True
        self.tx, self.ty = t.x, Window.height - t.y
        if self.state == 'over' and self.time - self.over_t > 0.8:
            self.reset()
        return True
        
    def on_touch_move(self, t):
        self.tx, self.ty = t.x, Window.height - t.y
        return True
        
    def on_touch_up(self, t):
        self.touching = False
        return True
        
    # ----- update -----
    def update(self, dt):
        dt = min(dt, 0.05)
        self.time += dt
        W, H = Window.size
        S = W / 480
        for s in self.stars:
            s[1] += s[2] * 60 * S * dt
            if s[1] > H:
                s[0], s[1] = random.random() * W, 0
                
        if self.state == 'play':
            if self.touching:
                k = min(1, 15 * dt)
                self.px += (self.tx - self.px) * k
                self.py += (self.ty - 120 * S - self.py) * k
            self.px = min(max(self.px, 20 * S), W - 20 * S)
            self.py = min(max(self.py, 40 * S), H - 30 * S)
            
            if self.time - self.last > 0.22:
                self.bul.append([self.px, self.py - 24 * S])
                self.sfx('shoot')
                self.last = self.time
            self.inv = max(0, self.inv - dt)
            
            self.spawn -= dt
            if self.spawn <= 0:
                self.spawn_enemy(W, S)
                self.spawn = max(0.35, 1.0 - self.score / 1500)
                
            for b in self.bul:
                b[1] -= 700 * S * dt
            for b in self.ebul:
                b[1] += 320 * S * dt
            for e in self.en:
                e['t'] += dt
                e['y'] += e['vy'] * dt
                if e['k'] == 'sct':
                    e['x'] = e['x0'] + math.sin(e['t'] * 3) * 90 * S
                if e['k'] == 'shr':
                    e['cd'] -= dt
                    if e['cd'] <= 0 and e['y'] > 0:
                        e['cd'] = 1.4
                        self.ebul.append([e['x'], e['y'] + e['r']])
                        
            for b in self.bul[:]:
                for e in self.en:
                    if math.hypot(b[0] - e['x'], b[1] - e['y']) < e['r'] + 6 * S:
                        self.bul.remove(b)
                        e['hp'] -= 1
                        if e['hp'] <= 0:
                            self.score += PTS[e['k']]
                            self.en.remove(e)
                            self.sfx('boom')
                            self.burst(e['x'], e['y'], (1, 0.63, 0.24))
                        break 
                        
            if self.inv <= 0:
                for e in self.en[:]:
                    if math.hypot(self.px - e['x'], self.py - e['y']) < e['r'] + 14 * S:
                        self.en.remove(e)
                        self.burst(e['x'], e['y'], (1, 0.63, 0.24))
                        self.hurt()
                        break 
                for b in self.ebul[:]:
                    if self.inv <= 0 and self.state == 'play' and \
                            math.hypot(self.px - b[0], self.py - b[1]) < 20 * S:
                        self.ebul.remove(b)
                        self.hurt()
                        
            self.bul = [b for b in self.bul if b[1] > -20]
            self.ebul = [b for b in self.ebul if b[1] < H + 20]
            self.en = [e for e in self.en if e['y'] < H + 80]
            
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]
        self.draw(W, H, S)
        
    # ------ draw -------
    def draw(self, W, H, S):
        self.score_lbl.font_size = 32 * S
        self.score_lbl.size = (300 * S, 50 * S)
        self.score_lbl.text_size = self.score_lbl.size 
        self.score_lbl.pos = (15 * S, H - 60 * S)
        self.score_lbl.text = 'Score ' + str(self.score)
        self.over_lbl.font_size = 36 * S
        self.over_lbl.size = (W, 300 * S)
        self.over_lbl.text_size = self.over_lbl.size
        self.over_lbl.pos = (0, H / 2 - 150 * S)
        if self.state == 'over':
            self.over_lbl.text = ('GAME OVER\nScore ' + str(self.score) +
                                  '\nBest ' + str(self.hi) + '\nTap to play again')
        
        c = self.canvas.before
        c.clear()
        with c:
            Color(0, 0, 0, 1)
            Rectangle(pos=(0, 0), size=(W, H))
            for s in self.stars:
                v = (90 + s[2] * 55) / 255
                Color(v, v, v, 1)
                d = s[2] * 2
                Ellipse(pos=(s[0], H - s[1]), size=(d, d))
            for e in self.en:
                x, y, r = e['x'], H - e['y'], e['r']
                if e['k'] == 'ast':
                    Color(0.51, 0.47, 0.43, 1)
                    Ellipse(pos=(x - r, y - r), size=(2 * r, 2 * r))
                elif e['k'] == 'sct':
                    Color(0.9, 0.24, 0.24, 1)
                    Triangle(points=[x - r, y + r, x + r, y + r, x, y - r])
                else:
                    Color(0.67, 0.27, 0.86, 1)
                    Ellipse(pos=(x - r, y - r), size=(2 * r, 2 * r))
                    Color(1, 1, 1, 1)
                    Rectangle(pos=(x - 4 * S, y - r - 8 * S), size=(8 * S, r + 8 * S))
            Color(0.47, 1, 1, 1)
            for b in self.bul:
                Rectangle(pos=(b[0] - 3 * S, H - b[1] - 10 * S), size=(6 * S, 20 * S))
            Color(1, 0.35, 0.35, 1)
            for b in self.ebul:
                Ellipse(pos=(b[0] - 7 * S, H - b[1] - 7 * S), size=(14 * S, 14 * S))
            for p in self.parts:
                Color(*p[5], 1)
                r = max(1, 4 * S * p[4] * 2)
                Ellipse(pos=(p[0] - r, H - p[1] - r), size=(2 * r, 2 * r))
            if self.state == 'play' and int(self.inv * 10) % 2 == 0:
                px, py = self.px, self.py
                Color(0.31, 0.78, 1, 1)
                Triangle(points=[px, H - (py - 24 * S), px - 18 * S, H - (py + 18 * S),
                                 px + 18 * S, H - (py + 18 * S)])
                Color(1, 0.6, 0.2, 1)
                Triangle(points=[px - 6 * S, H - (py + 18 * S), px + 6 * S,
                                 H - (py + 18 * S), px, H - (py + 30 * S)])
            Color(0.31, 0.78, 1, 1)
            for i in range(self.lives):
                x = W - (30 + i * 32) * S
                Triangle(points=[x, H - 18 * S, x - 10 * S, H - 38 * S, x + 10 * S, H - 38 * S])
                
class StarFighter(App):
    def build(self):
        folder = self.user_data_dir
        os.makedirs(folder, exist_ok=True)
        make_sounds(folder)
        self.game = Game(folder)
        return self.game
        
    def on_pause(self):
        self.game.pause_music()
        return True
        
    def on_resume(self):
        self.game.resume_music()
        
StarFighter().run()

