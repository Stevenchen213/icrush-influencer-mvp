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

# === Bio Category Negative Keywords ===
# P0 fix: detect wrong-category accounts (therapist, mommy blogger, foodie, etc.)
# that pass language detection but don't match our fashion/beauty/jewelry niche.
# Each category maps to a list of German keywords scanned in bio + full_name (lowercased).
# Keywords are chosen to avoid false-positives on genuine fashion/lifestyle influencers.
BIO_CATEGORY_BLOCKLIST: dict[str, list[str]] = {
    # ── 心理 / 咨询 / 治疗 / 情感 / 身心灵 ──
    "心理/咨询/治疗": [
        "psycholog", "therap", "paartherap", "familienberat",
        "trauer", "trauma", "narzissmus", "achtsamkeit",
        "selbstoptimierung", "atmung", "breathwork",
        "nervensystem", "heilung", "inneres kind",
        "selbstfindung", "persönlichkeitsentwicklung",
        "systemischer coach", "mental coach", "lifecoach",
        "bewältigung", "resilienz",
        "adhs", "mindset", "meditation", "mindfulness",
        "mental health", "mental illness",
        "depression", "angst", "burnout",
        "healing", "spiritual", "spirituell",
        "bewusstseinscoach", "mentalcoach", "mindsetcoach",
        "coaching", "beratung",
        # v0.9.1: from false-negative review
        "familiencoach", "familienberater",
        "trauerbegleitung", "systemisch",
        "selbstliebe", "selbstwert",
        "beziehungscoach", "bindungsangst",
        "energetiker", "energetikerin",
        "humanenergetiker", "humanenergetikerin",
    ],
    # ── 母婴 / 育儿 / 家庭 ──
    "母婴/育儿": [
        # Only explicit mommy-BLOGGER / parenting-content signals.
        # Just mentioning "Mama" does NOT exclude — fashion influencers can be moms too.
        "mamablog", "mamablogger", "mamabloggerin",
        "elternblog", "elternblogger",
        "familienblog", "familienblogger",
        "mom blog", "mommy blog", "momblog",
        "mama blog", "mami blog", "mutter blog",
        "erziehung", "elternschaft", "familienbett",
        "familienberat", "stillberatung",
        "hebamme", "wochenbett", "schwanger",
        "dreifachmama", "zweifachmama",
        "drilling", "kinderwunsch", "adoption",
        "homeschool", "grundschule", "kita", "kindergarten",
        "tagesmutter", "spielgruppe", "pflegekind",
        "kindererziehung", "bindungsorientiert",
        "bedürfnisorientiert", "attachment parenting",
        # v0.9.1: from false-negative review
        "babyschlaf", "geburtsvorbereitung", "momlife",
        "mamatipps", "mama von", "mom of",
        "familienalltag", "familienleben",
        "patchworkfamilie", "familiencoach",
        "mamaleben", "mamasein", "familienzeit",
        "geschwister", "kindergeburtstag",
        "mutterliebe", "elternsein",
    ],
    # ── 美食 / 烹饪 / 食谱 / 餐厅 ──
    "美食/烹饪": [
        "rezept", "foodblog", "foodguide", "foodporn",
        "kochen", "backen", "backblog", "fruehstueck",
        "restaurant", "cafe", "foodie", "foodspot",
        "ernaehrung", "ernaehrungsplan", "abnehmen",
        "diaet", "kalorien", "naehrstoff",
        "feinschmecker", "gastro", "gastronomie",
        "streetfood", "foodtruck",
        "kitchen", "cook ", "cooking", "bakery",
        "baecker", "baeckerei", "konditorei",
        # v0.9.1: missing keywords found from false-negative review
        "gerichte", "pfanne", "pfannentesterin",
        "kueche", "küche", "genuss", "schlemmer",
        "gourmet", "foodlover", "foodie",
        "geniessen", "genießen", "mahlzeit",
        "lecker", "schmeckt", "foodstagram",
        "rezeptideen", "kuechenliebe",
        "schnelle küche", "familienküche",
    ],
    # ── 宗教 / 教会 / 灵性 ──
    "宗教/教会": [
        "jesus", "christ", "bibel", "kirche", "gospel",
        "gott ", "gottes", "glaube", "gebet", "pastor",
        "predigt", "evangelium", "testament",
        "christlich", "auferstehung", "heilig",
        "segen", "taufe", "konfirmation",
        "gottesdienst", "gemeinde", "jünger",
        "church", "bible", "ministry", "faith",
        "god ", "christian", "catholic",
        "worship", "prayer", "scripture",
    ],
    # ── 音乐 / DJ / 乐队 / 演出 / 音乐节 ──
    "音乐/演出": [
        "dj ", "producer", "sänger", "sängerin",
        "musiker", "musikerin", "band ", "bands ",
        "festival", "open air", "openair",
        "konzert", "tour", "gig", "bühne",
        "booking@", "bookings@", "mgmt@",
        "aufleger", "remix", "electronic music",
        "techno", "house music",
        "singer", "songwriter", "rapper",
        "ballermann", "schlager",
    ],
    # ── 医疗 / 健康 / 疾病科普 ──
    "医疗/健康": [
        "arzt", "aerztin", "ärztin", "medizin", "klinik",
        "patient", "diagnos", "symptom",
        "erkrankung", "autoimmun", "chronisch",
        "entzuendung", "entzündung", "allergie", "unvertraeglich",
        "darm", "hormon", "schilddruese",
        "crohn", "colitis", "ernaehrungswissenschaft",
        "zahnarzt", "zahnaerztin", "kieferorthopaed",
        "hautarzt", "dermatolog",
        "physiotherap", "osteopath",
        "heilpraktiker", "heilpraktikerin",
        "clinic", "pharmacy", "apotheke",
        "praxis", "sprechstunde",
        # v0.9.1: from false-negative review
        "lipödem", "endometriose", "adenomyose",
        "darmerkrankung", "ernährungsberatung",
        "nährstoffberater", "nährstoffberatung",
        "mikronährstoff", "ganzheitliche gesundheit",
        "stoffwechsel", "hormonbalance",
        "autoimmunerkrankung", "chronisch krank",
        "diabetes", "migräne", "schilddrüsenerkrankung",
    ],
    # ── 宠物 / 动物 ──
    "宠物/动物": [
        # Compound/professional — count first, then don't double-count the base word
        "dog trainer", "dog training", "dog walking", "dog sitter",
        "dogtraining", "dogwalking", "dogsitting",
        "hundetrainer", "hundetraining", "hundeschule", "hundeblog",
        "hundebetreuung", "hundesitter",
        "katzenblog", "katzenbetreuung",
        "welpen", "canine",
        # Base words — each is a separate signal
        "tierarzt", "tierärztin", "tierheim",
        "tierschutz", "haustier",
        "fellnase", "samojede",
        "ridgeback", "pfote", "tierisch",
        "züchter",
        "horse", "pferd",
        "animal", "pet ",
        "reiterhof", "reitschule",
        # v0.9.1: from false-negative review
        "heimtier", "tierbedarf", "tierkommunikation",
        "tierkommunikatorin", "dressurreiterin",
        "dressur", "reitsport", "pferdeliebe",
        "dogmom", "catmom", "hundemama", "katzenmama",
        "haustiere", "tierliebe", "tierwelt",
    ],
    # ── 家居 / DIY / 装修 / 清洁 ──
    "家居/DIY/清洁": [
        "diy", "doityourself", "selbermachen",
        "heimwerken", "heimwerker", "möbel",
        "interior", "interior design", "einrichtung",
        "wohnzimmer", "wohnung", "deko",
        "dekoration", "renovierung", "renovieren",
        "cleaning", "reinigung", "putzen",
        "aufräumen", "ordnung", "ausmisten",
        # v0.9.1: missing keywords from false-negative review
        "hausbau", "neubau", "eigenheim",
        "einrichten", "home decor", "home design",
        "wohnen", "zuhause", "traumhaus",
        "homedeko", "wohnideen", "wohninspo",
        "garderobe", "innenarchitektur",
        "akustikpaneele", "wandgestaltung",
    ],
    # ── 教育 / 教师 / 知识付费 ──
    "教育/知识付费": [
        "lehrerin", "grundschullehrerin",
        "pädagog", "erzieherin",
        "kurs", "kursangebot", "onlinekurs",
        "workshop", "webinar", "coaching programm",
        "ausbildung", "weiterbildung", "fortbildung",
        "nachhilfe", "lerncoach",
        "podcast", "podcaster",
        "schule", "teacher", "academy",
        # v0.9.1: from false-negative review
        "klassenlehrerin", "klassenlehrer",
        "schulalltag", "unterrichtsideen",
        "pädagogin", "lehrkraft", "lehramt",
        "referendariat", "schüler", "schueler",
        "unterrichten", "bildungsbereich",
        "erzieher", "kinderbetreuung",
        "lernmaterial", "unterrichtsmaterial",
        "padlet", "eduki",
    ],
}

