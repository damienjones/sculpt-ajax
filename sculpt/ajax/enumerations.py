from sculpt.common import Enumeration
import re

# This list is problematic, as it excludes many state-like
# entries that are valid "US" addresses (Puerto Rico, District
# of Columbia, etc.)
#
US_STATES = Enumeration(
        ("AL", 'ALABAMA', "Alabama"),
        ("AK", 'ALASKA', "Alaska"),
        ("AZ", 'ARIZONA', "Arizona"),
        ("AR", 'ARKANSAS', "Arkansas"),
        ("CA", 'CALIFORNIA', "California"),
        ("CO", 'COLORADO', "Colorado"),
        ("CT", 'CONNECTICUT', "Connecticut"),
        ("DC", 'DISTRICT_OF_COLUMBIA', "D.C."), # because nobody writes "District of Columbia", ever
        ("DE", 'DELAWARE', "Delaware"),
        ("FL", 'FLORIDA', "Florida"),
        ("GA", 'GEORGIA', "Georgia"),
        ("HI", 'HAWAII', "Hawaii"),
        ("ID", 'IDAHO', "Idaho"),
        ("IL", 'ILLINOIS', "Illinois"),
        ("IN", 'INDIANA', "Indiana"),
        ("IA", 'IOWA', "Iowa"),
        ("KS", 'KANSAS', "Kansas"),
        ("KY", 'KENTUCKY', "Kentucky"),
        ("LA", 'LOUISIANA', "Louisiana"),
        ("ME", 'MAINE', "Maine"),
        ("MD", 'MARYLAND', "Maryland"),
        ("MA", 'MASSACHUSETTS', "Massachusetts"),
        ("MI", 'MICHIGAN', "Michigan"),
        ("MN", 'MINNESOTA', "Minnesota"),
        ("MS", 'MISSISSIPPI', "Mississippi"),
        ("MO", 'MISSOURI', "Missouri"),
        ("MT", 'MONTANA', "Montana"),
        ("NE", 'NEBRASKA', "Nebraska"),
        ("NV", 'NEVADA', "Nevada"),
        ("NH", 'NEW_HAMPSHIRE', "New Hampshire"),
        ("NJ", 'NEW_JERSEY', "New Jersey"),
        ("NM", 'NEW_MEXICO', "New Mexico"),
        ("NY", 'NEW_YORK', "New York"),
        ("NC", 'NORTH_CAROLINA', "North Carolina"),
        ("ND", 'NORTH_DAKOTA', "North Dakota"),
        ("OH", 'OHIO', "Ohio"),
        ("OK", 'OKLAHOMA', "Oklahoma"),
        ("OR", 'OREGON', "Oregon"),
        ("PA", 'PENNSYLVANIA', "Pennsylvania"),
        ("RI", 'RHODE_ISLAND', "Rhode Island"),
        ("SC", 'SOUTH_CAROLINA', "South Carolina"),
        ("SD", 'SOUTH_DAKOTA', "South Dakota"),
        ("TN", 'TENNESSEE', "Tennessee"),
        ("TX", 'TEXAS', "Texas"),
        ("UT", 'UTAH', "Utah"),
        ("VT", 'VERMONT', "Vermont"),
        ("VA", 'VIRGINIA', "Virginia"),
        ("WA", 'WASHINGTON', "Washington"),
        ("WV", 'WEST_VIRGINIA', "West Virginia"),
        ("WI", 'WISCONSIN', "Wisconsin"),
        ("WY", 'WYOMING', "Wyoming"),  
    )
    
