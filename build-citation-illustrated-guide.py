"""Rebuild the illustrated guide from genuine local MSFS cockpit captures.

Run: uv run --with reportlab --with pillow --with pymupdf python build-citation-illustrated-guide.py
"""
from pathlib import Path
from io import BytesIO
from math import atan2, cos, sin, pi
from PIL import Image, ImageEnhance
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import pymupdf

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'citation-guide-assets'
OUTPUT = ROOT / 'Citation_X_Cold_Dark_Illustrated.pdf'
MANUAL = 'https://msfs.dev-pset.com/assets/docs/FlightFX%20-%20Citation%20X%20-%20Manual%20V1.0.pdf'
W, H = 842, 595
NAVY = HexColor('#142B40')
TEAL = HexColor('#116C70')
MUTED = HexColor('#546576')
AMBER = HexColor('#FFC857')
PAPER = HexColor('#F4F7FA')
STYLE = ParagraphStyle('body', fontName='Helvetica', fontSize=12, leading=16, textColor=NAVY)
SMALL = ParagraphStyle('small', parent=STYLE, fontSize=10, leading=13)

# Callouts: number, exact target in original screenshot pixels, badge in crop fractions.
def shot(name, crop, box, caption, marks):
    return dict(name=name, crop=crop, box=box, caption=caption, marks=marks)

