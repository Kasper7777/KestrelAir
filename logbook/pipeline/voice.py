"""The pilot's voice: short, in-character comments on real local news, written offline.

No AI service and no model download - a few hundred lines of plain logic:

  1. classify a story (headline + the article's own summary) into a topic:
     sport, weather, festival, food, transport, council, crime, accident,
     business, nature, aviation, school, health, charity, housing, heritage, other
  2. pull out the concrete details: teams and score, an event or venue name,
     money, a person, and one real sentence from the article's summary
  3. write a comment in the pilot's voice - a reaction that fits the topic and
     the story's tone (sad stories get a sympathetic, quiet line), sometimes tied
     back to flying or to where the pilot is (breakfast cafe, hotel bar, a sight)

Deterministic: the same story in the same place always gets the same comment, and a
Voice instance never repeats a phrasing until it has used the others.
The facts quoted are the article's; the reactions are the imagined day.
"""
import hashlib
import random
import re

TOPICS = [
    ('sky', r'\b(eclipse|meteor\w*|northern lights|aurora|supermoon|blood moon|comet|stargaz\w*|planets?)\b'),
    ('accident', r'\b(crash(ed|es)?|collision|collided|overturned|fire|blaze|flames|explosion|rescued?|coastguard|lifeboat|air ambulance|emergency services|injur\w*|hospitali[sz]ed|missing)\b'),
    ('crime', r'\b(court|jailed|sentenced|guilty|charged|arrest\w*|police|murder|stabb\w*|assault|theft|burglar\w*|fraud|robbery|prison|trial|convicted|killers?)\b'),
    ('aviation', r'\b(airport|airfield|runway|flights?|airline|aircraft|pilots?|helicopter|air show|airshow|spitfire|raf|drones?|hangar)\b'),
    ('weather', r'\b(storm|rain|flood\w*|heatwave|heat|drought|snow|frost|wind|gales?|weather|sunshine|temperatures?|met office|hosepipe|wildfire|thunder\w*|fog)\b'),
    ('sport', r'\b(\d+\s*-\s*\d+|match|fc|united|city fc|rovers|wanderers|league|cup|derby|goals?|scored|striker|manager|squad|season|rugby|cricket|golf|tennis|marathon|race|championship|premiership|playoffs?|fixture|kick-off|olympi\w*|medal|coach|cyclists?|regatta)\b'),
    ('festival', r'\b(festival|concert|gig|music|band|live (music|electronic)|theatre|show|exhibition|gallery|art(ist)?s?|museum|film|cinema|fair|carnival|parade|celebrat\w*|fireworks|eclipse|night out|comedy|orchestra|choir|dance)\b'),
    ('food', r'\b(restaurant|cafe|café|pub|bar|brewery|beer|wine|food|chef|menu|bakery|market|takeaway|dining|cuisine|pizza|chips|cheese|coffee|tasting)\b'),
    ('transport', r'\b(roads?|roadworks|bus(es)?|trains?|rail|station|traffic|motorway|bridge|ferry|tram|park and ride|parking|cycle lane|closures?|diversion|potholes?|a\d{1,4})\b'),
    ('housing', r'\b(homes?|houses?|housing|bungalow|property|flats?|estate agent|for sale|rent|planning permission|development|build(ing)? plans?)\b'),
    ('council', r'\b(council|councill?ors?|mayor|mp|election|vote|minister|government|parliament|budget|tax|policy|consultation|leader|board|hq|headquarters)\b'),
    ('business', r'\b(opens?|opening|closes?|closing|closure|jobs?|business|shop|store|company|firm|investment|expansion|redundanc\w*|£\s?\d|€\s?\d|\$\s?\d|million|billion|sale|launch\w*|brand)\b'),
    ('school', r'\b(school|pupils?|students?|university|college|teachers?|exam|graduat\w*|nursery|class)\b'),
    ('health', r'\b(nhs|hospital|clinic|doctor|gp|health|patients?|care home|dementia|mental health|vaccine|medical|recovery month|recovery)\b'),
    ('nature', r'\b(zoo|wildlife|animals?|birds?|dogs?|cats?|horses?|seals?|whales?|dolphins?|beach|coast|park|forest|trees?|nature|river|lake|conservation|puffins?|penguins?|bears?)\b'),
    ('charity', r'\b(charity|fundrais\w*|volunteers?|donat\w*|appeal|community|tribute|memorial|anniversary|veterans?|award|honoured|celebrates? \d+)\b'),
    ('heritage', r'\b(historic|history|heritage|castle|church|cathedral|abbey|stones?|ancient|centuries|medieval|war|wwii|ww2|monument|restoration)\b'),
]
# the same topics in the languages of places you fly to (Spanish, French, German, Portuguese, Italian, Turkish)
EXTRA = {
    'accident': r'accidente|incendio|choque|herid\w*|rescate|incendie|bless\w*|unfall|feuerwehr|verletzt\w*|incidente|kaza|yangın',
    'crime': r'polic[ií]a|capturan?|detenid\w*|incaut\w*|robo|homicidio|asesinat\w*|condenad\w*|tribunal|gendarmerie|meurtre|polizei|festgenommen|gericht|polizia|arrestat\w*|polis|gözaltı',
    'sky': r'eclipse|éclipse|finsternis|eclissi|tutulma',
    'sport': r'f[uú]tbol|partido|goles?|liga|copa|campeonato|ligue|fu(ß|ss)ball|spiel|verein|calcio|partita|futebol|maç|takım',
    'weather': r'lluvia|tormenta|sequ[ií]a|inundaci\w*|calor|pluie|orage|s[eé]cheresse|canicule|regen|sturm|hitze|unwetter|chuva|pioggia|yağmur|fırtına',
    'festival': r'feria|concierto|exposici[oó]n|museo|fiesta|carnaval|f[eê]te|spectacle|exposition|konzert|ausstellung|festa|mostra|konser|sergi',
    'food': r'gastronom\w*|comida|restaurante|cocina|vino|cerveza|cuisine|vin|bière|essen|wein|bier|cibo|vinho|yemek',
    'transport': r'carretera|v[ií]a|tr[aá]fico|puente|autob[uú]s|aeropuerto|route|circulation|stra(ß|ss)e|verkehr|br[uü]cke|estrada|strada|trafik|köprü',
    'housing': r'vivienda|viviendas|logement|wohnung|abitazion\w*|konut',
    'council': r'alcald\w*|municipal\w*|gobierno|congreso|ministeri\w*|mairie|maire|conseil|gemeinde|b[uü]rgermeister|stadtrat|comune|sindaco|prefeitura|belediye|vali',
    'business': r'empresa|empleo|inversi[oó]n|apertura|tienda|entreprise|emploi|unternehmen|arbeitspl\w*|azienda|şirket',
    'school': r'escuela|colegio|ni[nñ]os|estudiantes|universidad|concurso de dibujo|[eé]cole|[eé]l[eè]ves|schule|sch[uü]ler|scuola|okul|öğrenci',
    'health': r'salud|hospital|cl[ií]nica|m[eé]dic\w*|sant[eé]|h[oô]pital|gesundheit|krankenhaus|sanit\w*|sağlık|hastane',
    'nature': r'playa|parque|animales|r[ií]o|bosque|plage|for[eê]t|strand|wald|tiere|spiaggia|praia|sahil|orman',
    'charity': r'solidari\w*|benéfic\w*|voluntari\w*|bénévol\w*|spende\w*|ehrenamt\w*|gönüllü',
    'heritage': r'hist[oó]ric\w*|patrimonio|patrimoine|castillo|ch[aâ]teau|iglesia|[eé]glise|kirche|burg|tarihi',
}
TOPICS = [(n, rx[:-3] + '|' + EXTRA[n] + rx[-3:]) if n in EXTRA else (n, rx) for n, rx in TOPICS]
SAD = re.compile(r'\b(die[sd]?|death|dead|killed|fatal|tragic|tragedy|tribute|funeral|mourn\w*|victims?|seriously injured|lost (his|her|their) li(fe|ves)|jailed|killers?|murder\w*|stabb\w*|assault\w*)\b', re.I)

