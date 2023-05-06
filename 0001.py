import requests, appdirs, os, time, sys, json, io
from PIL import Image, ImageFont, ImageDraw
from math import floor

wantedcards = [46986422,31241087,97417863,78098950,77832858,13836592,52382379,17550376,43944080,16893370,81743801,4483598,
97240499,91073013,41443249,15845914,8085950,27015862,59900655,19510093,31600845,40221691,35026117,14959144,18494511,
38033127,41165831,88554436,5852388,55349196,4836680,55688914,53270092,5205146,76615300,62411811,55461744,60283232,67853262,
28954097,29302858,31987203,88875133,45005708,66401502,28720123,13014905,15171722,26077388,45883110,65477143,92332424,23076639,
31600513,61845881,49109013,89809665,97534104,29280200,20455229,82112494,92565383,5182107,67972302,56727340,23512906,27132400,
8910240,96305350,97682931,31464658,48386462,76593718,3361010,6327734,60023855,89776023,83334932,82090807,77202120,54594017,
2992467,30765615,17272964,44760562,80621253,3248469,54126514,91479482,53404966,10333641,66150724,39643167,70155677,75771170,
88890658,52495649,15001940,89016236,53618197,26223582,653675,8775395,19403423,19671433,23969415,24081957,32807847,36920182,
41773061,44843954,45065541,46382143,50357013,54562327,59131526,61070601,63166096,67523044,68441986,74063035,78231356,83308376,
95283172,96127902,96661780,97474300,98696958,14166715,87778106,10793085,23746827,27345070,30284022,46497537,60176682,60623203,
61292243,63136489,66712905,91951471,96352712,18458255,83008724,84121302,99531088,98319530,15388353,25807544,34771947,36742774,
56787189,62314831,82460246,10780049,11802691,15967552,19271881,21677871,22024279,42952160,43331750,43618262,44553392,53174748,
53330789,57296396,58019984,62219643,70825459,71164684,85520170,89569453,93918159,6214163,33055499,40551410,45675980,76823930,
84281045,85407683,88346805,7336745,18158393,80738884,87955518,67745632,8505920,50687050,41232648,97783338,34904525,75286622,
61398234,74659582,38264974,38811586,43227,93347961,92422871,1769875,91300233,28798938,37442336,94130731,53971455,64193046,63436931,
27572350,22850702,72309040,24634594,821049,90587641,85969517,9709452,24070330,25862691,22390469,36320744,62714453,26096329,
95243515,98986900,30128445,35103106,39943352,34481518,62592805,61470213,58884063,24269961,98462037,9205574,36609519,97864322,
90673289,20515672,30342076,28168628]

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
unknowntypes = set()

def parseMonsterTypes(type):
    types = type.lower().split(' ')
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
            elif monsterTypes := parseMonsterTypes(type):
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
                
            else:
                if not type in unknowntypes:
                    print('Unknown card type \'%s\' on %d, skipped.' % (type, passcode))
                    unknowntypes.add(type)
            
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
                                print('Skipped #%08d (%s), subsize cropped artwork (height < width)' % (passcode, info['name']))
                                continue
                                
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