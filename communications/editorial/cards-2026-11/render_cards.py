from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json, math, base64, html, hashlib, zipfile
root=Path(__file__).resolve().parent
(root/'assets').mkdir(exist_ok=True)
# Card copy is deliberately separate from the approved post text.
items=[
('02','С чего начать\nсолнечную станцию?','Start with your\nelectricity use',['Когда расходуется энергия','На что она расходуется','Мощность под профиль объекта'],['When you use electricity','What it powers','Capacity matched to your site'],'01'),
('04','Продумать\nдо монтажа','Plan before\ninstallation',['Размещение','Подключение','Безопасность','Обслуживание'],['Placement','Connection','Safety','Maintenance'],'02'),
('06','У каждой гостиницы\nсвой режим','Every hotel has\nits own routine',['Потребление → подбор мощности','Генерация ↔ нагрузка'],['Consumption → sizing','Generation ↔ load'],'03'),
('09','Станция\nуже работает?','Already have\na solar installation?',['Обслуживание','Задачи мониторинга'],['Maintenance','Monitoring needs'],'04'),
('11','Один период.\nДва показателя.','One period.\nTwo measurements.',['Генерация','Нагрузка'],['Generation','Load'],'05'),
('13','Как описать\nзадачу обслуживания','Describe your\nmaintenance enquiry',['Что заметили?','Когда началось?','Повторяется ли?'],['What did you notice?','When did it start?','Does it happen repeatedly?'],'06'),
('16','Сочи.\nКраснодарский край.','Sochi.\nKrasnodar Krai.',['Основной регион работы','Кавказ — по запросу'],['Our main service area','Caucasus — on request'],'07'),
('18','Дневник\nпотребления','Your electricity\nuse diary',['Утро','День','Вечер'],['Morning','Afternoon','Evening'],'08'),
('20','Один разговор.\nОдин главный вопрос.','One conversation.\nOne main question.',['После разговора с инженером','я хочу понять…'],['After speaking with an engineer,','I want to understand…'],'09'),
('23','У станции есть\nистория измерений','A station has\na measurement history',['История показаний','Учёт энергии','Данные для проверки'],['Measurement history','Energy accounting','Data for further review'],'10'),
('25','Данные и проверка:\nразные этапы','Data and assessment:\nseparate stages',['GSun → подготовка данных','Уполномоченные организации','→ официальные процедуры'],['GSun → data preparation','Authorised organisations','→ official procedures'],'11'),
('27','Работаете\nс гостиницами?','Working\nwith hotels?',['Проектирование','Установка','Обслуживание'],['Design','Installation','Maintenance'],'12'),
('30','С какой задачей\nвы сейчас?','What are you\nworking on?',['Новая станция','Обслуживание','Мониторинг'],['A new installation','Maintenance','Monitoring'],'13')]
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def F(n,b=False):return ImageFont.truetype(bold if b else font,n)
manifest=[]; previews=[]
for day,ru,en,bullets,english,pid in items:
 for lang,title,lines in [('ru',ru,bullets),('en',en,english)]:
  dark=int(pid) in (1,5,7,9,11,13)
  bg='#153E35' if dark else '#F6F3EA';fg='#F6F3EA' if dark else '#153E35';muted='#B8CFC0' if dark else '#56776B'; accent='#DBB560'
  im=Image.new('RGB',(1080,1080),bg);d=ImageDraw.Draw(im)
  d.text((64,48),'GSun',font=F(49,True),fill=fg);d.text((226,65),'ENERGY',font=F(20),fill=accent)
  d.text((64,146),'СОЛНЕЧНАЯ ЭНЕРГИЯ / ПРАКТИКА' if lang=='ru' else 'SOLAR ENERGY / FIELD NOTES',font=F(19),fill=muted)
  # Restrained solar motif, no fabricated readings or client site.
  cx,cy=925,105
  d.ellipse((cx-26,cy-26,cx+26,cy+26),outline=accent,width=3)
  for k in range(12):
   a=math.pi*k/6;d.line((cx+37*math.cos(a),cy+37*math.sin(a),cx+50*math.cos(a),cy+50*math.sin(a)),fill=accent,width=3)
  size=60
  while max(d.textlength(x,font=F(size,True)) for x in title.split('\n'))>952:size-=1
  d.multiline_text((64,215),title,font=F(size,True),fill=fg,spacing=12)
  d.line((64,416,1016,416),fill=muted,width=1)
  if pid=='08':
   for j,line in enumerate(lines):
    x=64+j*324;d.rounded_rectangle((x,486,x+304,826),radius=22,outline=muted,width=2)
    d.text((x+22,515),line,font=F(27,True),fill=fg)
    for y in (620,690,760):d.line((x+22,y,x+280,y),fill=muted,width=1)
  elif pid=='05':
   for j,line in enumerate(lines):
    x=64+j*488;d.rounded_rectangle((x,498,x+464,780),radius=28,outline=muted,width=2)
    d.text((x+26,530),line,font=F(33,True),fill=fg)
    # abstract outlined circles, not a graph
    d.ellipse((x+175,620,x+255,700),outline=accent,width=4)
   d.text((64,819),'Вопрос для анализа, не показания станции' if lang=='ru' else 'An analysis prompt, not station readings',font=F(21),fill=muted)
  elif pid in ('09','11'):
   y=500
   for j,line in enumerate(lines):
    size2=33
    while d.textlength(line,font=F(size2))>940:size2-=1
    d.text((64,y),line,font=F(size2,j==0),fill=fg if j==0 else muted)
    y+=85
   if pid=='09':
    d.rounded_rectangle((64,730,1016,855),radius=16,outline=muted,width=2)
  else:
   y=487
   for j,line in enumerate(lines):
    d.text((64,y+3),f'{j+1:02}',font=F(22),fill=accent)
    size2=31
    while d.textlength(line,font=F(size2))>864:size2-=1
    d.text((126,y),line,font=F(size2),fill=fg)
    d.line((126,y+63,1016,y+63),fill=muted,width=1)
    y+=92
  d.line((64,942,1016,942),fill=muted,width=1)
  d.text((64,971),'ceo@gsun.io',font=F(24),fill=fg)
  d.text((830,976),f'GSUN / {pid}',font=F(20),fill=muted)
  name=f'gsun-2026-11-{pid}-{lang}.png';p=root/'assets'/name;im.save(p,optimize=True)
  manifest.append({'post_id':f'2026-11-{pid}','date':f'2026-11-{day}','language':lang,'file':'assets/'+name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'kind':'illustration','origin':'Original programmatic editorial card; no client photo','approval':'PENDING_OWNER_VISUAL_REVIEW'})
  previews.append((pid,lang,p))
