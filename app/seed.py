from sqlalchemy.orm import Session
from app.models import Category, LibraryItem, User
from app.config import settings

CATEGORIES = [
    {"name": "Fruit",              "icon": "🍎", "sort_order": 1},
    {"name": "Vegetables",         "icon": "🥦", "sort_order": 2},
    {"name": "Spices",             "icon": "🌿", "sort_order": 3},
    {"name": "Frozen Foods",       "icon": "🧊", "sort_order": 4},
    {"name": "Meat & Fish",        "icon": "🥩", "sort_order": 5},
    {"name": "Dairy",              "icon": "🧀", "sort_order": 6},
    {"name": "Nuts",               "icon": "🥜", "sort_order": 7},
    {"name": "Condiments",         "icon": "🫙", "sort_order": 8},
    {"name": "Pantry",             "icon": "🏪", "sort_order": 9},
    {"name": "Drinks",             "icon": "🥤", "sort_order": 10},
    {"name": "Household Products", "icon": "🧹", "sort_order": 11},
]

# (name, icon, category, default_qty, unit, notes, translations)
ITEMS = [
    # ── Fruit ──
    ("Grapes",       "🍇", "Fruit", 1, "pack",  "Purple ones, 20kr (usually in fridge)", {"da": "Vindruer", "it": "Uva", "bg": "Грозде"}),
    ("Apples",       "🍎", "Fruit", 1, "kg",    None, {"da": "Æbler", "it": "Mele", "bg": "Ябълки"}),
    ("Pears",        "🍐", "Fruit", 1, "kg",    None, {"da": "Pærer", "it": "Pere", "bg": "Круши"}),
    ("Bananas",      "🍌", "Fruit", 1, "bunch", None, {"da": "Bananer", "it": "Banane", "bg": "Банани"}),
    ("Clementines",  "🍊", "Fruit", 1, "pack",  None, {"da": "Clementiner", "it": "Clementine", "bg": "Клементини"}),
    ("Lemons",       "🍋", "Fruit", 1, "unit",  None, {"da": "Citroner", "it": "Limoni", "bg": "Лимони"}),
    ("Blueberries",  "🫐", "Fruit", 1, "pack",  None, {"da": "Blåbær", "it": "Mirtilli", "bg": "Боровинки"}),
    ("Kiwi",         "🥝", "Fruit", 1, "unit",  None, {"da": "Kiwi", "it": "Kiwi", "bg": "Киви"}),
    ("Grapefruit",   "🍊", "Fruit", 1, "unit",  None, {"da": "Grapefrugt", "it": "Pompelmo", "bg": "Грейпфрут"}),
    ("Lime",         "🍋‍🟩", "Fruit", 1, "unit",  None, {"da": "Lime", "it": "Lime", "bg": "Лайм"}),
    ("Pineapple",    "🍍", "Fruit", 1, "unit",  None, {"da": "Ananas", "it": "Ananas", "bg": "Ананас"}),

    # ── Vegetables ──
    ("Red Onions",          "🧅", "Vegetables", 1, "unit",  None, {"da": "Rødløg", "it": "Cipolle rosse", "bg": "Червен лук"}),
    ("Carrots",             "🥕", "Vegetables", 1, "pack",  None, {"da": "Gulerødder", "it": "Carote", "bg": "Моркови"}),
    ("Zucchini",            "🥒", "Vegetables", 3, "unit",  None, {"da": "Squash", "it": "Zucchine", "bg": "Тиквички"}),
    ("Garlic",              "🧄", "Vegetables", 1, "unit",  None, {"da": "Hvidløg", "it": "Aglio", "bg": "Чесън"}),
    ("Cucumber",            "🥒", "Vegetables", 1, "unit",  None, {"da": "Agurk", "it": "Cetriolo", "bg": "Краставица"}),
    ("Broccoli",            "🥦", "Vegetables", 1, "unit",  None, {"da": "Broccoli", "it": "Broccoli", "bg": "Броколи"}),
    ("Bell Pepper Mix",     "🫑", "Vegetables", 1, "pack",  None, {"da": "Peberfrugt mix", "it": "Peperoni misti", "bg": "Чушки микс"}),
    ("Snack Bell Peppers",  "🫑", "Vegetables", 1, "pack",  "The orange ones", {"da": "Snack peberfrugter", "it": "Peperoncini snack", "bg": "Мини чушки"}),
    ("Avocado",             "🥑", "Vegetables", 1, "pack",  "Big package with 6-8 avocados", {"da": "Avocado", "it": "Avocado", "bg": "Авокадо"}),
    ("Green Cabbage",       "🥬", "Vegetables", 1, "unit",  None, {"da": "Grøn spidskål", "it": "Cavolo verde", "bg": "Зелено зеле"}),
    ("Cherry Tomatoes",     "🍅", "Vegetables", 1, "pack",  None, {"da": "Cherrytomater", "it": "Pomodorini", "bg": "Чери домати"}),
    ("Hokkaido Pumpkin",    "🎃", "Vegetables", 1, "unit",  None, {"da": "Hokkaido græskar", "it": "Zucca Hokkaido", "bg": "Тиква Хокайдо"}),
    ("Enoki Mushroom",      "🍄", "Vegetables", 1, "pack",  None, {"da": "Enoki svampe", "it": "Funghi enoki", "bg": "Еноки гъби"}),
    ("Potatoes",            "🥔", "Vegetables", 1, "kg",    None, {"da": "Kartofler", "it": "Patate", "bg": "Картофи"}),
    ("Romaine Salad",       "🥬", "Vegetables", 1, "unit",  None, {"da": "Romaine salat", "it": "Lattuga romana", "bg": "Салата Ромейн"}),
    ("Spinach",             "🥬", "Vegetables", 1, "pack",  None, {"da": "Spinat", "it": "Spinaci", "bg": "Спанак"}),
    ("Celery Stalks",       "🥬", "Vegetables", 1, "unit",  None, {"da": "Bladselleri", "it": "Sedano", "bg": "Целина"}),
    ("Ginger",              "🫚", "Vegetables", 1, "unit",  None, {"da": "Ingefær", "it": "Zenzero", "bg": "Джинджифил"}),
    ("Green Onions",        "🧅", "Vegetables", 1, "bunch", None, {"da": "Forårsløg", "it": "Cipollotti", "bg": "Зелен лук"}),
    ("Aubergine",           "🍆", "Vegetables", 1, "unit",  None, {"da": "Aubergine", "it": "Melanzana", "bg": "Патладжан"}),
    ("Purple Cabbage",      "🥬", "Vegetables", 1, "unit",  None, {"da": "Rødkål", "it": "Cavolo rosso", "bg": "Червено зеле"}),
    ("Cauliflower",         "🥦", "Vegetables", 1, "unit",  None, {"da": "Blomkål", "it": "Cavolfiore", "bg": "Карфиол"}),
    ("Rucola",              "🥬", "Vegetables", 1, "pack",  None, {"da": "Rucola", "it": "Rucola", "bg": "Рукола"}),
    ("Mushrooms",           "🍄", "Vegetables", 1, "pack",  None, {"da": "Champignon", "it": "Funghi", "bg": "Гъби"}),

    # ── Spices ──
    ("Parsley",  "🌿", "Spices", 1, "bunch", None, {"da": "Persille", "it": "Prezzemolo", "bg": "Магданоз"}),

    # ── Frozen Foods ──
    ("Frozen Pizza",        "🍕", "Frozen Foods", 1, "unit", None, {"da": "Frossen pizza", "it": "Pizza surgelata", "bg": "Замразена пица"}),
    ("Cauliflower Rice",    "🥦", "Frozen Foods", 1, "pack", None, {"da": "Blomkålsris", "it": "Riso di cavolfiore", "bg": "Ориз от карфиол"}),
    ("Frozen Raspberries",  "🍓", "Frozen Foods", 1, "pack", None, {"da": "Frosne hindbær", "it": "Lamponi surgelati", "bg": "Замразени малини"}),
    ("Frozen Potatoes",     "🥔", "Frozen Foods", 1, "pack", None, {"da": "Frosne kartofler", "it": "Patate surgelate", "bg": "Замразени картофи"}),
    ("Frozen Peas",         "🟢", "Frozen Foods", 1, "pack", None, {"da": "Frosne ærter", "it": "Piselli surgelati", "bg": "Замразен грах"}),
    ("Edamame",             "🫛", "Frozen Foods", 1, "pack", "No shell", {"da": "Edamame", "it": "Edamame", "bg": "Едамаме"}),

    # ── Meat & Fish ──
    ("Sausages",                  "🌭", "Meat & Fish", 1,   "pack",  None, {"da": "Pølser", "it": "Salsicce", "bg": "Наденици"}),
    ("Nora Sausages",             "🌭", "Meat & Fish", 1,   "pack",  "Individually wrapped", {"da": "Nora pølser", "it": "Salsicce Nora", "bg": "Наденици за Нора"}),
    ("Prosciutto Crudo",          "🥓", "Meat & Fish", 2,   "pack",  "Not cotto", {"da": "Prosciutto crudo", "it": "Prosciutto crudo", "bg": "Прошуто крудо"}),
    ("Bacon Cubes",               "🥓", "Meat & Fish", 1,   "pack",  None, {"da": "Baconterninger", "it": "Cubetti di pancetta", "bg": "Бекон на кубчета"}),
    ("Beef Mince",                "🥩", "Meat & Fish", 750, "grams", None, {"da": "Hakket oksekød", "it": "Macinato di manzo", "bg": "Говежда кайма"}),
    ("Chicken Breast",            "🍗", "Meat & Fish", 1,   "pack",  None, {"da": "Kyllingebryst", "it": "Petto di pollo", "bg": "Пилешки гърди"}),
    ("Smoked Salmon",             "🐟", "Meat & Fish", 1,   "pack",  None, {"da": "Røget laks", "it": "Salmone affumicato", "bg": "Пушена сьомга"}),
    ("Pork Chops",                "🥩", "Meat & Fish", 1,   "pack",  None, {"da": "Svinekotelet", "it": "Braciole di maiale", "bg": "Свински котлети"}),
    ("Chicken Drumsticks",        "🍗", "Meat & Fish", 6,   "piece", None, {"da": "Kyllingelår", "it": "Cosce di pollo", "bg": "Пилешки бутчета"}),
    ("Chicken Thighs",            "🍗", "Meat & Fish", 1,   "pack",  None, {"da": "Kyllingeoverlår", "it": "Sovracosce di pollo", "bg": "Пилешки бедра"}),
    ("Salmon",                    "🐟", "Meat & Fish", 1,   "pack",  "From Brugsen", {"da": "Laks", "it": "Salmone", "bg": "Сьомга"}),
    ("Pancetta",                  "🥓", "Meat & Fish", 1,   "pack",  None, {"da": "Pancetta", "it": "Pancetta", "bg": "Панчета"}),
    ("Salami",                    "🥩", "Meat & Fish", 1,   "pack",  "For Nora", {"da": "Salami", "it": "Salame", "bg": "Салам"}),
    ("Chorizo",                   "🌶️", "Meat & Fish", 1,   "pack",  None, {"da": "Chorizo", "it": "Chorizo", "bg": "Чоризо"}),
    ("Prosciutto Cotto / Ham",    "🥩", "Meat & Fish", 1,   "pack",  None, {"da": "Skinke", "it": "Prosciutto cotto", "bg": "Шунка"}),

    # ── Dairy ──
    ("Ostehaps",              "🧀", "Dairy", 1, "pack",   None, {"da": "Ostehaps", "it": "Formaggini", "bg": "Топено сирене"}),
    ("Eggs",                  "🥚", "Dairy", 1, "pack",   None, {"da": "Æg", "it": "Uova", "bg": "Яйца"}),
    ("Cooking Cream",         "🥛", "Dairy", 1, "pack",   "Lactose free only, not regular", {"da": "Madlavningsfløde", "it": "Panna da cucina", "bg": "Готварска сметана"}),
    ("Pizza Dough",           "🍕", "Dairy", 1, "pack",   None, {"da": "Pizzadej", "it": "Impasto per pizza", "bg": "Тесто за пица"}),
    ("Milk for Nora",         "🥛", "Dairy", 1, "unit",   None, {"da": "Mælk til Nora", "it": "Latte per Nora", "bg": "Мляко за Нора"}),
    ("Philadelphia",          "🧀", "Dairy", 1, "unit",   None, {"da": "Philadelphia", "it": "Philadelphia", "bg": "Филаделфия"}),
    ("Cottage Cheese",        "🧀", "Dairy", 1, "unit",   None, {"da": "Hytteost", "it": "Fiocchi di latte", "bg": "Извара"}),
    ("Dry Yeast",             "🍞", "Dairy", 1, "pack",   None, {"da": "Tørgær", "it": "Lievito secco", "bg": "Суха мая"}),
    ("Parmigiano",            "🧀", "Dairy", 1, "unit",   None, {"da": "Parmesan", "it": "Parmigiano", "bg": "Пармезан"}),
    ("Feta",                  "🧀", "Dairy", 1, "pack",   None, {"da": "Feta", "it": "Feta", "bg": "Фета"}),
    ("Butter",                "🧈", "Dairy", 1, "unit",   None, {"da": "Smør", "it": "Burro", "bg": "Масло"}),
    ("Greek Yoghurt 0%",      "🥛", "Dairy", 1, "unit",   None, {"da": "Græsk yoghurt 0%", "it": "Yogurt greco 0%", "bg": "Гръцко кисело мляко 0%"}),
    ("Skyr",                  "🥛", "Dairy", 1, "unit",   None, {"da": "Skyr", "it": "Skyr", "bg": "Скир"}),
    ("Mini Yoghurts for Nora","🥛", "Dairy", 1, "pack",   None, {"da": "Mini yoghurt til Nora", "it": "Mini yogurt per Nora", "bg": "Мини кисело мляко за Нора"}),
    ("Mozzarella Shredded",   "🧀", "Dairy", 1, "pack",   None, {"da": "Revet mozzarella", "it": "Mozzarella grattugiata", "bg": "Настъргана моцарела"}),
    ("Cheddar",               "🧀", "Dairy", 1, "pack",   None, {"da": "Cheddar", "it": "Cheddar", "bg": "Чедър"}),
    ("Sliced Cheese",         "🧀", "Dairy", 1, "pack",   None, {"da": "Skiveskåret ost", "it": "Formaggio a fette", "bg": "Нарязано сирене"}),

    # ── Nuts ──
    ("Walnuts",   "🌰", "Nuts", 1, "pack", "Big pack, in big Netto near chips and nuts", {"da": "Valnødder", "it": "Noci", "bg": "Орехи"}),
    ("Cashews",   "🥜", "Nuts", 1, "pack", None, {"da": "Cashewnødder", "it": "Anacardi", "bg": "Кашу"}),
    ("Hazelnuts", "🌰", "Nuts", 1, "pack", None, {"da": "Hasselnødder", "it": "Nocciole", "bg": "Лешници"}),
    ("Almonds",   "🌰", "Nuts", 1, "pack", None, {"da": "Mandler", "it": "Mandorle", "bg": "Бадеми"}),
    ("Peanuts",   "🥜", "Nuts", 1, "pack", None, {"da": "Jordnødder", "it": "Arachidi", "bg": "Фъстъци"}),

    # ── Condiments ──
    ("Toasted Sesame Oil",    "🫗", "Condiments", 1, "bottle", None, {"da": "Ristet sesamolie", "it": "Olio di sesamo tostato", "bg": "Печено сусамово масло"}),
    ("Panang Curry Paste",    "🍛", "Condiments", 1, "unit",   None, {"da": "Panang karrypasta", "it": "Pasta di curry Panang", "bg": "Пананг къри паста"}),
    ("Apple Cider Vinegar",   "🍶", "Condiments", 1, "bottle", None, {"da": "Æblecidereddike", "it": "Aceto di mele", "bg": "Ябълков оцет"}),
    ("Soya Sauce",            "🍶", "Condiments", 1, "bottle", None, {"da": "Sojasauce", "it": "Salsa di soia", "bg": "Соев сос"}),
    ("Fish Sauce",            "🍶", "Condiments", 1, "bottle", None, {"da": "Fiskesauce", "it": "Salsa di pesce", "bg": "Рибен сос"}),
    ("Rice Vinegar",          "🍶", "Condiments", 1, "bottle", None, {"da": "Riseddike", "it": "Aceto di riso", "bg": "Оризов оцет"}),
    ("Vegetable Broth",       "🥣", "Condiments", 1, "unit",   None, {"da": "Grøntsagsbouillon", "it": "Brodo vegetale", "bg": "Зеленчуков бульон"}),
    ("Chicken Broth",         "🥣", "Condiments", 1, "unit",   None, {"da": "Kyllingebouillon", "it": "Brodo di pollo", "bg": "Пилешки бульон"}),
    ("Maple Syrup",           "🍁", "Condiments", 1, "bottle", None, {"da": "Ahornsirup", "it": "Sciroppo d'acero", "bg": "Кленов сироп"}),
    ("Honey",                 "🍯", "Condiments", 1, "jar",    None, {"da": "Honning", "it": "Miele", "bg": "Мед"}),
    ("Coconut Oil",           "🥥", "Condiments", 1, "jar",    None, {"da": "Kokosolie", "it": "Olio di cocco", "bg": "Кокосово масло"}),
    ("Vanilla Extract",       "🫗", "Condiments", 1, "bottle", None, {"da": "Vaniljeekstrakt", "it": "Estratto di vaniglia", "bg": "Ванилов екстракт"}),

    # ── Pantry ──
    ("Passata",                    "🍅", "Pantry", 1, "unit",   None, {"da": "Passata", "it": "Passata", "bg": "Пасата"}),
    ("Canned Tomatoes",            "🥫", "Pantry", 2, "unit",   None, {"da": "Hakkede tomater", "it": "Pomodori pelati", "bg": "Консервирани домати"}),
    ("Canned Kidney Beans",        "🥫", "Pantry", 2, "unit",   None, {"da": "Kidneybønner", "it": "Fagioli rossi", "bg": "Консервиран червен боб"}),
    ("Cereal for Nora",            "🥣", "Pantry", 1, "pack",   None, {"da": "Morgenmad til Nora", "it": "Cereali per Nora", "bg": "Зърнена закуска за Нора"}),
    ("Olives",                     "🫒", "Pantry", 1, "jar",    None, {"da": "Oliven", "it": "Olive", "bg": "Маслини"}),
    ("Spaghetti",                  "🍝", "Pantry", 1, "pack",   None, {"da": "Spaghetti", "it": "Spaghetti", "bg": "Спагети"}),
    ("Beans",                      "🫘", "Pantry", 1, "can",    None, {"da": "Bønner", "it": "Fagioli", "bg": "Боб"}),
    ("Risotto Rice",               "🍚", "Pantry", 1, "pack",   None, {"da": "Risottoris", "it": "Riso per risotto", "bg": "Ориз за ризото"}),
    ("Peanut Butter",              "🥜", "Pantry", 1, "jar",    None, {"da": "Jordnøddesmør", "it": "Burro di arachidi", "bg": "Фъстъчено масло"}),
    ("Jam",                        "🍓", "Pantry", 1, "jar",    None, {"da": "Marmelade", "it": "Marmellata", "bg": "Конфитюр"}),
    ("Quinoa",                     "🌾", "Pantry", 1, "pack",   None, {"da": "Quinoa", "it": "Quinoa", "bg": "Киноа"}),
    ("Black Olives (pitted)",      "🫒", "Pantry", 1, "jar",    None, {"da": "Sorte oliven uden sten", "it": "Olive nere denocciolate", "bg": "Черни маслини без костилки"}),
    ("Prunes",                     "🫐", "Pantry", 1, "pack",   None, {"da": "Svesker", "it": "Prugne secche", "bg": "Сушени сливи"}),
    ("Smoothies",                  "🥤", "Pantry", 1, "pack",   None, {"da": "Smoothies", "it": "Smoothie", "bg": "Смути"}),
    ("Mayonnaise",                 "🫙", "Pantry", 1, "jar",    "Hellmanns", {"da": "Mayonnaise", "it": "Maionese", "bg": "Майонеза"}),
    ("Tahini",                     "🫙", "Pantry", 1, "jar",    None, {"da": "Tahini", "it": "Tahina", "bg": "Тахан"}),
    ("Dark Chocolate",             "🍫", "Pantry", 1, "unit",   None, {"da": "Mørk chokolade", "it": "Cioccolato fondente", "bg": "Тъмен шоколад"}),
    ("Basmati Rice",               "🍚", "Pantry", 1, "pack",   None, {"da": "Basmatiris", "it": "Riso basmati", "bg": "Ориз басмати"}),
    ("Rice Cakes",                 "🍘", "Pantry", 1, "pack",   None, {"da": "Riskager", "it": "Gallette di riso", "bg": "Оризови бисквити"}),
    ("Concentrated Tomato Paste",  "🍅", "Pantry", 1, "unit",   None, {"da": "Tomatpuré", "it": "Concentrato di pomodoro", "bg": "Доматено пюре"}),
    ("Chia Seeds",                 "🌱", "Pantry", 1, "pack",   None, {"da": "Chiafrø", "it": "Semi di chia", "bg": "Семена от чиа"}),
    ("Pasta",                      "🍝", "Pantry", 1, "pack",   None, {"da": "Pasta", "it": "Pasta", "bg": "Паста"}),
    ("Wholegrain Toast for Nora",  "🍞", "Pantry", 1, "unit",   None, {"da": "Fuldkornstoast til Nora", "it": "Pane integrale per Nora", "bg": "Пълнозърнест тост за Нора"}),
    ("Flour",                      "🌾", "Pantry", 1, "pack",   None, {"da": "Mel", "it": "Farina", "bg": "Брашно"}),
    ("Oats",                       "🌾", "Pantry", 1, "pack",   None, {"da": "Havregryn", "it": "Fiocchi d'avena", "bg": "Овесени ядки"}),
    ("Shredded Coconut",           "🥥", "Pantry", 1, "pack",   None, {"da": "Kokosmel", "it": "Cocco grattugiato", "bg": "Кокосови стърготини"}),
    ("Coconut Milk",               "🥥", "Pantry", 1, "can",    None, {"da": "Kokosmælk", "it": "Latte di cocco", "bg": "Кокосово мляко"}),

    # ── Drinks ──
    ("White Wine",                "🍷", "Drinks", 1, "bottle", None, {"da": "Hvidvin", "it": "Vino bianco", "bg": "Бяло вино"}),
    ("Sparkling Water",           "💧", "Drinks", 1, "pack",   None, {"da": "Danskvand", "it": "Acqua frizzante", "bg": "Газирана вода"}),
    ("Iced Tea Peach for Nora",   "🧃", "Drinks", 1, "pack",   None, {"da": "Iste fersken til Nora", "it": "Tè freddo pesca per Nora", "bg": "Студен чай праскова за Нора"}),
    ("Tonic",                     "🥂", "Drinks", 1, "unit",   None, {"da": "Tonic", "it": "Tonica", "bg": "Тоник"}),

    # ── Household Products ──
    ("Birthday Hats",              "🎉", "Household Products", 1, "pack",   None, {"da": "Fødselsdagshatte", "it": "Cappellini di compleanno", "bg": "Парти шапки"}),
    ("Cleaning Gloves",            "🧤", "Household Products", 1, "pack",   None, {"da": "Rengøringshandsker", "it": "Guanti per pulizia", "bg": "Ръкавици за почистване"}),
    ("Swimming Diapers",           "🩱", "Household Products", 1, "pack",   None, {"da": "Svømmebleer", "it": "Pannolini da piscina", "bg": "Бански пелени"}),
    ("Dishwashing Tablets",        "🫧", "Household Products", 1, "pack",   None, {"da": "Opvasketabs", "it": "Pastiglie lavastoviglie", "bg": "Таблетки за съдомиялна"}),
    ("Toothpaste Sensodyne",       "🪥", "Household Products", 1, "unit",   None, {"da": "Tandpasta Sensodyne", "it": "Dentifricio Sensodyne", "bg": "Паста за зъби Sensodyne"}),
    ("Big Trash Bags",             "🗑️", "Household Products", 1, "pack",   None, {"da": "Store skraldeposer", "it": "Sacchi spazzatura grandi", "bg": "Големи чували за боклук"}),
    ("Kleenex",                    "🤧", "Household Products", 1, "pack",   None, {"da": "Kleenex", "it": "Fazzoletti", "bg": "Носни кърпички"}),
    ("Softener",                   "🧴", "Household Products", 1, "bottle", None, {"da": "Skyllemiddel", "it": "Ammorbidente", "bg": "Омекотител"}),
    ("Kitchen Paper",              "🧻", "Household Products", 1, "pack",   None, {"da": "Køkkenrulle", "it": "Carta da cucina", "bg": "Кухненска хартия"}),
    ("Wet Wipes",                  "🧻", "Household Products", 1, "pack",   None, {"da": "Vådservietter", "it": "Salviette umidificate", "bg": "Мокри кърпички"}),
    ("Dishwasher Cleaning Liquid", "🫧", "Household Products", 1, "bottle", None, {"da": "Opvaskemiddel", "it": "Liquido lavastoviglie", "bg": "Препарат за съдове"}),
    ("Toothpaste Nora",            "🪥", "Household Products", 1, "unit",   None, {"da": "Tandpasta til Nora", "it": "Dentifricio per Nora", "bg": "Паста за зъби за Нора"}),
]


def seed_database(db: Session):
    if db.query(Category).count() > 0:
        return

    admin = User(name="Admin", api_key=settings.admin_api_key, role="admin", language="en")
    user = User(name="User", api_key=settings.user_api_key, role="user", language="en")
    db.add_all([admin, user])
    db.flush()

    cat_map = {}
    for c in CATEGORIES:
        cat = Category(**c)
        db.add(cat)
        db.flush()
        cat_map[c["name"]] = cat.id

    for name, icon, cat_name, qty, unit, notes, translations in ITEMS:
        item = LibraryItem(
            name=name,
            icon=icon,
            category_id=cat_map[cat_name],
            default_quantity=qty,
            unit=unit,
            notes=notes,
            translations=translations or {},
        )
        db.add(item)

    db.commit()
