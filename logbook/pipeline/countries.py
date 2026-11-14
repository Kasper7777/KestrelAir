"""ICAO location-indicator prefix -> (country name, ISO-3166 alpha-2).

Longest prefix wins, so special cases (e.g. EGY = Falklands, EGJ = Channel Islands)
sit alongside the general two-letter prefixes. Single letters cover the big
one-letter regions (K = USA, C = Canada, Y = Australia).
"""

PREFIXES = {
    # one-letter regions
    'K': ('United States', 'US'), 'C': ('Canada', 'CA'), 'Y': ('Australia', 'AU'),
    'Z': ('China', 'CN'), 'U': ('Russia', 'RU'), 'P': ('United States', 'US'),
    # Europe
    'EG': ('United Kingdom', 'GB'), 'EGJ': ('Channel Islands', 'JE'), 'EGJB': ('Guernsey', 'GG'),
    'EGJA': ('Alderney', 'GG'), 'EGY': ('Falkland Islands', 'FK'), 'EGN': ('United Kingdom', 'GB'),
    'EGNS': ('Isle of Man', 'IM'), 'EI': ('Ireland', 'IE'), 'EB': ('Belgium', 'BE'),
    'ED': ('Germany', 'DE'), 'ET': ('Germany', 'DE'), 'EE': ('Estonia', 'EE'), 'EF': ('Finland', 'FI'),
    'EH': ('Netherlands', 'NL'), 'EK': ('Denmark', 'DK'), 'EL': ('Luxembourg', 'LU'),
    'EN': ('Norway', 'NO'), 'EP': ('Poland', 'PL'), 'ES': ('Sweden', 'SE'), 'EV': ('Latvia', 'LV'),
    'EY': ('Lithuania', 'LT'), 'BI': ('Iceland', 'IS'), 'BG': ('Greenland', 'GL'),
    'LF': ('France', 'FR'), 'LE': ('Spain', 'ES'), 'GC': ('Spain (Canaries)', 'ES'),
    'LP': ('Portugal', 'PT'), 'LI': ('Italy', 'IT'), 'LS': ('Switzerland', 'CH'), 'LO': ('Austria', 'AT'),
    'LK': ('Czechia', 'CZ'), 'LZ': ('Slovakia', 'SK'), 'LH': ('Hungary', 'HU'), 'LR': ('Romania', 'RO'),
    'LB': ('Bulgaria', 'BG'), 'LG': ('Greece', 'GR'), 'LT': ('Türkiye', 'TR'), 'LC': ('Cyprus', 'CY'),
    'LD': ('Croatia', 'HR'), 'LJ': ('Slovenia', 'SI'), 'LQ': ('Bosnia & Herzegovina', 'BA'),
    'LY': ('Serbia', 'RS'), 'LW': ('North Macedonia', 'MK'), 'LA': ('Albania', 'AL'), 'LM': ('Malta', 'MT'),
    'LU': ('Moldova', 'MD'), 'LL': ('Israel', 'IL'), 'LN': ('Monaco', 'MC'), 'LX': ('Gibraltar', 'GI'),
    # former USSR
    'UK': ('Ukraine', 'UA'), 'UM': ('Belarus', 'BY'), 'UB': ('Azerbaijan', 'AZ'), 'UG': ('Georgia', 'GE'),
    'UD': ('Armenia', 'AM'), 'UA': ('Kazakhstan', 'KZ'), 'UAF': ('Kyrgyzstan', 'KG'), 'UT': ('Uzbekistan', 'UZ'),
    'UTA': ('Turkmenistan', 'TM'), 'UTD': ('Tajikistan', 'TJ'),
    # Africa / Middle East
    'DA': ('Algeria', 'DZ'), 'DT': ('Tunisia', 'TN'), 'GM': ('Morocco', 'MA'), 'HE': ('Egypt', 'EG'),
    'HL': ('Libya', 'LY'), 'GQ': ('Mauritania', 'MR'), 'GO': ('Senegal', 'SN'), 'DN': ('Nigeria', 'NG'),
    'DG': ('Ghana', 'GH'), 'HK': ('Kenya', 'KE'), 'HT': ('Tanzania', 'TZ'), 'FA': ('South Africa', 'ZA'),
    'FV': ('Zimbabwe', 'ZW'), 'FN': ('Angola', 'AO'), 'HA': ('Ethiopia', 'ET'), 'GV': ('Cape Verde', 'CV'),
    'OE': ('Saudi Arabia', 'SA'), 'OM': ('United Arab Emirates', 'AE'), 'OT': ('Qatar', 'QA'),
    'OB': ('Bahrain', 'BH'), 'OK': ('Kuwait', 'KW'), 'OO': ('Oman', 'OM'), 'OI': ('Iran', 'IR'),
    'OR': ('Iraq', 'IQ'), 'OJ': ('Jordan', 'JO'), 'OL': ('Lebanon', 'LB'), 'OS': ('Syria', 'SY'),
    'OA': ('Afghanistan', 'AF'), 'OP': ('Pakistan', 'PK'),
    # Asia / Pacific
    'VA': ('India', 'IN'), 'VI': ('India', 'IN'), 'VO': ('India', 'IN'), 'VE': ('India', 'IN'),
    'VN': ('Nepal', 'NP'), 'VG': ('Bangladesh', 'BD'), 'VC': ('Sri Lanka', 'LK'), 'VQ': ('Bhutan', 'BT'),
    'VT': ('Thailand', 'TH'), 'VV': ('Vietnam', 'VN'), 'VL': ('Laos', 'LA'), 'VD': ('Cambodia', 'KH'),
    'VY': ('Myanmar', 'MM'), 'VH': ('Hong Kong', 'HK'), 'VM': ('Macau', 'MO'), 'WS': ('Singapore', 'SG'),
    'WM': ('Malaysia', 'MY'), 'WB': ('Malaysia / Brunei', 'MY'), 'WI': ('Indonesia', 'ID'), 'WA': ('Indonesia', 'ID'),
    'RP': ('Philippines', 'PH'), 'RC': ('Taiwan', 'TW'), 'RK': ('South Korea', 'KR'), 'ZK': ('North Korea', 'KP'),
    'RJ': ('Japan', 'JP'), 'RO': ('Japan', 'JP'), 'ZM': ('Mongolia', 'MN'), 'NZ': ('New Zealand', 'NZ'),
    'NF': ('Fiji', 'FJ'), 'PH': ('United States (Hawaii)', 'US'), 'PG': ('Guam', 'GU'),
    # Americas
    'MM': ('Mexico', 'MX'), 'MK': ('Jamaica', 'JM'), 'MU': ('Cuba', 'CU'), 'MY': ('Bahamas', 'BS'),
    'MD': ('Dominican Republic', 'DO'), 'MT': ('Haiti', 'HT'), 'TJ': ('Puerto Rico', 'PR'),
    'MG': ('Guatemala', 'GT'), 'MH': ('Honduras', 'HN'), 'MN': ('Nicaragua', 'NI'), 'MR': ('Costa Rica', 'CR'),
    'MP': ('Panama', 'PA'), 'MS': ('El Salvador', 'SV'), 'MZ': ('Belize', 'BZ'), 'MW': ('Cayman Islands', 'KY'),
    'TN': ('Caribbean Netherlands', 'CW'), 'TF': ('French Antilles', 'GP'), 'TT': ('Trinidad & Tobago', 'TT'),
    'TB': ('Barbados', 'BB'), 'SK': ('Colombia', 'CO'), 'SV': ('Venezuela', 'VE'), 'SE': ('Ecuador', 'EC'),
    'SP': ('Peru', 'PE'), 'SL': ('Bolivia', 'BO'), 'SC': ('Chile', 'CL'), 'SA': ('Argentina', 'AR'),
    'SB': ('Brazil', 'BR'), 'SD': ('Brazil', 'BR'), 'SN': ('Brazil', 'BR'), 'SW': ('Brazil', 'BR'),
    'SU': ('Uruguay', 'UY'), 'SG': ('Paraguay', 'PY'), 'SY': ('Guyana', 'GY'), 'SM': ('Suriname', 'SR'),
    'SO': ('French Guiana', 'GF'), 'TX': ('Bermuda', 'BM'),
}


