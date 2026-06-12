"""All hardcoded word sets extracted from run_batch.mjs."""

# === Language Detection Words ===
# From run_batch.mjs lines 187-189
GERMAN_WORDS: frozenset[str] = frozenset(
    "ich,ist,das,die,der,den,dem,des,mit,und,auf,ein,eine,einen,oder,was,wie,sind,haben,aber,auch,nicht,nur,wenn,sich,dass,sie,für,mein,meine,meinen,kann,mehr,noch,mal,so,aus,zu,von,als,bei,zur,beim,ihr,euch,wir,heute,immer,ihre,ihren,wer,wo,warum,wieso,vom,zum,dich,nichts,etwas,keine,wird,würde,schon,dann,jetzt,wieder,sehr,viel,viele,vielen,danke,liebe,herz,leben,alle,allen,allem,alles,man,mir,dir,bin,bist,war,waren,am,im,um,wegen,ohne,nach,vor,ganz,kein,damit,weil,denn,seid,seit,dabei,dazu,hier,dort,einmal,zwischen,endlich,während,solange,obwohl,trotzdem,vielleicht,gerne,genau,wirklich,niemals,morgen,gestern,übermorgen,gut,besser,beste,schön,schöne,toll,super,prima,klasse,okay,euer,eure,mädchen,jungs,frauen,männer,leute,menschen,freunde,familie,mama,papa,tochter,sohn,schwester,bruder,neu,neue,neues,alt,alte,altes,jung,junge,erste,zweite,dritte,letzte,geht,kommt,machen,machte,gemacht,tun,tat,getan,sagen,sagte,gesagt,sehen,sah,gesehen,wollen,wollte,gewollt,müssen,musste,gemusst,sollen,sollte,gesollt,dürfen,durfte,gedurft,hätte,könnte,wäre,würde,willst,wirst,werden,werde,wurde,ihm,ihn,ihnen,ihres,ihrer,seine,seiner,seines,unser,unsere,mode,schmuck,outfit,look,herzlich,liebsten,aknesafe,akne,abspeichern,kanzlei,notar,notarin,rechtswahl,testament,beitrag,infos,rechtlichen,wusstet,jedem,tag,chance,schönste,lebens,girlie,girl,schauspielerin,willkommen,probiert,prinzessin,königin,wunderschön,wunderschöne,wunderschönen,wunderschönes,glückwunsch,geburtstag,natürlich,traum,süß,hübsch,wahnsinn,mega,geil,wow,steht".split(
        ","
    )
)

# From run_batch.mjs lines 189
ENGLISH_WORDS: frozenset[str] = frozenset(
    "the,and,you,with,is,of,for,it,this,that,have,are,was,were,my,be,on,at,in,to,a,an,me,we,they,their,them,these,those,just,so,what,where,when,why,how,do,does,did,can,could,should,would,will,today,always,never,very,much,many,about,out,over,under,from,some,any,all,no,yes,one,two,three,your,his,her,its,him,she,he,i,love,like,life,girl,boy,people,friend,family,mom,dad,sister,brother,new,old,young,first,last,make,said,say,see,want,need,must,should,happy,sad,beautiful,cute,amazing,perfect,best,better,good,great,nice,really,actually,definitely,probably,maybe,sometimes,recipe,dress,jewelry,look,feel,feeling,tips,outfits,content,sharing,wearing,things,agenda,cleaning,streets,viennese,baby,girls,boys,women,men,wow,omg,queen,king,vibes,aesthetic,iconic,obsessed,gorgeous,stunning,adore,fabulous,pretty,lovely".split(
        ","
    )
)

# === Region Detection ===
# From run_batch.mjs lines 234-235
AUSTRIAN_CITIES: list[str] = [
    "wien", "vienna", "salzburg", "graz", "innsbruck", "linz",
    "klagenfurt", "tirol", "tyrol", "österreich", "austria",
]

GERMAN_CITY_LIST: list[str] = [
    "berlin", "münchen", "munich", "hamburg", "köln", "cologne",
    "frankfurt", "stuttgart", "düsseldorf", "dusseldorf", "dortmund",
    "bremen", "hannover", "hanover", "leipzig", "dresden", "nürnberg",
    "nuremberg", "duisburg", "bochum", "wuppertal", "bielefeld",
    "mannheim", "karlsruhe", "wiesbaden", "bonn", "münster", "augsburg",
    "aachen", "germany", "deutschland",
]

GERMAN_CITY_ABBR: list[str] = ["cgn", "muc", "ber", "fra", "dus"]

# === Commercial Signal Keywords ===
# From run_batch.mjs lines 279-283
COMMERCIAL_SIGNALS: list[str] = [
    "ad", "anzeige", "werbung", "sponsored", "gifted", "collab",
    "collaboration", "paid", "partner", "partnership", "kooperation",
    "reklame", "geschenkt", "presssample", "prsample", "pr-sample",
    "unbezahlt", "unbezahlte",
]

