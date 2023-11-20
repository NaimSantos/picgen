import requests, appdirs, os, time, sys, json, io
from PIL import Image, ImageFont, ImageDraw
from math import floor

wantedcards = []
deck_to_read = "deck.ydk"

# Read list of cards to be generated from a YDK file
try:
    with open(deck_to_read, 'r') as file:
        for line in file:
            try:
                number = int(line)
                wantedcards.append(number)
            except ValueError:
                print(f"Skipping line {line.strip()} in the deck file (not a valid integer)")
    file.close()
except FileNotFoundError:
    print(f"File not found: {deck_to_read}")

#  Proxy Generation
newCards = []

datapath = os.path.join(appdirs.user_cache_dir('animecards','animecards'), 'carddata.json')

try:
    mtime = os.path.getmtime(datapath)
except FileNotFoundError:
    mtime = 0

if ((time.time() - mtime) > 3600) or ('--force' in sys.argv):
    print('Downloading new carddata.json from ygoprodeck api...')
    with requests.get('https://db.ygoprodeck.com/api/v7/cardinfo.php', stream=True) as r:
        r.raise_for_status()
        os.makedirs(os.path.dirname(datapath), exist_ok=True)
        with open(datapath, 'wb') as f:
            for c in r.iter_content(chunk_size=4*1024*1024):
                f.write(c)

with open(datapath, 'rb') as f:
    carddata = json.load(f)['data']

print('Loaded carddata with %d cards.' % (len(carddata),))

knownCards = set(map(lambda n: int(n[:-4]), os.listdir('output')))

for cardentry in carddata:
    try:
        imagedata = cardentry['card_images']
    except KeyError:
        continue
    for imageentry in imagedata:
        try:
            passcode = imageentry['id']
        except KeyError:
            continue
        if passcode in knownCards:
            continue
        if passcode in wantedcards:
            newCards.append((passcode, cardentry, imageentry))
        #if cardentry['id'] != 65477143:
         #   continue

        #newCards.append((passcode, cardentry, imageentry))

atkDefFont = ImageFont.truetype('fonts/atkdef.ttf', 48)
linkRatingFont = ImageFont.truetype('fonts/linkrating.ttf', 48)
pendulumScaleFont = ImageFont.truetype('fonts/pendulum.ttf', 20)

def parseMonsterTypes(types):
    if types[-1] in ('monster','token'):
        return types