# ISO 3166-1-alpha-2; see http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
# NOTE: this uses a string value as the enumeration value
# rather than an integer; for this we actually treat the
# value and the label as the same, with additional columns
# for the display value and the country TLD and the phone prefix
#
# phone prefixes from https://en.wikipedia.org/wiki/List_of_country_calling_codes
# NOTE: many of these are not unique so you cannot directly reverse
# from phone prefix to country
#
ISO_COUNTRIES = Enumeration(
        labels = ('value','id','label','tld','phone_prefix'),
        choices = [
            # Abkhazia (not formally recognized by ISO) +7 840, +7 940
            ( 'AF', 'AF', 'Afghanistan', '.af', '+93' ),
            ( 'AX', 'AX', '&Aring;land Islands', '.ax', '+358 18' ),
            ( 'AL', 'AL', 'Albania', '.al', '+355' ),
            ( 'DZ', 'DZ', 'Algeria', '.dz', '+213' ),
            ( 'AS', 'AS', 'American Samoa', '.as', '+1 684', ),
            ( 'AD', 'AD', 'Andorra', '.ad', '+376' ),
            ( 'AO', 'AO', 'Angola', '.ao', '+244' ),
            ( 'AI', 'AI', 'Anguilla', '.ai', '+1 264' ),
            ( 'AQ', 'AQ', 'Antarctica', '.aq', None ),
            ( 'AG', 'AG', 'Antigua and Barbuda', '.ag', '+1 268' ),
            ( 'AR', 'AR', 'Argentina', '.ar', '+54' ),
            ( 'AM', 'AM', 'Armenia', '.am', '+374' ),
            ( 'AW', 'AW', 'Aruba', '.aw', '+297' ),
            ( 'AU', 'AU', 'Australia', '.au', '+61' ),
            ( 'AT', 'AT', 'Austria', '.at', '+43' ),
            ( 'AZ', 'AZ', 'Azerbaijan', '.az', '+994' ),
            ( 'BS', 'BS', 'Bahamas', '.bs', '+1 242' ),
            ( 'BH', 'BH', 'Bahrain', '.bh', '+973' ),
            ( 'BD', 'BD', 'Bangladesh', '.bd', '+880' ),
            ( 'BB', 'BB', 'Barbados', '.bb', '+1 246' ),
            ( 'BY', 'BY', 'Belarus', '.by', '+375' ),
            ( 'BE', 'BE', 'Belgium', '.be', '+32' ),
            ( 'BZ', 'BZ', 'Belize', '.bz', '+501' ),
            ( 'BJ', 'BJ', 'Benin', '.bj', '+229' ),
            ( 'BM', 'BM', 'Bermuda', '.bm', '+1 441' ),
            ( 'BT', 'BT', 'Bhutan', '.bt', '+975' ),
            ( 'BO', 'BO', 'Bolivia, Plurinational State of', '.bo', '+591' ),
            ( 'BQ', 'BQ', 'Bonaire, Sint Eustatius and Saba', '.bq', ('+599 3','+599 4','+599 7') ),    # Caribbean Netherlands
            ( 'BA', 'BA', 'Bosnia and Herzegovina', '.ba', '+387' ),
            ( 'BW', 'BW', 'Botswana', '.bw', '+267' ),
            ( 'BV', 'BV', 'Bouvet Island', '.bv', None ),
            ( 'BR', 'BR', 'Brazil', '.br', '+55' ),
            ( 'IO', 'IO', 'British Indian Ocean Territory', '.io', '+246' ),    # Diego Garcia
            ( 'BN', 'BN', 'Brunei Darussalam', '.bn', '+673' ),
            ( 'BG', 'BG', 'Bulgaria', '.bg', '+359' ),
            ( 'BF', 'BF', 'Burkina Faso', '.bf', '+226' ),
            ( 'BI', 'BI', 'Burundi', '.bi', '+257' ),
            ( 'CV', 'CV', 'Cabo Verde', '.cv', '+238' ),    # Cape Verde
            ( 'KH', 'KH', 'Cambodia', '.kh', '+855' ),
            ( 'CM', 'CM', 'Cameroon', '.cm', '+237' ),
            ( 'CA', 'CA', 'Canada', '.ca', '+1' ),
            ( 'KY', 'KY', 'Cayman Islands', '.ky', '+1 345' ),
            ( 'CF', 'CF', 'Central African Republic', '.cf', '+236' ),
            ( 'TD', 'TD', 'Chad', '.td', '+235' ),
            ( 'CL', 'CL', 'Chile', '.cl', '+56' ),
            ( 'CN', 'CN', 'China', '.cn', '+86' ),
            ( 'CX', 'CX', 'Christmas Island', '.cx', '+61' ),
            ( 'CC', 'CC', 'Cocos (Keeling) Islands', '.cc', '+61' ),
            ( 'CO', 'CO', 'Colombia', '.co', '+57' ),
            ( 'KM', 'KM', 'Comoros', '.km', '+269' ),
            ( 'CG', 'CG', 'Congo', '.cg', '+242' ),
            ( 'CD', 'CD', 'Congo, the Democratic Republic of the', '.cd', '+243' ), # Zaire
            ( 'CK', 'CK', 'Cook Islands', '.ck', '+682' ),
            ( 'CR', 'CR', 'Costa Rica', '.cr', '+506' ),
            ( 'HR', 'HR', 'Croatia', '.hr', '+385' ),
            ( 'CU', 'CU', 'Cuba', '.cu', '+53' ),
            ( 'CW', 'CW', 'Cura&ccedil;ao', '.cw', '+599 9' ),
            ( 'CY', 'CY', 'Cyprus', '.cy', ('+357','+90 392') ),    # include Northern Cyprus, recognized only by Turkey, using part of Turkey's +90 prefix
            ( 'CZ', 'CZ', 'Czech Republic', '.cz', '+420' ),
            ( 'CI', 'CI', 'C&ocirc;te d&#8217;Ivoire', '.ci', '+225' ), # Ivory Coast
            ( 'DK', 'DK', 'Denmark', '.dk', '+45' ),
            ( 'DJ', 'DJ', 'Djibouti', '.dj', '+253' ),
            ( 'DM', 'DM', 'Dominica', '.dm', '+1 767' ),
            ( 'DO', 'DO', 'Dominican Republic', '.do', ('+1 809','+1 829','+1 849') ),  # multiple prefixes
            ( 'EC', 'EC', 'Ecuador', '.ec', '+593' ),
            ( 'EG', 'EG', 'Egypt', '.eg', '+20' ),
            ( 'SV', 'SV', 'El Salvador', '.sv', '+503' ),
            ( 'GQ', 'GQ', 'Equatorial Guinea', '.gq', '+240' ),
            ( 'ER', 'ER', 'Eritrea', '.er', '+291' ),
            ( 'EE', 'EE', 'Estonia', '.ee', '+372' ),
            ( 'ET', 'ET', 'Ethiopia', '.et', '+251' ),
            ( 'FK', 'FK', 'Falkland Islands (Malvinas)', '.fk', '+500' ),
            ( 'FO', 'FO', 'Faroe Islands', '.fo', '+298' ),
            ( 'FJ', 'FJ', 'Fiji', '.fj', '+679' ),
            ( 'FI', 'FI', 'Finland', '.fi', '+358' ),
            ( 'FR', 'FR', 'France', '.fr', '+33' ),
            ( 'GF', 'GF', 'French Guiana', '.gf', '+594' ),
            ( 'PF', 'PF', 'French Polynesia', '.pf', '+689' ),
            ( 'TF', 'TF', 'French Southern Territories', '.tf', None ),
            ( 'GA', 'GA', 'Gabon', '.ga', '+241' ),
            ( 'GM', 'GM', 'Gambia', '.gm', '+220' ),
            ( 'GE', 'GE', 'Georgia', '.ge', '+995' ),   # including disputed South Ossetia
            ( 'DE', 'DE', 'Germany', '.de', '+49' ),
            ( 'GH', 'GH', 'Ghana', '.gh', '+233' ),
            ( 'GI', 'GI', 'Gibraltar', '.gi', '+350' ),
            ( 'GR', 'GR', 'Greece', '.gr', '+30' ),
            ( 'GL', 'GL', 'Greenland', '.gl', '+299' ),
            ( 'GD', 'GD', 'Grenada', '.gd', '+1 473' ),
            ( 'GP', 'GP', 'Guadeloupe', '.gp', '+590' ),
            ( 'GU', 'GU', 'Guam', '.gu', '+1 671' ),
            ( 'GT', 'GT', 'Guatemala', '.gt', '+502' ),
            ( 'GG', 'GG', 'Guernsey', '.gg', '+44' ),
            ( 'GN', 'GN', 'Guinea', '.gn', '+224' ),
            ( 'GW', 'GW', 'Guinea-Bissau', '.gw', '+245' ),
            ( 'GY', 'GY', 'Guyana', '.gy', '+592' ),
            ( 'HT', 'HT', 'Haiti', '.ht', '+509' ),
            ( 'HM', 'HM', 'Heard Island and McDonald Islands', '.hm', None ),
            ( 'VA', 'VA', 'Holy See (Vatican City State)', '.va', ('+39 06 698','+379') ),
            ( 'HN', 'HN', 'Honduras', '.hn', '+504' ),
            ( 'HK', 'HK', 'Hong Kong', '.hk', '+852' ),
            ( 'HU', 'HU', 'Hungary', '.hu', '+36' ),
            ( 'IS', 'IS', 'Iceland', '.is', '+354' ),
            ( 'IN', 'IN', 'India', '.in', '+91' ),
            ( 'ID', 'ID', 'Indonesia', '.id', '+62' ),
            ( 'IR', 'IR', 'Iran, Islamic Republic of', '.ir', '+98' ),
            ( 'IQ', 'IQ', 'Iraq', '.iq', '+964' ),
            ( 'IE', 'IE', 'Ireland', '.ie', '+353' ),
            ( 'IM', 'IM', 'Isle of Man', '.im', '+44' ),
            ( 'IL', 'IL', 'Israel', '.il', '+972' ),
            ( 'IT', 'IT', 'Italy', '.it', '+39' ),
            ( 'JM', 'JM', 'Jamaica', '.jm', '+1 876' ),
            ( 'JP', 'JP', 'Japan', '.jp', '+81' ),
            ( 'JE', 'JE', 'Jersey', '.je', '+44' ),
            ( 'JO', 'JO', 'Jordan', '.jo', '+962' ),
            ( 'KZ', 'KZ', 'Kazakhstan', '.kz', ('+7 6','+7 7') ),
            ( 'KE', 'KE', 'Kenya', '.ke', '+254' ),
            ( 'KI', 'KI', 'Kiribati', '.ki', '+686' ),
            ( 'KR', 'KR', 'Korea, Republic of', '.kr', '+82' ),                             # South Korea
            ( 'KP', 'KP', 'Korea, Democratic People&#8217;s Republic of', '.kp', '+850' ),  # North Korea
            ( 'KW', 'KW', 'Kuwait', '.kw', '+965' ),
            ( 'KG', 'KG', 'Kyrgyzstan', '.kg', '+996' ),
            ( 'LA', 'LA', 'Lao People&#8217;s Democratic Republic', '.la', '+856' ),        # Laos
            ( 'LV', 'LV', 'Latvia', '.lv', '+371' ),
            ( 'LB', 'LB', 'Lebanon', '.lb', '+961' ),
            ( 'LS', 'LS', 'Lesotho', '.ls', '+266' ),
            ( 'LR', 'LR', 'Liberia', '.lr', '+231' ),
            ( 'LY', 'LY', 'Libya', '.ly', '+218' ),
            ( 'LI', 'LI', 'Liechtenstein', '.li', '+423' ),
            ( 'LT', 'LT', 'Lithuania', '.lt', '+370' ),
            ( 'LU', 'LU', 'Luxembourg', '.lu', '+352' ),
            ( 'MO', 'MO', 'Macao', '.mo', '+853' ),     # Macau
            ( 'MK', 'MK', 'Macedonia, the former Yugoslav Republic of', '.mk', '+389' ),
            ( 'MG', 'MG', 'Madagascar', '.mg', '+261' ),
            ( 'MW', 'MW', 'Malawi', '.mw', '+265' ),
            ( 'MY', 'MY', 'Malaysia', '.my', '+60' ),
            ( 'MV', 'MV', 'Maldives', '.mv', '+960' ),
            ( 'ML', 'ML', 'Mali', '.ml', '+223' ),
            ( 'MT', 'MT', 'Malta', '.mt', '+356' ),
            ( 'MH', 'MH', 'Marshall Islands', '.mh', '+692' ),
            ( 'MQ', 'MQ', 'Martinique', '.mq', '+596' ),
            ( 'MR', 'MR', 'Mauritania', '.mr', '+222' ),
            ( 'MU', 'MU', 'Mauritius', '.mu', '+230' ),
            ( 'YT', 'YT', 'Mayotte', '.yt', '+262' ),
            ( 'MX', 'MX', 'Mexico', '.mx', '+52' ),
            ( 'FM', 'FM', 'Micronesia, Federated States of', '.fm', '+691' ),
            ( 'MD', 'MD', 'Moldova, Republic of', '.md', '+373' ),
            ( 'MC', 'MC', 'Monaco', '.mc', '+377' ),
            ( 'MN', 'MN', 'Mongolia', '.mn', '+976' ),
            ( 'ME', 'ME', 'Montenegro', '.me', '+382' ),
            ( 'MS', 'MS', 'Montserrat', '.ms', '+1 664' ),
            ( 'MA', 'MA', 'Morocco', '.ma', '+212' ),
            ( 'MZ', 'MZ', 'Mozambique', '.mz', '+258' ),
            ( 'MM', 'MM', 'Myanmar', '.mm', '+95' ),
            ( 'NA', 'NA', 'Namibia', '.na', '+264' ),
            ( 'NR', 'NR', 'Nauru', '.nr', '+674' ),
            ( 'NP', 'NP', 'Nepal', '.np', '+977' ),
            ( 'NL', 'NL', 'Netherlands', '.nl', '+31' ),
            ( 'NC', 'NC', 'New Caledonia', '.nc', '+687' ),
            ( 'NZ', 'NZ', 'New Zealand', '.nz', '+64' ),
            ( 'NI', 'NI', 'Nicaragua', '.ni', '+505' ),
            ( 'NE', 'NE', 'Niger', '.ne', '+227' ),
            ( 'NG', 'NG', 'Nigeria', '.ng', '+234' ),
            ( 'NU', 'NU', 'Niue', '.nu', '+683' ),
            ( 'NF', 'NF', 'Norfolk Island', '.nf', '+672' ),
            ( 'MP', 'MP', 'Northern Mariana Islands', '.mp', '+1 670' ),
            ( 'NO', 'NO', 'Norway', '.no', '+47' ),
            ( 'OM', 'OM', 'Oman', '.om', '+968' ),
            ( 'PK', 'PK', 'Pakistan', '.pk', '+92' ),
            ( 'PW', 'PW', 'Palau', '.pw', '+680' ),
            ( 'PS', 'PS', 'Palestine, State of', '.ps', '+970' ),
            ( 'PA', 'PA', 'Panama', '.pa', '+507' ),
            ( 'PG', 'PG', 'Papua New Guinea', '.pg', '+675' ),
            ( 'PY', 'PY', 'Paraguay', '.py', '+595' ),
            ( 'PE', 'PE', 'Peru', '.pe', '+51' ),
            ( 'PH', 'PH', 'Philippines', '.ph', '+63' ),
            ( 'PN', 'PN', 'Pitcairn', '.pn', '+64' ),
            ( 'PL', 'PL', 'Poland', '.pl', '+48' ),
            ( 'PT', 'PT', 'Portugal', '.pt', '+351' ),
            ( 'PR', 'PR', 'Puerto Rico', '.pr', ('+1 787','+1 939') ),
            ( 'QA', 'QA', 'Qatar', '.qa', '+974' ),
            ( 'RO', 'RO', 'Romania', '.ro', '+40' ),
            ( 'RU', 'RU', 'Russian Federation', '.ru', '+7' ),
            ( 'RW', 'RW', 'Rwanda', '.rw', '+250' ),
            ( 'RE', 'RE', 'R&eacute;union', '.re', '+262' ),
            ( 'BL', 'BL', 'Saint Barth&eacute;lemy', '.bl', '+590' ),
            ( 'SH', 'SH', 'Saint Helena, Ascension and Tristan da Cunha', '.sh', '+290' ),
            ( 'KN', 'KN', 'Saint Kitts and Nevis', '.kn', '+1 869' ),
            ( 'LC', 'LC', 'Saint Lucia', '.lc', '+1 758' ),
            ( 'MF', 'MF', 'Saint Martin (French part)', '.mf', '+590' ),
            ( 'PM', 'PM', 'Saint Pierre and Miquelon', '.pm', '+508' ),
            ( 'VC', 'VC', 'Saint Vincent and the Grenadines', '.vc', '+1 784' ),
            ( 'WS', 'WS', 'Samoa', '.ws', '+685' ),
            ( 'SM', 'SM', 'San Marino', '.sm', '+378' ),
            ( 'ST', 'ST', 'S&atilde;o Tom&eacute; and Pr&iacute;ncipe', '.st', '+239' ),
            ( 'SA', 'SA', 'Saudi Arabia', '.sa', '+966' ),
            ( 'SN', 'SN', 'Senegal', '.sn', '+221' ),
            ( 'RS', 'RS', 'Serbia', '.rs', '+381' ),
            ( 'SC', 'SC', 'Seychelles', '.sc', '+248' ),
            ( 'SL', 'SL', 'Sierra Leone', '.sl', '+232' ),
            ( 'SG', 'SG', 'Singapore', '.sg', '+65' ),
            ( 'SX', 'SX', 'Sint Maarten (Dutch part)', '.sx', '+1 721' ),
            ( 'SK', 'SK', 'Slovakia', '.sk', '+421' ),
            ( 'SI', 'SI', 'Slovenia', '.si', '+386' ),
            ( 'SB', 'SB', 'Solomon Islands', '.sb', '+677' ),
            ( 'SO', 'SO', 'Somalia', '.so', '+252' ),
            ( 'ZA', 'ZA', 'South Africa', '.za', '+27' ),
            ( 'GS', 'GS', 'South Georgia and the South Sandwich Islands', '.gs', '+500' ),
            ( 'SS', 'SS', 'South Sudan', '.ss', '+211' ),
            ( 'ES', 'ES', 'Spain', '.es', '+34' ),
            ( 'LK', 'LK', 'Sri Lanka', '.lk', '+94' ),
            ( 'SD', 'SD', 'Sudan', '.sd', '+249' ),
            ( 'SR', 'SR', 'Suriname', '.sr', '+597' ),
            ( 'SJ', 'SJ', 'Svalbard and Jan Mayen', '.sj', '+47 79' ),
            ( 'SZ', 'SZ', 'Swaziland', '.sz', '+268' ),
            ( 'SE', 'SE', 'Sweden', '.se', '+46' ),
            ( 'CH', 'CH', 'Switzerland', '.ch', '+41' ),
            ( 'SY', 'SY', 'Syrian Arab Republic', '.sy', '+963' ),  # Syria
            ( 'TW', 'TW', 'Taiwan, Province of China', '.tw', '+886' ),
            ( 'TJ', 'TJ', 'Tajikistan', '.tj', '+992' ),
            ( 'TZ', 'TZ', 'Tanzania, United Republic of', '.tz', '+255' ),  # Zanzibar
            ( 'TH', 'TH', 'Thailand', '.th', '+66' ),
            ( 'TL', 'TL', 'Timor-Leste', '.tl', '+670' ),   # East Timor
            ( 'TG', 'TG', 'Togo', '.tg', '+228' ),
            ( 'TK', 'TK', 'Tokelau', '.tk', '+690' ),
            ( 'TO', 'TO', 'Tonga', '.to', '+676' ),
            ( 'TT', 'TT', 'Trinidad and Tobago', '.tt', '+1 868' ),
            ( 'TN', 'TN', 'Tunisia', '.tn', '+216' ),
            ( 'TR', 'TR', 'Turkey', '.tr', '+90' ),
            ( 'TM', 'TM', 'Turkmenistan', '.tm', '+993' ),
            ( 'TC', 'TC', 'Turks and Caicos Islands', '.tc', '+1 649' ),
            ( 'TV', 'TV', 'Tuvalu', '.tv', '+688' ),
            ( 'UG', 'UG', 'Uganda', '.ug', '+256' ),
            ( 'UA', 'UA', 'Ukraine', '.ua', '+380' ),
            ( 'AE', 'AE', 'United Arab Emirates', '.ae', '+971' ),
            ( 'GB', 'GB', 'United Kingdom', '.uk', '+44' ),
            ( 'US', 'US', 'United States', '.us', '+1' ),
            ( 'UM', 'UM', 'United States Minor Outlying Islands', '.um', '+1 808' ),    # prefix for Wake Island
            ( 'UY', 'UY', 'Uruguay', '.uy', '+598' ),
            ( 'UZ', 'UZ', 'Uzbekistan', '.uz', '+998' ),
            ( 'VU', 'VU', 'Vanuatu', '.vu', '+678' ),
            ( 'VE', 'VE', 'Venezuela, Bolivarian Republic of', '.ve', '+58' ),
            ( 'VN', 'VN', 'Vietnam', '.vn', '+84' ),
            ( 'VG', 'VG', 'Virgin Islands, British', '.vg' ),
            ( 'VI', 'VI', 'Virgin Islands, U.S.', '.vi', '+1 340' ),
            ( 'WF', 'WF', 'Wallis and Futuna', '.wf', '+681' ),
            ( 'EH', 'EH', 'Western Sahara', '.eh', None ),
            ( 'YE', 'YE', 'Yemen', '.ye', '+967' ),
            ( 'ZM', 'ZM', 'Zambia', '.zm', '+260' ),
            ( 'ZW', 'ZW', 'Zimbabwe', '.zw', '+263' ),
        ]
    )