# reactions per topic: {h} = short headline, {fact} = a real line from the article, {town}, {where} = where the
# pilot is reading it, {thing} = event/venue/person, {teams}, {score}, {money}. Each line is self-contained.
LINES = {
    'sport': [
        "The whole of {where} had the {teams} game on. {score_line}",
        "{teams_or_h} - the bloke next to me at {where} hadn't stopped talking about it by the time I left.",
        "Sport pages in {town} are all about this: “{h}”. Locals take it seriously.",
        "Caught the end of the {teams} highlights over {meal}. {score_line}",
    ],
    'weather': [
        "“{h}”. Checked the TAFs twice before bed - glad I landed when I did.",
        "Weather is the talk of {town} today: “{h}”. As a pilot I'm paying attention too.",
        "Local news says “{h}”. Planning tomorrow's departure round it.",
        "“{h}” - you could feel it in the air walking back from {where}.",
    ],
    'sky': [
        "“{h}”. Best seat for that is 35,000 feet - I'll keep an eye out from the flight deck.",
        "Sky news in {town}: “{h}”. {fact} Pilots get the front-row view.",
        "“{h}”. Already working out if I can be airborne for it.",
    ],
    'festival': [
        "Saw posters for this all over {town}: “{h}”. Very tempted to stay another night.",
        "“{h}”. {fact} Might have to come back for that one.",
        "Apparently “{h}”. Shame my schedule won't stretch to it.",
        "If you're near {town}: “{h}”. Sounds like a good night out.",
        "“{h}”. The kind of thing that makes a stopover worth it.",
        "Culture corner in the {town} paper: “{h}”. {fact}",
    ],
    'food': [
        "Fitting reading over {meal}: “{h}”.",
        "“{h}” - noted for next time I'm through {town}.",
        "Food news in the local paper: “{h}”. {fact}",
        "“{h}”. After the meal I just had, I believe it.",
    ],
    'transport': [
        "“{h}”. One advantage of arriving by air - no traffic.",
        "Taxi driver filled me in on this: “{h}”.",
        "Local paper: “{h}”. {fact} Glad I'm not driving.",
    ],
    'housing': [
        "Browsing the property pages over {meal}: “{h}”. One day, maybe.",
        "“{h}”. {fact} Could get used to that view.",
    ],
    'council': [
        "Local politics in {town}: “{h}”. {fact}",
        "Everyone at {where} had an opinion on this: “{h}”.",
        "“{h}”. Not my patch, but interesting to see what matters here.",
        "Front page in {town}: “{h}”.",
    ],
    'business': [
        "News in {town}: “{h}”. {fact}",
        "“{h}”. Good to see a place like {town} keep busy.",
        "Spotted this in the local paper: “{h}”.",
        "Talk of the town in {town}: “{h}”.",
        "“{h}”. The owner at {where} had plenty to say about that.",
    ],
    'school': [
        "“{h}”. Nice to read some good news over {meal}.",
        "Local paper: “{h}”. {fact}",
    ],
    'health': [
        "“{h}”. {fact}",
        "Read this one twice: “{h}”. Worth knowing about.",
    ],
    'nature': [
        "Best story in the paper today: “{h}”.",
        "“{h}”. {fact} Might take a detour on the way back to the airfield.",
        "Something to see if you're in {town}: “{h}”.",
    ],
    'charity': [
        "Lovely one in the local paper: “{h}”.",
        "“{h}”. {fact} Good people round here.",
    ],
    'heritage': [
        "History lesson over {meal}: “{h}”. {fact}",
        "“{h}”. Had a look at it on the way in - spotted from the circuit, too.",
    ],
    'aviation': [
        "Of course I read this one first: “{h}”. {fact}",
        "Aviation news in {town}: “{h}”. Professional interest.",
        "“{h}” - had to tell the barman I'd just flown in myself.",
    ],
    'other': [
        "Picked up the local paper at {where}: “{h}”.",
        "What {town} is talking about today: “{h}”.",
        "“{h}”. {fact}",
        "Local headlines over {meal}: “{h}”.",
        "“{h}”. You learn a lot about a place from its local paper.",
    ],
}
SAD_LINES = {
    'accident': [
        "Sobering news in {town}: “{h}”. Thoughts with everyone involved.",
        "Quiet mood at {where} after this: “{h}”.",
        "“{h}”. Hard reading. Hope everyone's all right.",
    ],
    'crime': [
        "Grim story in the local paper: “{h}”.",
        "“{h}”. Sad to read; people at {where} were talking about it quietly.",
    ],
    'other': [
        "Sobering read in the local paper: “{h}”. Thoughts with everyone affected.",
        "Quiet mood in {town} today: “{h}”.",
    ],
}
WHERE = {'breakfast': 'the café', 'lunch': 'the lunch spot', 'dinner': 'the restaurant', 'hotel': 'the hotel bar', 'sight': 'the visitor centre'}
MEAL = {'breakfast': 'breakfast', 'lunch': 'lunch', 'dinner': 'dinner', 'hotel': 'a nightcap', 'sight': 'a coffee'}