PAGES = [
 dict(section='1', title='Power on', view='Shift + 8: left lower panel  |  Shift + 7: rear pedestal',
 shots=[
  shot('citation-pilot.png', (675,805,2290,1350), (24,277,510,178), 'LEFT LOWER PANEL  /  Shift + 8', [
   ('2',(2170,1240),(.87,.90)),('3',(787,955),(.06,.15)),
   ('4',(1780,960),(.62,.13)),('4',(1850,960),(.73,.13)),
   ('5',(2198,953),(.95,.15)),('6',(1655,1115),(.52,.88))]),
  shot('citation-aft-wide.png',(1510,970,1990,1340),(96,82,325,174), 'PARKING BRAKE  /  rear end of centre pedestal', [
   ('1',(1880,1210),(.22,.76))])],
 steps=[('1','Parking brake: SET','Pull the handle UP. Keep the aircraft parked while you work.'),
 ('2','STBY PWR: ON','Use the standby power switch at the bottom right of this panel.'),
 ('3','EMERG LT: ARM','Move the emergency-light switch to ARM.'),
 ('4','BATT 1 + BATT 2: ON','Turn both battery switches on.'),
 ('5','EICAS POWER: ON','This is the right-hand switch under AVIONICS POWER.'),
 ('6','LH FUEL BOOST: NORM','Use the left fuel-boost switch.')],
 note='Follow the numbers. These cold-and-dark photos show WHERE controls are; set them as written.'),

 dict(section='2', title='Start the APU', view='Shift + 9: APU panel beside the co-pilot',
 shots=[shot('citation-side.png',(1090,285,1570,1135),(99,79,358,394),'APU PANEL  /  right side of cockpit',[
  ('1',(1420,980),(.91,.88)), ('2',(1384,914),(.42,.80)),
  ('3',(1440,510),(.93,.25)), ('4',(1362,745),(.18,.55)),
  ('5',(1250,910),(.08,.76)), ('6',(1360,440),(.40,.08)),
  ('7',(1195,425),(.03,.16))])],
 steps=[('1','MASTER: ON','Turn the APU master switch on.'),
 ('2','TEST: press','Push the round TEST button once.'),
 ('3','GENERATOR: ON','Turn the APU generator switch on.'),
 ('4','Check DC VOLTS','Read the bottom part of the APU display: at least 22 V.'),
 ('5','Hold APU START up','Hold until the RELAY ENGAGED light comes on, then release.'),
 ('6','Wait: READY TO LOAD','Wait for the start sequence to finish.'),
 ('7','BLEED AIR: ON','Move the bleed-air switch to ON for engine starting.')],
 note='Before starting: LH fuel boost NORM (page 1); APU STARTER DISENGAGE stays NORMAL.'),

 dict(section='3A', title='Avionics and IRS', view='Shift + 8: power panel  |  Shift + 7: IRS selectors',
 shots=[
 shot('citation-pilot.png',(1490,810,2290,1320),(65,286,430,168),'AVIONICS POWER  /  Shift + 8',[
 ('1',(2120,952),(.90,.16))]),
 shot('citation-aft-wide.png',(940,465,1515,950),(65,78,430,187),'TWO IRS SELECTORS  /  Shift + 7',[
 ('2',(1060,850),(.12,.63)),('2',(1320,640),(.84,.20))])],
 steps=[('1','AVIONICS POWER: ON','Turn on the left switch under AVIONICS POWER. Leave EICAS on.'),
 ('2','Both IRS selectors: NAV','Use the two rotary selectors behind the throttles.'),
 ('3','Stay parked','Allow the IRS to align. Complete FMS position initialisation on the next page.'),
 ('','Then check the displays','Wait until the flight displays have valid attitude and position information.')],
 note='IRS = the navigation/attitude reference system. NAV is marked beside each selector.'),

 dict(section='3B', title='FMS and takeoff data', view='Shift + 3: the two flight-management computers',
 shots=[
 shot('fms-powered.png',(790,265,1265,525),(24,275,244,180),'FIRST: NAV IDENT',[
 ('1',(1233,476),(.92,.88))]),
 shot('fms-pos-init.png',(790,265,1265,525),(290,275,244,180),'THEN: POSITION INIT',[
 ('2',(1233,430),(.92,.88))]),
 shot('fms-pos-init.png',(785,525,1265,830),(90,78,380,176),'FMS KEYPAD AND PAGE BUTTONS',[
 ('3',(1060,556),(.60,.30)),('4',(826,556),(.09,.30)),
 ('5',(1010,690),(.35,.86))])],
 steps=[('1','Open POS INIT','On initial NAV IDENT, press the fourth screen-side key down on the RIGHT.'),
 ('2','Load GPS position','On POS INIT, wait for GPS 1 POS. Press the third key down on the RIGHT.'),
 ('3','FPL: enter your route','Use the FPL button for the flight plan. Check departure, destination and runway.'),
 ('4','PERF: takeoff data','Complete weight/runway data and use TAKEOFF DATA to obtain V1, VR and V2.'),
 ('5','Type with the keypad','Then press the screen-side key next to the field you want to fill.')],
 note='Set takeoff flaps to 15 before expecting V-speeds on the PFD. Use calculated speeds for your flight.'),

 dict(section='4A', title='Prepare engine starting', view='Shift + 5: bleed controls  |  Shift + 8: start buttons',
 shots=[
 shot('citation-lower.png',(1770,595,2240,1040),(97,264,355,201),'BLEED-AIR CONTROLS  /  Shift + 5',[
 ('1',(2015,860),(.50,.20))]),
 shot('citation-pilot.png',(1500,825,2050,1170),(68,79,422,164),'START BUTTONS AND GENERATORS  /  Shift + 8',[
 ('2',(1990,1090),(.94,.52)),('3',(1840,1090),(.48,.82)),
 ('4',(1670,932),(.12,.14)),('4',(1955,938),(.83,.14))])],
 steps=[('1','PAC ISOL VALVE: CLOSED','Turn the horizontal isolation-valve control to C (closed).'),
 ('','Check start-air pressure','APU READY TO LOAD and bleed ON. Confirm at least 30 PSI on the engine/system display before starting.'),
 ('2','RIGHT engine first','The RIGHT START button is the rightmost of the three black buttons.'),
 ('3','LEFT engine second','The LEFT START button is the leftmost black button. The middle button is DISENGAGE.'),
 ('4','Generators after both starts','Set LH GEN and RH GEN on when both engines are running.')],
 note='Continue to page 6 for throttle timing and engine monitoring. Do not just press both start buttons.'),

 dict(section='4B', title='Start right, then left', view='Shift + 6: throttles  |  Shift + 4: centre engine display',
 shots=[
 shot('citation-throttles.png',(990,300,1680,850),(25,259,255,212),'THROTTLES  /  Shift + 6',[
 ('1',(1510,665),(.85,.77)),('3',(1165,665),(.14,.77))]),
 shot('eicas-powered.png',(1005,35,1465,1020),(299,79,235,380),'ENGINE INDICATIONS  /  Shift + 4',[
 ('2',(1385,205),(.94,.10)),('2',(1370,480),(.94,.55))])],
 steps=[('1','Right start + right IDLE','Press RIGHT START (previous page). Move the RIGHT throttle to IDLE by 10% N2.'),
 ('2','Watch EICAS','Check N1 rotation, oil pressure, ITT and hydraulic pressure as the engine starts.'),
 ('3','Repeat for the left engine','When the right start is normal, press LEFT START and move the LEFT throttle to IDLE by 10% N2.'),
 ('','Finish the start','Both generators ON. APU bleed OFF; verify the engine bleed setup.'),
 ('','Stop for abnormal indications','Do not continue with abnormal starter, ITT, oil-pressure or hydraulic indications.')],
 note='Display photo is powered with ENGINES STOPPED. It shows locations, not normal running values.'),

 dict(section='5', title='Set up for taxi', view='Shift + 6: throttle quadrant  |  tablet: Ground Services',
 shots=[shot('citation-throttles.png',(645,280,1860,1050),(24,100,510,354),'THROTTLE QUADRANT  /  viewed from above',[
 ('1',(1025,635),(.07,.32)), ('2',(1710,625),(.94,.30)),
 ('3',(815,615),(.08,.73)), ('4',(1260,445),(.43,.10)),
 ('4',(1440,445),(.72,.10)), ('5',(1375,945),(.59,.93))])],
 steps=[('1','Speedbrake: fully STOWED','Lever on the LEFT of the throttles. Check EICAS shows 0%. Your CP3 lever must also be stowed.'),
 ('2','Flaps/slats: takeoff','Use the white SLATS FLAPS handle on the RIGHT. Select takeoff 15 and check the indication.'),
 ('3','Trim: takeoff band','Set elevator trim, then confirm the takeoff band on EICAS.'),
 ('4','Reversers: STOWED','Check both reverser handles/indications.'),
 ('5','Taxi light: as required','Use the TAXI LIGHT switch behind the throttles.')],
 note='Also: controls free/correct; IRS aligned; EICAS messages resolved. Tablet > Ground Services: chocks off, door shut.'),

 dict(section='6A', title='Before entering the runway', view='Shift + 5: pitot heat  |  Shift + 2: yaw damper / Mach trim',
 shots=[
 shot('citation-lower.png',(425,600,850,890),(95,279,350,177),'ANTI-ICE PANEL  /  Shift + 5',[
 ('1',(490,710),(.12,.80)),('1',(565,710),(.66,.80))]),
 shot('citation-left.png',(1200,325,1780,580),(45,80,470,175),'FLIGHT GUIDANCE PANEL  /  Shift + 2',[
 ('2',(1678,420),(.89,.16)),('3',(1678,477),(.89,.87))])],
 steps=[('1','Both PITOT/STATIC: ON','Switch LH and RH pitot/static heat on. Set other anti-ice for the conditions.'),
 ('2','Yaw damper: ON','Use YD on the flight-guidance panel; check its indication.'),
 ('3','Mach trim: ON','Use M TRIM directly below YD; check its indication.'),
 ('','Recheck takeoff configuration','Flaps set, trim in takeoff band, speedbrakes 0%, reversers stowed.'),
 ('','Set your lights','Landing-light switches are beside the taxi-light switch shown on page 7.')],
 note='Next page: transponder and departure checks. Hold short until you are cleared to enter the runway.'),

 dict(section='6B', title='Transponder and final check', view='Shift + 3: radio units  |  Shift + 6: departure altitude knob',
 shots=[
 shot('radio-mode.png',(745,865,1120,1290),(55,239,340,224),'LEFT RADIO UNIT  /  Shift + 3',[
 ('1',(800,1032),(.05,.64)),('1',(1025,1195),(.88,.88)),
 ('2',(890,1032),(.67,.34)),('2',(800,1000),(.05,.18))]),
 shot('citation-throttles.png',(1380,1060,1810,1315),(145,78,350,141),'ALTITUDE SELECTOR  /  Shift + 6',[
 ('3',(1585,1185),(.20,.80))])],
 steps=[('1','Select mode, then turn knob','Press the LEFT key beside the mode (fourth down). Turn the tuning knob until TA/RA is shown.'),
 ('2','Check TA/RA and squawk','TA/RA is below the four-digit code. The LEFT key above selects the code for adjustment with the tuning knobs.'),
 ('3','Set departure altitude','Turn the ALT knob to the cleared initial altitude and check the flight display.'),
 ('','Final cross-check','Confirm fuel/weight, runway, departure, flight director and calculated V1 / VR / V2.'),
 ('','EICAS: ready for takeoff','Resolve abnormal messages before applying takeoff thrust.')],
 note='7000 is only the code in this screenshot. Use your assigned squawk; select STBY during preparation.'),

 dict(section='7', title='Takeoff and initial climb', view='Shift + 6: thrust / flaps  |  Shift + 5: landing gear',
 shots=[
 shot('citation-throttles.png',(985,295,1830,850),(24,260,510,208),'THRUST DETENTS AND FLAPS  /  Shift + 6',[
 ('1',(1315,340),(.30,.10)), ('4',(1315,366),(.61,.25)),
 ('3',(1715,627),(.94,.77))]),
 shot('citation-lower.png',(230,605,435,1020),(142,79,220,166),'LANDING GEAR  /  Shift + 5',[
 ('2',(280,935),(.15,.86))])],
 steps=[('1','Takeoff thrust: TO/MC','Line up when cleared. Apply TO/MC thrust, release brakes and check engine indications.'),
 ('','Rotate at YOUR calculated VR','Keep the centreline. At VR, ease the nose toward about 13 degrees pitch.'),
 ('2','Positive climb: gear UP','Confirm a positive climb, then raise the landing gear.'),
 ('3','Flaps UP when appropriate','Retract flaps/slats above 170 KIAS when appropriate for the departure.'),
 ('4','Climb thrust: CLB','Set CLB thrust. Follow the flight director and published departure.')],
 note='Never use a fixed VR. The correct rotation speed depends on weight and conditions.'),
]