# Contact sheet RU
sheet=Image.new('RGB',(1200,1610),'#E8E8DF');sd=ImageDraw.Draw(sheet)
for i,(_,lang,p) in enumerate([x for x in previews if x[1]=='ru']):
 x=15+(i%4)*298;y=15+(i//4)*395
 thumb=Image.open(p).resize((280,280));sheet.paste(thumb,(x,y))
 sd.text((x,y+290),f"{items[i][0]}.11 · №{items[i][-1]}",font=F(19),fill='#153E35')
sheet.save(root/'overview.jpg',quality=90)
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
# Standalone local preview of paired image variants; no remote dependencies or publication controls.
sections=[]
for i,item in enumerate(items):
 day,ru,en,_,_,pid=item
 blocks=[]
 for lang in ('ru','en'):
  p=root/'assets'/f'gsun-2026-11-{pid}-{lang}.png'
  blocks.append(f'<figure data-lang="{lang}"><img alt="{html.escape(ru.replace(chr(10)," "))} — {lang.upper()}" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"><figcaption>{lang.upper()} · 1080 × 1080</figcaption></figure>')
 sections.append(f'<article><h2>{day} ноября · пост {pid}</h2><div class="pair">'+''.join(blocks)+'</div></article>')
(root/'preview.html').write_text('''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GSun · ноябрь 2026 · карточки</title><style>body{margin:0;background:#f6f3ea;color:#153e35;font:17px system-ui}header,main{max-width:1180px;margin:auto;padding:24px}header{position:sticky;top:0;background:#f6f3eaf5;border-bottom:1px solid #cbd4cb;z-index:1}h1{margin:0 0 12px;font-size:30px}p{line-height:1.5}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;border-radius:16px}figcaption{padding:10px 0;color:#56776b}article{margin-bottom:48px}button{padding:10px 20px;border:1px solid #153e35;background:white;color:#153e35;border-radius:30px;margin-right:8px;cursor:pointer}button[aria-pressed=true]{background:#153e35;color:white}@media(max-width:650px){.pair{grid-template-columns:1fr}header,main{padding:16px}}body.ru figure[data-lang=en],body.en figure[data-lang=ru]{display:none}body.ru .pair,body.en .pair{grid-template-columns:minmax(0,650px)}button:focus-visible{outline:3px solid #b18a3b}</style><header><h1>GSun / визуальная редакция</h1><p>Ноябрь 2026 · 13 публикаций · макеты для согласования</p><nav><button data-view="both" aria-pressed="true">RU + EN</button><button data-view="ru" aria-pressed="false">RU</button><button data-view="en" aria-pressed="false">EN</button></nav></header><main><p>Карточки подготовлены по темам V5. Это локальный предпросмотр изображений: тексты постов на VPS не изменены, изображения к очереди не подключены. Полные подписи здесь не воспроизводятся. Перед подключением нужно проверить изображения вместе с актуальными подписями и заново согласовать пакет.</p>'''+''.join(sections)+'''</main><script>document.querySelectorAll('button').forEach(b=>b.onclick=()=>{document.body.className=b.dataset.view;document.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))})</script></html>''')
(root/'README.txt').write_text('GSun — карточки ноября 2026, visual V1\n\nОткройте preview.html двойным щелчком. Интернет не нужен.\n26 PNG: 13 RU и 13 EN, 1080×1080. overview.jpg — обзор RU.\nЭто шаблонная редакционная графика, а не фотографии клиентов.\nНа VPS ничего не изменено и не опубликовано.\nПеред подключением: сопоставить с реальным V5, проверить подпись «Иллюстрация» (требование текущего runtime), заново проверить изменённые подписи и согласовать новый пакет. Не переносить старый review.posts_hash на изменённые посты.\nRU/EN изображения пока выбираются отдельно: текущая очередь имеет только один media_id на пост.\nШрифт DejaVu Sans; сведения о лицензии в FONT-LICENSE.txt.\n')
license_path=Path('/usr/share/doc/fonts-dejavu-core/copyright')
if license_path.exists():(root/'FONT-LICENSE.txt').write_bytes(license_path.read_bytes())
for m in manifest:
 im=Image.open(root/m['file']);assert im.size==(1080,1080);assert (root/m['file']).stat().st_size<10_000_000
print('PASS: 26 PNG images; dimensions, hashes and sizes validated')