IDIOMS = re.compile(r'\b(under fire|came under fire|fired up|on fire form|in hot water|weather the storm|storm of criticism|crash course|smashed (it|the)|killer (app|deal|line-up))\b', re.I)


def topic_of(title, summary=''):
    text = IDIOMS.sub(' ', f'{title} {summary or ""}').lower()
    for name, rx in TOPICS:
        if re.search(rx, text):
            return name
    return 'other'


def _first_sentence(summary, title, limit=150):
    """One real sentence from the article's summary that adds something to the headline."""
    if not summary:
        return ''
    s = re.sub(r'\s+', ' ', summary).strip()
    s = re.split(r'(?<=[.!?])\s', s)[0].strip()
    if len(s) < 25 or len(s) > limit:
        return ''
    tw = set(re.findall(r'\w{4,}', title.lower()))
    sw = set(re.findall(r'\w{4,}', s.lower()))
    if sw and len(tw & sw) / len(sw) > 0.7:            # just repeats the headline
        return ''
    if re.search(r'cookies|subscribe|sign up|newsletter|click here|javascript', s, re.I):
        return ''
    return s if s.endswith(('.', '!', '?')) else s + '.'


def _teams(title):
    m = re.search(r'([A-Z][\w\'.&]+(?:\s[A-Z][\w\'.&]+){0,2})\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Z][\w\'.&]+(?:\s[A-Z][\w\'.&]+){0,2})', title)
    if m:
        return f'{m.group(1)} v {m.group(4)}', f'{m.group(2)}-{m.group(3)}'
    m = re.search(r'([A-Z][\w\'.&]+(?:\s[A-Z][\w\'.&]+){0,2})\s+v(?:s\.?)?\s+([A-Z][\w\'.&]+(?:\s[A-Z][\w\'.&]+){0,2})', title)
    if m:
        return f'{m.group(1)} v {m.group(2)}', None
    return None, None