if newCards:
    print('Generating artworks for %d new cards...' % len(newCards))
    step = max(floor(len(newCards) / 20),1)
    for (i, (passcode,info,imageinfo)) in enumerate(newCards):
        if (i % step) == 0:
            print('%d%% done...' % (i/len(newCards)*100))
        try:
            type = info['type']
            frame = None
            layers = []
            textlayers = []
            if type in ('Spell Card','Trap Card'):
                frame = (type == ('Spell Card')) and 'spell' or 'trap'
            else:
                string_with_types = type.lower().split(' ')
                monsterTypes = []
                if string_with_types[0] in ('tuner', 'spirit'): #let's handle these special cases like this
                    frame = info['frameType']
                else:
                    monsterTypes = parseMonsterTypes(string_with_types)
                    for frametype in ('normal','effect','ritual','fusion','synchro','xyz','link','token'):
                        if frametype in monsterTypes:
                            frame = frametype
                if frame is None:
                    print('Skipped #%08d (%s), could not determine frame (%s)' % (passcode, info['name'], str(monsterTypes)))
                    continue
                
                if 'pendulum' in monsterTypes:
                    frame += '_p'
                
                try:
                    lvl = info['level']
                    if (1 <= lvl) and (lvl <= 12):
                        layers.append((('parts/%s_%d.png' % ((('xyz' in monsterTypes) and 'rank' or 'level'), lvl)), (0,455,400,31)))
                except KeyError:
                    pass
                
                try:
                    attr = info['attribute'].lower()
                    if attr in ('divine','earth','wind','fire','water','dark','light'):
                        layers.append((('parts/jp/%s.png' % (attr,)), ('link' in monsterTypes) and (178,451,43,43) or (325,451,43,43)))
                except KeyError:
                    pass
                
                try:
                    atk = str(info['atk'])
                    textlayers.append((atk, (108,530), atkDefFont))
                except KeyError:
                    pass
                
                try:
                    defs = str(info['def'])
                    textlayers.append((defs, (292,530), atkDefFont))
                except KeyError:
                    pass
                
                try:
                    rating = str(info['linkval'])
                    textlayers.append((rating, (294,533), linkRatingFont))
                except KeyError:
                    pass
                
                try:
                    scale = str(info['scale'])
                    if frame not in ('fusion_p','ritual_p','synchro_p','xyz_p'): # listed frames already have a pendulum overlay
                        layers.append(('parts/pendulum.png',(9,376,382,50)))
                    textlayers.append((scale, (26,415), pendulumScaleFont))
                    textlayers.append((scale, (374,415), pendulumScaleFont))
                except KeyError:
                    pass
                
                try:
                    linkmarkers = set(map(lambda s: s.lower(), info['linkmarkers']))
                    for (posi,posn,pos) in ((1,'bottom-left',(4,393,39,39)),(2,'bottom',(169,410,63,25)),(3,'bottom-right',(356,393,39,39)),(4,'left',(0,183,25,61)),(6,'right',(375,183,25,62)),(7,'top-left',(4,4,39,39)),(8,'top',(169,0,63,25)),(9,'top-right',(356,4,39,39))):
                        layers.append((('parts/arrow_%d_%s.png' % (posi, posn in linkmarkers and 'yes' or 'no')), pos))
                except KeyError:
                    pass

            
            if frame and ('image_url_cropped' in imageinfo):
                with Image.new(mode='RGBA', size=(400,583), color=(0,0,0,0)) as img:
                    with requests.get(imageinfo['image_url_cropped']) as r:
                        time.sleep(.1)
                        try:
                            r.raise_for_status()
                        except requests.exceptions.HTTPError as ex:
                            print('Skipped #%08d (%s), failed to get cropped artwork (%d %s)' % (passcode, info['name'], ex.response.status_code, ex.response.reason))
                            continue

                        with Image.open(io.BytesIO(r.content)) as artworkI:
                            if artworkI.height < artworkI.width:
                                if type in ('Spell Card','Trap Card'):
                                    print('Skipped #%08d (%s), subsize cropped artwork (height < width)' % (passcode, info['name']))
                                    continue
                                else:
                                    # Pendulum monsters were being skipped, so ignore that for now
                                    print('For #%08d (%s), the subsize cropped artwork (height < width) but it was not skipped' % (passcode, info['name']))
                                
                            if (artworkI.width/artworkI.height) < (382/417):
                                cropBox = (0,0,artworkI.width, round(artworkI.width*417/382))
                            else:
                                cropBox = (0,0,artworkI.width, artworkI.height)
                            img.paste(artworkI.resize(size=(382,417), box=cropBox), box=(9,9,9+382,9+417))
                    
                    with Image.open('frames/%s.png' % (frame,)) as frameI:
                        img.alpha_composite(frameI)
                    
                    for (path, (x,y,w,h)) in layers:
                        with Image.new(mode='RGBA', size=(400,583), color=(0,0,0,0)) as tmpimg:
                            with Image.open(path) as srcimg:
                                tmpimg.paste(srcimg.resize(size=(w,h), resample=Image.Resampling.HAMMING), box=(x,y,x+w,y+h))
                            img.alpha_composite(tmpimg)
                    
                    for (string, pos, font) in textlayers:
                        ImageDraw.Draw(img).text(pos, string, font=font, anchor='mm', fill=(0,0,0,255))
                    
                    img.save('output/%d.png' % (passcode,), format='PNG', optimize=True)
        except Exception as ex:
            print('Skipped #%08d (%s), general failure: %s' % (passcode, info['name'], str(ex)))
    
    print('Finished!')
else:
    print('Check OK, no new artworks.')
    if not ('--force' in sys.argv):
        print('(If you think there should be new card data, maybe try with --force?)')