def paragraph(c, text, x, top, width, style=STYLE):
    p=Paragraph(text,style)
    _,height=p.wrap(width,1000)
    p.drawOn(c,x,top-height)
    return height

def arrow(c, start, end):
    sx,sy=start; ex,ey=end
    angle=atan2(ey-sy,ex-sx)
    for col,width in [(NAVY,4.5),(AMBER,2)]:
        c.setStrokeColor(col); c.setLineWidth(width); c.line(sx,sy,ex,ey)
    c.setFillColor(AMBER)
    p=c.beginPath();p.moveTo(ex,ey)
    p.lineTo(ex-8*cos(angle-pi/7),ey-8*sin(angle-pi/7))
    p.lineTo(ex-8*cos(angle+pi/7),ey-8*sin(angle+pi/7));p.close()
    c.drawPath(p,fill=1,stroke=0)
    c.setStrokeColor(AMBER);c.setLineWidth(1.3);c.circle(ex,ey,3,stroke=1,fill=0)

def photo(c, spec):
    image=Image.open(ASSETS/spec['name']).convert('RGB').crop(spec['crop'])
    # Mild exposure lift preserves the genuine cockpit pixels and makes dark labels legible.
    image=ImageEnhance.Brightness(image).enhance(1.22)
    bx,by,bw,bh=spec['box']; iw,ih=image.size
    bh=min(bh,459-by)  # Keep image captions below the camera-view instruction.
    scale=min(bw/iw,bh/ih); dw,dh=iw*scale,ih*scale
    x,y=bx+(bw-dw)/2,by+(bh-dh)/2
    buf=BytesIO();image.save(buf,format='JPEG',quality=94)
    c.drawImage(ImageReader(BytesIO(buf.getvalue())),x,y,dw,dh)
    c.setStrokeColor(HexColor('#D4DEE6'));c.setLineWidth(.6);c.rect(x,y,dw,dh)
    c.setFillColor(MUTED);c.setFont('Helvetica-Bold',9)
    c.drawString(bx,by+bh+9,spec['caption'])
    left,top,_,_=spec['crop']
    for number,(tx,ty),(fx,fy) in spec['marks']:
        assert left<=tx<=spec['crop'][2] and top<=ty<=spec['crop'][3],(spec['name'],number)
        end=(x+(tx-left)*scale,y+dh-(ty-top)*scale)
        start=(x+fx*dw,y+(1-fy)*dh)
        arrow(c,start,end)
        c.setFillColor(AMBER);c.setStrokeColor(NAVY);c.setLineWidth(1.2)
        c.circle(*start,10,stroke=1,fill=1)
        c.setFont('Helvetica-Bold',11);c.setFillColor(NAVY)
        c.drawCentredString(start[0],start[1]-3.7,number)