PREFIXES['SF'] = ('Falkland Islands', 'FK')


def country_for(ident, navdata_country=None, state=None, region=None):
    """Best-effort country for an airport ident.

    Order: specific 3-4 letter prefixes (EGJ, EGY) > navdata's ICAO region > the
    ident's own prefix. Airfields with no region and a U-ident are unofficial
    Russian codes (UBOK, UTOE), not the Azerbaijan/Uzbekistan the prefix suggests.
    FAA-style idents (7FL6) carry a US state, so they fall back to the United States."""
    ident = (ident or '').upper()
    for n in (4, 3):
        hit = PREFIXES.get(ident[:n])
        if hit:
            return {'name': hit[0], 'iso': hit[1]}
    if region:
        for n in (2, 1):
            hit = PREFIXES.get(region.upper()[:n])
            if hit and region[:1].isalpha() and not (region[0] == 'K' and region[1:].isdigit() and n == 2):
                return {'name': hit[0], 'iso': hit[1]}
    elif ident[:1] == 'U' and ident[:1].isalpha() and len(ident) == 4:
        return {'name': 'Russia', 'iso': 'RU'}
    for n in (2, 1):
        hit = PREFIXES.get(ident[:n])
        if hit and ident[:1].isalpha():
            return {'name': hit[0], 'iso': hit[1]}
    if navdata_country:
        return {'name': navdata_country, 'iso': None}
    if state:
        return {'name': 'United States', 'iso': 'US'}
    return {'name': 'Unknown', 'iso': None}