def short_headline(title, n=90):
    t = re.sub(r'\s+', ' ', title).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(' ', 1)[0] + '…'


class Voice:
    def __init__(self, pilot='the pilot', seed='kestrel'):
        self.pilot = pilot
        self.seed = seed
        self.used_count = {}

    def _pick(self, rng, key, pool):
        """The least-used phrasing in this pool (random among ties), so nothing repeats until it must."""
        counts = self.used_count.setdefault(key, {})
        low = min(counts.get(x, 0) for x in pool)
        line = rng.choice([x for x in pool if counts.get(x, 0) == low])
        counts[line] = counts.get(line, 0) + 1
        return line

    def comment(self, story, town, at='breakfast'):
        """A short in-character comment on a real story. Returns (text, headline_as_quoted)."""
        title = story.get('title') or ''
        summary = story.get('summary') or ''
        h = short_headline(title)
        topic = topic_of(title, summary)
        # sad only when the story really is (a death, a serious injury, a violent crime) - not just any court or fire mention
        sad = bool(SAD.search(title)) or (story.get('tone') == 'sad' and topic in ('accident', 'crime'))
        rng = random.Random(int(hashlib.sha1(f'{self.seed}|{story.get("id") or title}|{town}'.encode()).hexdigest()[:12], 16))
        key = ('sad-' if sad else '') + topic
        pool = (SAD_LINES.get(topic) or SAD_LINES['other']) if sad else LINES.get(topic, LINES['other'])
        line = self._pick(rng, key, pool)

        teams, score = _teams(title)
        fact = _first_sentence(summary, title)
        if '{teams' in line and not teams:                  # a sport line that needs teams we don't have
            line = rng.choice([x for x in pool if '{teams' not in x] or LINES['other'])
        vals = {
            'h': h, 'town': town or 'town', 'fact': fact,
            'where': WHERE.get(at, 'breakfast'), 'meal': MEAL.get(at, 'breakfast'),
            'teams': teams or '', 'teams_or_h': teams or f'“{h}”',
            'score_line': (f'Finished {score}, if you were wondering.' if score else f'“{h}”.'),
        }
        text = line.format(**vals)
        text = re.sub(r'\s+', ' ', text).replace(' .', '.').strip()
        if '“' not in text:                                  # always quote the real headline, so it links to the story
            text = f'{text} (“{h}”)' if teams else f'“{h}”. {text}'
        return text, h