# === Male First Name Detection ===
# Common German / European / Turkish male first names.
# Case-insensitive matching against IG fullName first token.
MALE_FIRST_NAMES: frozenset[str] = frozenset(
    "alexander,andreas,benjamin,christian,daniel,david,dennis,dominik,elias,erik,"
    "fabian,felix,florian,frank,gabriel,georg,hannes,hans,henrik,henry,jakob,jan,"
    "jannik,jens,joel,johann,johannes,jonas,jonathan,julian,justin,kai,kevin,"
    "konstantin,lars,leon,leonard,leopold,linus,lorenz,luca,lucas,lukas,manuel,"
    "marc,marcel,marco,markus,martin,matthias,max,maximilian,michael,moritz,"
    "niclas,nico,nicolas,niklas,nikolai,nils,noah,oliver,patrick,paul,peter,"
    "philipp,phillip,ralf,raphael,rene,robert,robin,samuel,sebastian,simon,"
    "stefan,thomas,tim,tobias,tom,uwe,valentin,vincent,wolfgang,yannick,"
    # Missing German / European / Latin male names (from rejection review)
    "pascal,julius,diego,miro,leo,ricardo,cedric,"
    "sascha,sandro,heiko,malte,carsten,thorsten,sven,"
    "germain,wolf,lui,luis,samouz,"
    "tammo,batomae,"
    "adam,andrew,anthony,brandon,brian,charles,chris,connor,derek,dylan,"
    "edward,eric,ethan,george,harry,jack,james,jason,jayden,jeremy,jesse,"
    "john,jordan,joseph,joshua,kyle,liam,logan,luke,mason,matthew,nathan,"
    "nicholas,nick,owen,ryan,sam,tyler,william,zach,"
    "ahmet,ali,arda,baran,berk,burak,can,cem,deniz,efe,emir,emre,"
    "enes,eren,ferhat,furkan,hakan,hasan,huseyin,ibrahim,ismail,kadir,kaan,"
    "kemal,kerem,mehmet,mert,murat,mustafa,omer,onur,orhan,osman,"
    "selim,serdar,serkan,suleyman,tolga,ugur,umut,volkan,yasin,"
    "yigit,yunus,yusuf"
    .split(",")
)
