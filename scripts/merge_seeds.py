"""Merge all new seeds from recent checks, dedup, clean, and write to file."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Seeds from batch 1 (36 new)
batch1 = [
    "yuleeeeed", "natalieyears", "lica_vee", "annaaaurelia", "jennifer_abigail",
    "fatimacheriee", "malenaa.sch", "shalinachantal", "jeylaviee", "luise.wndt",
    "m4rielouise", "jana_bln.hag", "marina.koehler", "f1nja.mar1e", "emilia.peter",
    "felicia.felic", "romesaa._01", "mrsma.a", "lillysolti_", "sportschu",
    "n.mariaam", "Kontrajunkie", "liloxxloli", "melli_plachta", "wiktorialipiecc",
    "lisa.lindinger", "by_sevnur", "rabiasnrk", "lyssi_xcii", "mamaheubl",
    "aleynaoezkann", "ay1ena", "sarah.fbr", "erpel.ine", "yaraline",
    "dilarajnur", "wencke.sperveslage", "fit.bernaa", "la_vie_est_belle70",
    "maraknewel", "maike.produkttesterin", "kiamisu_", "betuel.interior",
    "jessie.matata", "elmessa__", "josephine.krk",
]

# Seeds from batch 2 (141 new)
batch2 = [
    "valerie_s_secret", "anniju__", "tori.smi", "sarahsunita", "chanteljavin",
    "lauraverwi", "teresa.jg", "zoeliss", "whatnanaloves", "suareza_shameti",
    "leilas_lookbook", "denise_kln", "carolin_.1", "saskiaceeline", "viviiksj",
    "amandadifine", "elisavrb", "sophiia.ugc", "yuloez", "minimalandso",
    "kristin_zirnsak", "dailynadjuschka", "annaxfo", "julia.kammerer",
    "annarossow", "maddy", "lauramichelleee", "hannaahcarolina",
    "growingannanas", "paola", "phiaka", "aliciaandritschke", "stellaaelena",
    "laurajoelle", "juleslw", "nelipies", "farinaopoku", "natalie_stommel",
    "wioleta_daria", "lauraabla", "lizkaeber", "lejannik", "mandybork",
    "leoonie", "alinamour", "juliabeautx", "dagibee", "nonakanal",
    "coupleontour", "inaontour", "jasminazizam", "samira.sfiii", "sarellax3",
    "cocobeautea", "annkathrin", "sindiarifi", "dianazurloewen", "luisalion",
    "carmushka", "lenagercke", "fabienne.bethmann", "thecandycrash",
    "ellenundradieschen", "lenaaaaaaaaaaaaaa_", "jasmine.jung", "malika_babel",
    "nancybeauty", "katharinaxeniaa", "julesboringlife", "ninapiaskowy",
    "sersn20.10", "catharinamaranca", "ninasuess", "loulou", "alaa.aloulabi",
    "ziba_makeupartist", "annavonklinski", "melisacarolinatatar", "cajaroli",
    "marriamalk", "hanadidiab", "nadia.vilaplana", "sarahfranssen",
    "twenty4tim", "tanjamakaric_", "chriena", "hannaweig", "romysbasics",
    "docalina", "elenaannamayr", "miajeana", "starkellen", "dani.klieber",
    "dani_nanaa", "loucafee", "lisa.mieschke", "annisofiagerlach",
    "verena_ahmann", "sarahtey_", "jaquelinevazzola", "audreyafs", "itsdolita",
    "patriziapalme", "paulasenfkorn", "ann.jonxs", "louisa_mazzurana",
    "sandra_worldtraveler", "dein_bestes_foto", "angelique.st88", "van.tuxx",
    "blvckgull", "nasrin.eileen", "svetlanabjelan", "daisy.wolanski",
    "birteko", "healthy_mandy", "aleynamovez", "jowuensche", "dilaraa.s",
    "anna_strigl", "minnie.mouse_daniii", "jezzgross.official",
    "lifewithaliina", "andragoganoff", "nadinebreaty", "besassique",
    "chiaratews", "pamela_rf", "pdm.clara", "lucy_lacht", "hannahmria",
    "alionagris", "sophodoph", "jessica.karakas", "squadbelles",
    "andrea_subotic", "joanpeachy", "blanca_friedrich", "by.isabelyvonne",
    "diademlori", "thesaltypassports",
]

# Batch 3 (299 new) — read from a temp file if available
batch3_raw = [
    "malvareezz", "Maria_Gabriela", "katrinpalme", "leonieloh_",
    "zara_secret", "SonnyLoops", "lauramaria.rpa", "sosopinkypie",
    "sarah.theiler", "vanessa.mai", "stefaniehelen", "paolaparente",
    "elif_sima", "doresaa", "annakova", "nini_flash", "payton.r",
    "nathalie_bw", "verenakerth", "amelie_weissenberger", "merv.ozkn",
    "chanajk_", "sophiebreuer99", "leylalahouar", "shanicemessina",
    "adorablecaro", "donnaromina", "liv.yah", "melina.hoch", "juliaschwab",
    "vanniteske", "dodipi", "junamanaj", "emmawinterhagen",
    "annachristinaschwartz", "carina", "janinewiggert", "LuisaCrash",
    "paulakraemer", "minicuta", "joyyy_tv", "selinamour", "monemahoni",
    "laraspengler", "mashabk", "aliciaawa", "kisu", "jolinamennen",
    "carinaspoon", "amiraaly", "ergibardhollari", "anettaberi_",
    "mymiapage", "thelifeoflibs", "deborah_tmz", "franzidohn", "neleamiri",
    "elenakamperi", "lolaweippert", "malikadzumaev", "hannah.muehi",
    "gymgona", "isismarianiedecken", "alessawinter", "lara_bsmnn",
    "shawnysander", "linda.sza", "e1isabethng", "laraaceliaa", "mvb",
    "holylora", "linasoophiee", "llolarosalie", "ronjanicola", "sarahrohde_",
    "sophiepirrung", "rike_de", "angeeeelia", "cemre.fe", "asenaneuhoff",
    "fusunlindner", "itsmisabell", "alisia.ludwig", "alexa_breit",
    "melissadeines", "sarahx.ws", "kimschiele", "stella_tiana",
    "celinebethmann", "sarahposch", "jessyhartel", "rominapalm",
    "jessideoliveira", "aleandrafrerk", "emmaaurora", "mrs.lilly___",
    "tahneechristin", "citamaass", "jasmin.diem", "rabiosa",
    "ingridelisabethh", "linuschka", "jasi_xx3", "melissadamilia",
    "maximeee", "pelican_bay", "tanja_cruz", "xapiaxa_", "alicia.andrich",
    "stephifashion", "karokauer", "annistoerling", "michivonwant",
    "gisellefilyos", "elena.zbt", "annie.shr", "beautylishar",
    "michelleschellhaas", "alinakhani", "saracrumbleleg", "xfibii",
    "kassi", "linlouuu", "mariagabrielasantos", "revedtv", "ninajuliasimon",
    "mariesophieglm", "lori.ality", "honeypuu", "karlotta.nila",
    "helenabeckmann", "xmeliina", "harriet.herbigmatten", "_mandyhess_",
    "tatumsara", "joana.salamone", "cocobasics", "anna.gazanis",
    "louisa_masciullo", "julia.schulze_official", "mathilda.mkh",
    "rashan.mh", "janalibra", "weweskaa", "vanessa_zinner",
    "baochiinguyen", "yuki_injo", "lethilda", "emilyy", "alissamarija",
    "maxinereuker", "stinalex", "eyasminbal", "itsmanjuu", "johanna_einhorn",
    "filiparies", "ruppert.alysa", "emilia.nia", "therrmann.mom",
    "honeyhannii", "lenimariee", "jenefer_riili", "alexis.blond",
    "lenaglams", "mona.mxe", "veroniquesophie", "lenajensn", "lisaschnapa",
    "salomeenaa", "nataliavogel_", "tanja.fleger", "berivansworld",
    "hannahtulnik", "cindyjane", "kimiloveslipsticks", "olesja.schalnich",
    "laurafruitfairy", "susamamma", "miabender", "aliciaknebel",
    "selfiesandra", "eyfreundin.official", "lenamauteofficial",
    "anastasia.samardzijaa", "zoetastetravel", "leni.pie", "storiesofdine",
    "jil.rock", "ina.0601", "franzitoeroek", "stefiedrost", "sinasleben",
    "_ninovaa", "hannahsteffens", "idaluciam", "elina_bambina", "its.a_mela",
    "lexikar", "viviiiii93", "goingdownswingin", "lydiaruizaguilera",
    "chantalicia", "andraantn", "jessidcq", "sophiestriedl", "sara.xts",
    "miss.talina", "salilas__", "ninacvc", "its.gabriiele",
    "annabelle.koennecke", "michelle.cll", "aylin.end", "aaliyahmts",
    "vanessajackzon_", "thommy_cologne_", "jileileen", "malilogs",
    "life.to.go", "rebeccasbrow", "beahyggespreder", "kates.diary",
    "melindaunddawid", "jessicagelke", "yvonnepferrer", "jenniferlange",
    "einfachleichter__", "fatmasstory_", "nessiontour", "theresakirchnerr",
    "paula_doeringer", "linadueren", "edda.elisa", "himbeersahnetorte",
    "dr.emi", "verenapausder", "gerid_rux", "typischcalvin", "die_togs",
    "imsemdiary.official", "sophieklex", "josephine_welsch",
    "graceundriza", "julia.thiele_family", "_kikidoyouloveme_",
    "anajohnson", "annamariadamm", "lusandraa", "denisemerten",
    "diewalsers.official", "saskiamichalski", "gehmalzumbekka",
    "vladimir.gunjic", "trinksaufmich", "schwesta_ebra", "arifewoehrle",
    "julezz.offiziell", "kampi.c", "merleschoon", "michellestny",
    "thorina_s", "samiraxrieger", "sidneey.marie", "milenaerlenbach",
    "jennifersaro", "marci", "joi_bella", "aliciasmumlife", "sarabirgani",
    "aylinaphrodite", "mariejohnson", "frau_mone", "aline.kaplan",
    "laberrhababer.official", "cima.villa", "olali1987", "antonia_hemmer",
    "annaadamyan", "kathrinbommann", "franzykoenig",
    "consciouslyoverthinking", "juliagrw85", "ana.kohler",
    "johanna.albeert", "alinaristenpart", "thatsluri", "thats.mi",
    "alicia.isa.belle", "cheyennepahde", "jill_langee", "sabinamarkin",
    "sina.anjulie", "katharinaanjs", "maximemoeckl", "cathyhummels",
    "annasophiegottwald", "sarah.harrison.official",
]

# Merge all
all_seeds = set()
for s in batch1 + batch2 + batch3_raw:
    s = s.strip().strip('"').strip()
    if s:
        all_seeds.add(s.lower())

# Check against processed
processed = set()
proc_file = ROOT / "data" / "seeds_processed.txt"
with open(proc_file, "r", encoding="utf-8") as f:
    for line in f:
        s = line.strip()
        if s:
            processed.add(s.lower())

new = sorted(all_seeds - processed)

print(f"Total merged: {len(all_seeds)}")
print(f"Already processed: {len(all_seeds) - len(new)}")
print(f"New seeds to run: {len(new)}")

# Write
out = ROOT / "data" / "seeds_new_combined.txt"
with open(out, "w", encoding="utf-8") as f:
    for s in new:
        f.write(s + "\n")
print(f"Written to {out}")