# === Category Brand + Keyword Maps ===
# From run_batch.mjs lines 285-306
CATEGORY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "food": {
        "brands": [
            "lieferando", "hellofresh", "foodspring", "koro", "yfood",
            "huel", "myprotein", "more nutrition", "dm", "rewe", "edeka",
            "aldi", "lidl", "netto", "penny", "kaufland", "foodpanda",
            "wolt", "flink", "gorillas", "getir", "milka", "kinder",
            "ferrero", "haribo", "nimm2", "rittersport", "lindt",
            "knoppers", "bahlsen",
        ],
        "keywords": [
            "food", "foodie", "foodblog", "foodporn", "essen", "lecker",
            "kochen", "rezept", "backen", "frühstück", "breakfast",
            "lunch", "dinner", "restaurant", "café", "kaffee", "coffee",
            "smoothie", "bowl", "salat", "vegan", "vegetarisch", "bio",
            "organic",
        ],
    },
    "tech": {
        "brands": [
            "apple", "samsung", "huawei", "xiaomi", "google", "microsoft",
            "sony", "dell", "hp", "lenovo", "logitech", "amazon", "otto",
            "saturn", "mediamarkt", "cyberport", "alternate", "mindfactory",
            "caseking", "bequiet", "corsair", "razer", "nvidia", "amd",
            "intel", "oneplus", "nothing", "bose", "sonos", "jbl",
            "marshall", "sennheiser", "telekom", "vodafone", "o2", "congstar",
        ],
        "keywords": [
            "tech", "technology", "technik", "gadget", "smartphone",
            "handy", "laptop", "tablet", "pc", "computer", "gaming",
            "zocken", "setup", "unboxing", "review", "test", "testbericht",
            "kopfhörer", "headphones",
        ],
    },
    "beauty": {
        "brands": [
            "douglas", "sephora", "dm", "rossmann", "müller", "bipa",
            "essence", "catrice", "maybelline", "l'oréal", "loreal",
            "nivea", "balea", "rituals", "kiehls", "laneige", "glossier",
            "fenty", "kylie", "nyx", "mac", "clinique", "esteelauder",
            "shiseido", "neutrogena", "garnier", "babor", "drhauschka",
            "lavera", "weleda",
        ],
        "keywords": [
            "beauty", "makeup", "make-up", "skincare", "skincareroutine",
            "kosmetik", "pflege", "hautpflege", "gesichtspflege",
            "lippenstift", "mascara", "foundation", "nagellack", "nails",
            "nägel", "augenbrauen", "brows", "lashes", "haare", "hair",
            "haircare", "frisur", "friseur", "parfüm", "duft",
        ],
    },
    "fashion": {
        "brands": [
            "hm", "h&m", "zara", "mango", "bershka", "pullandbear",
            "stradivarius", "asos", "aboutyou", "zalando", "uniqlo", "cos",
            "arket", "otherstories", "massimodutti", "adidas", "nike",
            "puma", "reebok", "levis", "levi", "tommyhilfiger",
            "calvinklein", "esprit", "s.oliver", "only", "veromoda",
            "newyorker", "primark", "cunda", "peekcloppenburg",
            "breuninger", "mytheresa", "farfetch", "shein", "cider",
            "nakdfashion",
        ],
        "keywords": [
            "fashion", "mode", "outfit", "outfits", "ootd", "style",
            "streetstyle", "look", "lookbook", "kleidung", "klamotten",
            "kombi", "styling", "haul", "tryon", "anprobe", "passform",
            "fit", "trend", "trends", "kollektion", "collection",
        ],
    },
    "jewelry": {
        "brands": [
            "pandora", "swarovski", "thomassabo", "christ", "bijoubrigitte",
            "douglas", "swatch", "fossil", "michaelkors", "tiffany",
            "cartier", "bulgari", "apmmonaco", "lucardi", "siegel",
            "engelsrufer", "nomination", "sogniadoro", "lesgeorgettes",
            "anschmuck", "newbielovers", "arshajewellery", "marenjewelry",
            "pukka", "akind", "purelei",
        ],
        "keywords": [
            "jewelry", "jewellery", "schmuck", "schmuckstück", "kette",
            "halskette", "ring", "ringe", "ohrringe", "earrings", "armband",
            "armreif", "bracelet", "bangle", "anhänger", "pendant", "gold",
            "silber", "sterling", "vergoldet", "goldplated", "versilbert",
            "edelstein", "diamant", "perlen", "statement", "minimal",
            "layering",
        ],
    },
}

CAT_LABELS: dict[str, str] = {
    "food": "食品",
    "tech": "科技",
    "beauty": "美妆",
    "fashion": "服饰",
    "jewelry": "珠宝",
}