# additional prefixes for various satellite phone services
#
# Ellipso +881 2, +881 3
# EMSAT +882 13
# GMSS +881
# Globalstar +881 8, +881 9
# ICO +881 0, +881 1
# Inmarsat SNAC +870
# ISCS +808
# Iridium +881 6, +881 7
# Thuraya +882 16
# Universal Personal Telecommunications +878

# while not strictly an enumeration, it's useful to be
# able to look up a phone prefix and determine which
# country code(s) may apply; this dict uses space-stripped
# prefixes as keys and values that are a list of unstripped
# prefix plus country code(s)
#
# NOTE: because we include satellite phone services in
# this list of prefixes, sometimes the country list may
# be empty
#
PHONE_PREFIXES = {
    '+808': [ '+808' ],
    '+870': [ '+870' ],
    '+881': [ '+881' ],
    '+8810': [ '+881 0' ],
    '+8811': [ '+881 1' ],
    '+8812': [ '+881 2' ],
    '+8813': [ '+881 3' ],
    '+8816': [ '+881 6' ],
    '+8817': [ '+881 7' ],
    '+8818': [ '+881 8' ],
    '+8819': [ '+881 9' ],
    '+88213': [ '+882 13' ],
    '+88216': [ '+882 16' ],
}

for d in ISO_COUNTRIES.iter_dicts():
    prefixes = d['phone_prefix']
    if prefixes is None:
        continue
    if not isinstance(prefixes, (tuple, list)):
        prefixes = [ prefixes ]
    for prefix in prefixes:
        stripped_prefix = re.sub(r'[^+0-9]', '', prefix)
        if stripped_prefix not in PHONE_PREFIXES:
            PHONE_PREFIXES[stripped_prefix] = [ prefix, d['id'] ]
        else:
            PHONE_PREFIXES[stripped_prefix].append(d['id'])