def build():
    c=canvas.Canvas(str(OUTPUT),pagesize=(W,H),pageCompression=1)
    c.setTitle('Citation X | Illustrated Cold & Dark Quick Start')
    c.setAuthor('KestrelAir')
    c.setSubject('FlightFX Citation X in MSFS 2024: labelled in-game control-location guide')
    for page_no,page in enumerate(PAGES,1):
        c.bookmarkPage('page'+str(page_no))
        c.addOutlineEntry(page['section']+' - '+page['title'],'page'+str(page_no),0)
        c.setFillColor(PAPER);c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(NAVY);c.rect(0,505,W,90,fill=1,stroke=0)
        c.setFillColor(AMBER);c.setFont('Helvetica-Bold',13)
        c.drawString(24,568,'CITATION X  /  '+page['section'])
        c.setFillColor(white);c.setFont('Helvetica-Bold',25)
        c.drawString(24,534,page['title'])
        c.setFillColor(MUTED);c.setFont('Helvetica',10)
        c.drawString(24,487,page['view'])
        c.setStrokeColor(HexColor('#D4DEE6'));c.line(546,80,546,470)
        for spec in page['shots']:photo(c,spec)
        top=468
        for num,title,body in page['steps']:
            if num:
                c.setFillColor(TEAL);c.circle(565,top-8,9,fill=1,stroke=0)
                c.setFillColor(white);c.setFont('Helvetica-Bold',10)
                c.drawCentredString(565,top-11.4,num)
            x=582
            h=paragraph(c,'<b>'+title+'</b>',x,top,232)
            h+=paragraph(c,body,x,top-h-3,232,SMALL)+3
            top-=h+13
        assert top>=76,(page_no,top)
        c.setFillColor(HexColor('#E2EDF1'));c.roundRect(24,42,794,30,5,fill=1,stroke=0)
        paragraph(c,page['note'],34,63,774,ParagraphStyle('note',parent=SMALL,fontSize=9.3,leading=11))
        c.setFillColor(MUTED);c.setFont('Helvetica',8)
        c.drawString(24,25,'FlightFX Citation X | MSFS 2024 | SIMULATION USE ONLY | Control locations captured in your simulator')
        c.drawRightString(818,25,f'{page_no} / {len(PAGES)}')
        c.setFont('Helvetica',7.5)
        c.drawString(24,12,'Source: your original quick-start guide; FlightFX manual pp. 47, 82, 99-100, 131-134, 137. Click for manual.')
        c.linkURL(MANUAL,(24,10,590,21),relative=0,thickness=0)
        c.showPage()
    c.save()
    doc=pymupdf.open(OUTPUT)
    assert len(doc)==len(PAGES)
    previews=ASSETS/'previews';previews.mkdir(exist_ok=True)
    for i,page in enumerate(doc):
        assert page.get_images(),f'No screenshot on page {i+1}'
        for block in page.get_text('blocks'):
            assert block[0]>=0 and block[1]>=0 and block[2]<=W+.5 and block[3]<=H+.5,(i,block)
        page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(previews/f'page-{i+1:02}.png')
    # Contact sheet for a visual layout check.
    thumbs=[]
    for path in sorted(previews.glob('page-*.png')):
        im=Image.open(path).convert('RGB');im.thumbnail((505,357));thumbs.append(im)
    sheet=Image.new('RGB',(1010,357*((len(thumbs)+1)//2)),'#CBD5DF')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*505,(i//2)*357))
    sheet.save(previews/'contact-sheet.jpg',quality=90)
    print(f'Created {OUTPUT.name}: {len(doc)} pages, {OUTPUT.stat().st_size:,} bytes. All pages contain screenshots; text bounds checked.')

if __name__=='__main__':build()
