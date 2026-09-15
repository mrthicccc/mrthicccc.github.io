// Seeded demo dataset. Swap this module for live provider feeds (Ticketmaster,
// Eventbrite, Meetup) without touching the UI — see getEvents() in app.js.

const CITIES = {
  london:    { name: 'London',    country: 'United Kingdom', lat: 51.5074, lng: -0.1278, currency: '£', lang: 'English' },
  paris:     { name: 'Paris',     country: 'France',         lat: 48.8566, lng: 2.3522,  currency: '€', lang: 'French' },
  newyork:   { name: 'New York',  country: 'United States',  lat: 40.7128, lng: -74.0060, currency: '$', lang: 'English' },
  tokyo:     { name: 'Tokyo',     country: 'Japan',          lat: 35.6762, lng: 139.6503, currency: '¥', lang: 'Japanese' },
  barcelona: { name: 'Barcelona', country: 'Spain',          lat: 41.3851, lng: 2.1734,  currency: '€', lang: 'Spanish' },
  berlin:    { name: 'Berlin',    country: 'Germany',        lat: 52.5200, lng: 13.4050, currency: '€', lang: 'German' }
};

const CATEGORIES = {
  music:     { label: 'Music',     icon: '♪',  c1: '#7c3aed', c2: '#c026d3' },
  food:      { label: 'Food',      icon: '✦',  c1: '#ea580c', c2: '#f59e0b' },
  art:       { label: 'Art',       icon: '◆',  c1: '#0891b2', c2: '#6366f1' },
  sports:    { label: 'Sports',    icon: '▲',  c1: '#059669', c2: '#65a30d' },
  nightlife: { label: 'Nightlife', icon: '◐',  c1: '#be123c', c2: '#7c3aed' },
  culture:   { label: 'Culture',   icon: '❖',  c1: '#b45309', c2: '#0d9488' },
  festival:  { label: 'Festival',  icon: '✺',  c1: '#db2777', c2: '#f97316' },
  theatre:   { label: 'Theatre',   icon: '❋',  c1: '#4f46e5', c2: '#be123c' }
};

// dayOffset is days from today, so the dataset never goes stale.
const EVENTS = [
  { id:'ldn-1', city:'london', title:'Camden Jazz Nights', venue:'Jazz Café, Camden', lat:51.5416, lng:-0.1462, dayOffset:0, time:'20:00', hours:3, price:18, category:'music', organizer:'Camden Live',
    description:'A weekly residency pulling in the best of London\'s young jazz scene. Expect brass-heavy sets, a packed floor and a late licence. Doors at 7pm, first set at 8.' },
  { id:'ldn-2', city:'london', title:'Borough Market Street Food Festival', venue:'Borough Market, Southwark', lat:51.5055, lng:-0.0910, dayOffset:2, time:'11:00', hours:8, price:0, category:'food', organizer:'Borough Market',
    description:'Forty traders take over the market halls for a weekend of open-fire cooking, rare-breed charcuterie and small-batch everything. Free to wander, pay as you eat.' },
  { id:'ldn-3', city:'london', title:'Tate Modern: Light & Form', venue:'Tate Modern, Bankside', lat:51.5076, lng:-0.0994, dayOffset:4, time:'10:00', hours:9, price:16, category:'art', organizer:'Tate',
    description:'A major survey of post-war light installation, from Turrell\'s perceptual cells to contemporary Nigerian and Korean practice. Timed entry across the Blavatnik Building.' },
  { id:'ldn-4', city:'london', title:'West End: The Midnight Carousel', venue:'Lyceum Theatre, Covent Garden', lat:51.5115, lng:-0.1200, dayOffset:6, time:'19:30', hours:3, price:45, category:'theatre', organizer:'Lyceum',
    description:'A new musical set across one night in 1920s Soho. Critics have called the staging "the most inventive thing in the West End this decade".' },
  { id:'ldn-5', city:'london', title:'Hyde Park Sunrise 10K', venue:'Hyde Park', lat:51.5073, lng:-0.1657, dayOffset:9, time:'07:00', hours:3, price:25, category:'sports', organizer:'RunLDN',
    description:'Chip-timed 10K on a flat two-lap course around the Serpentine. Pacers for every target from 40 to 75 minutes. Bag drop and coffee at the finish.' },
  { id:'ldn-6', city:'london', title:'Shoreditch Rooftop Sessions', venue:'Netil House, Hackney', lat:51.5362, lng:-0.0596, dayOffset:3, time:'18:00', hours:6, price:12, category:'nightlife', organizer:'Netil360',
    description:'Sunset to late on an east London rooftop with a skyline view, house and disco on a proper soundsystem, and a bar that does not mess about.' },
  { id:'ldn-7', city:'london', title:'British Museum Late: Ancient Voices', venue:'British Museum, Bloomsbury', lat:51.5194, lng:-0.1270, dayOffset:11, time:'18:30', hours:4, price:0, category:'culture', organizer:'British Museum',
    description:'The galleries stay open late with live performance responding to the collection — Mesopotamian poetry read aloud, Assyrian reliefs by torchlight. Free, no booking.' },
  { id:'ldn-8', city:'london', title:'Notting Hill Vintage Market', venue:'Portobello Road', lat:51.5169, lng:-0.2058, dayOffset:5, time:'09:00', hours:7, price:0, category:'culture', organizer:'Portobello Traders',
    description:'The Friday edition is the one locals go to: less crowded than Saturday, better prices, and the clothing dealers at the north end actually have time to talk.' },

  { id:'par-1', city:'paris', title:'Montmartre Vineyard Harvest', venue:'Clos Montmartre, 18e', lat:48.8886, lng:2.3400, dayOffset:7, time:'11:00', hours:9, price:0, category:'festival', organizer:'Mairie du 18e',
    description:'Paris\'s last working vineyard brings in the harvest with a street parade, brass bands and tastings down the Rue des Saules. A genuine neighbourhood affair.' },
  { id:'par-2', city:'paris', title:'Le Marais Wine & Cheese Walk', venue:'Rue des Rosiers, 4e', lat:48.8571, lng:2.3595, dayOffset:2, time:'17:00', hours:3, price:38, category:'food', organizer:'Paris Food Walks',
    description:'Five stops, five pairings, one very opinionated guide. Includes a cave à fromage most tourists walk straight past and a natural wine bar with no sign on the door.' },
  { id:'par-3', city:'paris', title:'Musée d\'Orsay: Impressionist Nights', venue:'Musée d\'Orsay, 7e', lat:48.8600, lng:2.3266, dayOffset:4, time:'18:00', hours:4, price:14, category:'art', organizer:'Musée d\'Orsay',
    description:'Thursday late opening with the Impressionist floor kept deliberately dim and uncrowded. The Monets in low light are a completely different painting.' },
  { id:'par-4', city:'paris', title:'Seine Sunset Jazz Cruise', venue:'Port de Solférino, 7e', lat:48.8614, lng:2.3232, dayOffset:0, time:'19:30', hours:2, price:29, category:'music', organizer:'Canauxrama',
    description:'Ninety minutes downriver and back with a trio playing standards on the open deck. Boards at Solférino, passes under seven bridges, ends as the tower starts sparkling.' },
  { id:'par-5', city:'paris', title:'Pigalle Underground', venue:'Rue Frochot, 9e', lat:48.8821, lng:2.3376, dayOffset:6, time:'23:00', hours:6, price:15, category:'nightlife', organizer:'Le Carmen',
    description:'A nineteenth-century mansion turned club — gilt ceilings, a tiny dancefloor, and bookings that lean French touch and leftfield house. Queue before midnight.' },
  { id:'par-6', city:'paris', title:'Stade de France: International Rugby', venue:'Stade de France, Saint-Denis', lat:48.9244, lng:2.3601, dayOffset:14, time:'21:00', hours:3, price:65, category:'sports', organizer:'FFR',
    description:'Eighty thousand people and La Marseillaise sung properly. Category 3 seats behind the posts are the best value in the ground. RER B and D to Stade de France.' },
  { id:'par-7', city:'paris', title:'Canal Saint-Martin Open Air Cinema', venue:'Quai de Valmy, 10e', lat:48.8715, lng:2.3656, dayOffset:8, time:'21:30', hours:3, price:0, category:'festival', organizer:'Ville de Paris',
    description:'Free screenings projected onto a canal-side wall. Bring something to sit on and something to drink; the whole quai turns up an hour early to claim space.' },

  { id:'nyc-1', city:'newyork', title:'Brooklyn Warehouse Sessions', venue:'Bushwick, Brooklyn', lat:40.7061, lng:-73.9219, dayOffset:0, time:'22:00', hours:6, price:25, category:'music', organizer:'Elsewhere',
    description:'Three rooms, three completely different bills — live band in the hall, techno on the roof, something experimental in the basement. One wristband covers all of it.' },
  { id:'nyc-2', city:'newyork', title:'Smorgasburg Williamsburg', venue:'Marsha P. Johnson State Park', lat:40.7220, lng:-73.9615, dayOffset:3, time:'11:00', hours:7, price:0, category:'food', organizer:'Smorgasburg',
    description:'A hundred vendors on the East River with the Manhattan skyline behind them. Come hungry and early — the queues for the breakout stalls get absurd after 1pm.' },
  { id:'nyc-3', city:'newyork', title:'MoMA After Dark', venue:'MoMA, Midtown', lat:40.7614, lng:-73.9776, dayOffset:5, time:'17:30', hours:4, price:22, category:'art', organizer:'MoMA',
    description:'Members\' evening opened to the public once a month. Full collection access, a DJ in the atrium, and the fifth floor almost empty by 8pm.' },
  { id:'nyc-4', city:'newyork', title:'Broadway: The Velvet Room', venue:'Booth Theatre, Theater District', lat:40.7590, lng:-73.9845, dayOffset:7, time:'20:00', hours:3, price:89, category:'theatre', organizer:'Shubert',
    description:'A two-hander about a failing Harlem jazz club, running at the Booth through the season. Rush tickets released at the box office each morning at 10.' },
  { id:'nyc-5', city:'newyork', title:'Central Park Half Marathon', venue:'Central Park', lat:40.7829, lng:-73.9654, dayOffset:12, time:'07:30', hours:4, price:40, category:'sports', organizer:'NYRR',
    description:'Two loops of the park including Harlem Hill twice, which is exactly as bad as it sounds. Strong crowd support along the East Drive.' },
  { id:'nyc-6', city:'newyork', title:'Lower East Side Gallery Crawl', venue:'Orchard Street, LES', lat:40.7185, lng:-73.9885, dayOffset:4, time:'18:00', hours:4, price:0, category:'art', organizer:'LES Gallery Association',
    description:'Twenty-odd galleries open late on the first Thursday with new shows and free wine. Pick up the printed map at any participating space.' },
  { id:'nyc-7', city:'newyork', title:'Harlem Gospel Sunday', venue:'Adam Clayton Powell Jr. Blvd', lat:40.8116, lng:-73.9465, dayOffset:6, time:'10:00', hours:2, price:30, category:'culture', organizer:'Harlem Heritage',
    description:'A guided visit to a working Sunday service with historical context on the neighbourhood beforehand. Respectful dress requested; this is a congregation, not a show.' },
  { id:'nyc-8', city:'newyork', title:'Queens Night Market', venue:'Flushing Meadows Corona Park', lat:40.7458, lng:-73.8458, dayOffset:9, time:'17:00', hours:6, price:0, category:'food', organizer:'Queens Night Market',
    description:'Ninety-plus vendors representing something like forty countries, with a deliberate price cap so everything stays affordable. Arguably the most diverse food event in America.' },

  { id:'tky-1', city:'tokyo', title:'Shibuya Night Market', venue:'Miyashita Park, Shibuya', lat:35.6614, lng:139.7010, dayOffset:0, time:'17:00', hours:6, price:0, category:'food', organizer:'Shibuya Ward',
    description:'Yatai-style stalls along the elevated park deck — yakitori, takoyaki, natural wine — with the Shibuya crossing lights below. Entry free, cash preferred at most stalls.' },
  { id:'tky-2', city:'tokyo', title:'teamLab: Ephemeral', venue:'Azabudai Hills, Minato', lat:35.6595, lng:139.7396, dayOffset:3, time:'10:00', hours:10, price:3800, category:'art', organizer:'teamLab',
    description:'The digital art collective\'s newest permanent space. Rooms respond to where you stand and what you touch. Wear something you do not mind getting slightly wet.' },
  { id:'tky-3', city:'tokyo', title:'Golden Gai Bar Crawl', venue:'Golden Gai, Shinjuku', lat:35.6938, lng:139.7036, dayOffset:5, time:'20:00', hours:4, price:4500, category:'nightlife', organizer:'Tokyo Night Walks',
    description:'Six alleys, two hundred bars, most seating six people. A guide gets you past the members-only doors and explains the cover charge etiquette that trips up visitors.' },
  { id:'tky-4', city:'tokyo', title:'Sumida River Fireworks', venue:'Asakusa, Taito', lat:35.7148, lng:139.8067, dayOffset:10, time:'19:00', hours:2, price:0, category:'festival', organizer:'Sumida Ward',
    description:'Twenty thousand shells over the river in a tradition running since 1733. Free to watch from the banks; arrive by mid-afternoon if you want to actually see it.' },
  { id:'tky-5', city:'tokyo', title:'Grand Sumo Tournament', venue:'Ryogoku Kokugikan, Sumida', lat:35.6968, lng:139.7933, dayOffset:8, time:'08:30', hours:10, price:8000, category:'sports', organizer:'Japan Sumo Association',
    description:'Lower divisions from the morning, the ranked wrestlers from mid-afternoon, and the whole hall on its feet by the final bouts around 5.30pm.' },
  { id:'tky-6', city:'tokyo', title:'Shinjuku Jazz Basement', venue:'Nishi-Shinjuku', lat:35.6896, lng:139.6917, dayOffset:2, time:'19:30', hours:3, price:2500, category:'music', organizer:'Pit Inn',
    description:'A basement room that has been booking serious Japanese jazz since 1965. No talking during sets — the audience takes that genuinely seriously.' },
  { id:'tky-7', city:'tokyo', title:'Yoyogi Park Seasonal Picnic', venue:'Yoyogi Park, Shibuya', lat:35.6720, lng:139.6949, dayOffset:6, time:'11:00', hours:8, price:0, category:'festival', organizer:'Yoyogi Park',
    description:'Half of Tokyo on a tarpaulin. Convenience-store supplies are entirely acceptable and the rockabilly dancers by the Harajuku gate are a permanent fixture.' },

  { id:'bcn-1', city:'barcelona', title:'Festa Major de Gràcia', venue:'Vila de Gràcia', lat:41.4036, lng:2.1561, dayOffset:4, time:'12:00', hours:12, price:0, category:'festival', organizer:'Ajuntament de Barcelona',
    description:'Streets compete to decorate themselves and the results are genuinely extraordinary — whole blocks turned into underwater scenes or jungles out of recycled material. Free, all week, very loud.' },
  { id:'bcn-2', city:'barcelona', title:'Tapas Trail: El Born', venue:'Carrer de l\'Argenteria', lat:41.3840, lng:2.1820, dayOffset:2, time:'19:00', hours:3, price:42, category:'food', organizer:'Devour Barcelona',
    description:'Four bars across El Born and the Gothic Quarter, including a vermouth bar that has been in the same family since 1902. Vegetarian options on request.' },
  { id:'bcn-3', city:'barcelona', title:'Sagrada Família Twilight Tour', venue:'Sagrada Família, Eixample', lat:41.4036, lng:2.1744, dayOffset:3, time:'18:30', hours:2, price:33, category:'culture', organizer:'Sagrada Família',
    description:'The last entry slot, when the western stained glass throws the whole nave orange and red. Guided, small groups, tower access extra.' },
  { id:'bcn-4', city:'barcelona', title:'Barceloneta Beach Club', venue:'Passeig Marítim', lat:41.3784, lng:2.1925, dayOffset:5, time:'22:00', hours:6, price:20, category:'nightlife', organizer:'Opium',
    description:'Open-sided club straight onto the sand. Gets going properly around 1am and does not stop until the sun is up over the water.' },
  { id:'bcn-5', city:'barcelona', title:'Camp Nou Matchday', venue:'Estadi Olímpic, Montjuïc', lat:41.3647, lng:2.1558, dayOffset:11, time:'21:00', hours:3, price:75, category:'sports', organizer:'FC Barcelona',
    description:'League fixture under the lights. Get there early for the anthem and leave your bag at the hotel — the stadium bag policy is strictly enforced.' },
  { id:'bcn-6', city:'barcelona', title:'Museu Picasso Late', venue:'Carrer Montcada, El Born', lat:41.3851, lng:2.1808, dayOffset:7, time:'18:00', hours:4, price:12, category:'art', organizer:'Museu Picasso',
    description:'Thursday evenings at reduced admission. The early Barcelona work — painted when he was fourteen — is the reason to come, and it is upstairs and usually empty.' },
  { id:'bcn-7', city:'barcelona', title:'Magic Fountain of Montjuïc', venue:'Plaça de Carles Buïgas', lat:41.3711, lng:2.1517, dayOffset:0, time:'21:00', hours:2, price:0, category:'culture', organizer:'Ajuntament de Barcelona',
    description:'Water, light and orchestral music, running since the 1929 International Exposition. Free, thirty minutes, and best watched from halfway up the steps.' },

  { id:'ber-1', city:'berlin', title:'Kreuzberg Warm-Up', venue:'Ohlauer Straße, Kreuzberg', lat:52.4977, lng:13.4235, dayOffset:5, time:'23:00', hours:8, price:18, category:'nightlife', organizer:'Club der Visionaere',
    description:'Canal-side, mostly outdoors, wooden decking over the water. Starts late, runs until well into Sunday, and the door is friendlier than the famous one across town.' },
  { id:'ber-2', city:'berlin', title:'Markthalle Neun Street Food Thursday', venue:'Eisenbahnstraße, Kreuzberg', lat:52.5020, lng:13.4318, dayOffset:0, time:'17:00', hours:5, price:0, category:'food', organizer:'Markthalle Neun',
    description:'The market hall that started Berlin\'s street food revival. Forty stalls, every Thursday evening, and the Korean and Neapolitan queues are worth the wait.' },
  { id:'ber-3', city:'berlin', title:'Museum Island Night', venue:'Museumsinsel, Mitte', lat:52.5169, lng:13.4019, dayOffset:6, time:'18:00', hours:6, price:20, category:'art', organizer:'Staatliche Museen',
    description:'One ticket, five museums, open until midnight, with shuttle buses between them. The Pergamon and the Neues are the obvious draws; the Bode is the quiet one.' },
  { id:'ber-4', city:'berlin', title:'Mauerpark Karaoke Sunday', venue:'Mauerpark, Prenzlauer Berg', lat:52.5419, lng:13.4025, dayOffset:3, time:'15:00', hours:4, price:0, category:'culture', organizer:'Bearpit Karaoke',
    description:'A man with a bicycle sound system and two thousand strangers in an amphitheatre. Free, chaotic, and one of the genuinely great things about the city.' },
  { id:'ber-5', city:'berlin', title:'Kreuzberg Record Fair', venue:'Oranienstraße', lat:52.5028, lng:13.4210, dayOffset:8, time:'11:00', hours:7, price:0, category:'music', organizer:'Vinyl Berlin',
    description:'Sixty dealers, heavy on techno, krautrock and jazz reissues. Free entry, bring cash, and the good stuff is gone by one o\'clock.' },
  { id:'ber-6', city:'berlin', title:'Olympiastadion Matchday', venue:'Olympiastadion, Charlottenburg', lat:52.5147, lng:13.2395, dayOffset:10, time:'15:30', hours:3, price:35, category:'sports', organizer:'Hertha BSC',
    description:'Seventy-four thousand capacity in a stadium with a difficult history and a spectacular bowl. The Ostkurve is where the noise comes from.' },
  { id:'ber-7', city:'berlin', title:'Tempelhof Kite Festival', venue:'Tempelhofer Feld', lat:52.4730, lng:13.4030, dayOffset:12, time:'12:00', hours:6, price:0, category:'festival', organizer:'Tempelhofer Feld',
    description:'A decommissioned airport turned public park, and the runways make it the windiest open space in Berlin. Kites supplied for anyone who turns up without one.' }
];

// Keyed by city so a simulated identification matches where the visitor actually is.
const LANDMARKS = {
  london: {
    name: 'Elizabeth Tower (Big Ben)', built: '1859', style: 'Gothic Revival',
    history: 'The clock tower at the north end of the Palace of Westminster was completed in 1859 to a design by Augustus Pugin — his final work before illness ended his career. "Big Ben" properly refers only to the 13.7-tonne hour bell inside, which cracked within months of installation and has rung with a distinctive off-note ever since. The tower was renamed Elizabeth Tower in 2012 for the Diamond Jubilee, and emerged in 2022 from a five-year, £80m restoration that regilded the dials and returned them to their original Prussian blue.',
    nearby: ['Westminster Abbey (400m)', 'Churchill War Rooms (600m)', 'St James\'s Park (900m)'],
    relatedEvents: ['ldn-7', 'ldn-4', 'ldn-3']
  },
  paris: {
    name: 'Eiffel Tower', built: '1889', style: 'Wrought-iron lattice',
    history: 'Built as the entrance arch to the 1889 Exposition Universelle marking the centenary of the French Revolution, and intended to stand for only twenty years. A petition signed by Maupassant, Dumas fils and much of the Parisian artistic establishment denounced it as a "useless and monstrous" tower of bolted sheet metal. It survived because the army found it useful for radio transmission — the aerials on top intercepted German communications during the First World War. It remained the tallest structure in the world until the Chrysler Building overtook it in 1930.',
    nearby: ['Champ de Mars (immediate)', 'Trocadéro (700m)', 'Musée du quai Branly (500m)'],
    relatedEvents: ['par-4', 'par-3', 'par-7']
  },
  newyork: {
    name: 'Brooklyn Bridge', built: '1883', style: 'Hybrid cable-stayed suspension',
    history: 'Fourteen years in construction and the first steel-wire suspension bridge ever built. Its designer John Roebling died of tetanus from a foot injury sustained surveying the site; his son Washington took over and was crippled by decompression sickness working in the caissons, after which his wife Emily Warren Roebling ran the project for eleven years, teaching herself higher mathematics and cable engineering to do it. Six days after it opened, a rumour of collapse caused a stampede that killed twelve people. P.T. Barnum answered it the following year by leading twenty-one elephants across.',
    nearby: ['DUMBO (400m)', 'South Street Seaport (600m)', 'Brooklyn Bridge Park (500m)'],
    relatedEvents: ['nyc-1', 'nyc-2', 'nyc-6']
  },
  tokyo: {
    name: 'Sensō-ji Temple', built: '645 AD', style: 'Buddhist temple complex',
    history: 'Tokyo\'s oldest temple, founded when two fishermen brothers pulled a statue of Kannon from the Sumida River in 628 and the village headman converted his house into a shrine to hold it. The complex was destroyed in the March 1945 firebombing of Tokyo and rebuilt in the 1950s as a symbol of the city\'s recovery — the reconstruction used reinforced concrete rather than timber, deliberately. The great lantern at the Kaminarimon gate is replaced roughly every decade; the current one was donated, as they traditionally are, by a Kyoto manufacturer.',
    nearby: ['Nakamise shopping street (immediate)', 'Sumida Park (600m)', 'Tokyo Skytree (1.3km)'],
    relatedEvents: ['tky-4', 'tky-1', 'tky-7']
  },
  barcelona: {
    name: 'Sagrada Família', built: '1882–present', style: 'Catalan Modernisme',
    history: 'Gaudí took over the project in 1883, aged 31, and spent the last forty-three years of his life on it — the final fifteen exclusively, living on site in a workshop. He knew he would not see it finished and designed it to be continued, leaving plaster models rather than conventional drawings. Most of those models were smashed and the drawings burned by anarchists in 1936; the work since has been partly an act of reconstruction from fragments. Gaudí was killed by a tram in 1926 and, unrecognised in his worn clothes, was initially taken for a beggar. He is buried in the crypt.',
    nearby: ['Hospital de Sant Pau (900m)', 'Casa Milà (1.5km)', 'Park Güell (2.1km)'],
    relatedEvents: ['bcn-3', 'bcn-6', 'bcn-1']
  },
  berlin: {
    name: 'Brandenburg Gate', built: '1791', style: 'Neoclassical',
    history: 'Commissioned by Frederick William II as a symbol of peace and modelled on the Propylaea of the Athenian Acropolis. Napoleon took the Quadriga — the four-horse chariot on top — to Paris as spoils in 1806; it was recovered in 1814 and the goddess was pointedly rearmed with an iron cross. From 1961 the gate stood inside the death strip, unreachable from either side, and became the defining image of the divided city. It reopened on 22 December 1989, six weeks after the Wall fell, to a crowd of more than a hundred thousand people.',
    nearby: ['Reichstag (400m)', 'Holocaust Memorial (300m)', 'Tiergarten (immediate)'],
    relatedEvents: ['ber-3', 'ber-4', 'ber-5']
  }
};

const TRANSLATIONS = {
  london:    { from:'English', sample:'Today\'s Specials', original:'TODAY\'S SPECIALS\n\nPan-fried sea bass, brown shrimp butter — 24\nSlow-cooked short rib, bone marrow mash — 26\nWild mushroom pearl barley — 19\n\nService not included', translated:'TODAY\'S SPECIALS\n\nPan-fried sea bass, brown shrimp butter — £24\nSlow-cooked short rib, bone marrow mash — £26\nWild mushroom pearl barley — £19\n\nService not included', note:'Already in your language — no translation needed.' },
  paris:     { from:'French', sample:'Menu du Jour', original:'MENU DU JOUR\n\nEntrée — Velouté de potiron, huile de noisette\nPlat — Confit de canard, pommes sarladaises\nDessert — Tarte fine aux pommes\n\n32€ — service compris\nPain et eau offerts', translated:'MENU OF THE DAY\n\nStarter — Pumpkin velouté, hazelnut oil\nMain — Duck confit, Sarlat-style potatoes\nDessert — Thin apple tart\n\n€32 — service included\nBread and water complimentary', note:'"Service compris" means the tip is already included — no need to add more.' },
  newyork:   { from:'English', sample:'Subway Notice', original:'SERVICE CHANGE\n\nDowntown 2 and 3 trains run express\nfrom 96 St to Chambers St\n\nFor local stops take the 1', translated:'SERVICE CHANGE\n\nDowntown 2 and 3 trains run express\nfrom 96 St to Chambers St\n\nFor local stops take the 1', note:'Already in your language — no translation needed.' },
  tokyo:     { from:'Japanese', sample:'居酒屋メニュー', original:'本日のおすすめ\n\n刺身盛り合わせ　1,800円\n焼き鳥五本盛り　　980円\n出汁巻き玉子　　　650円\n生ビール　　　　　580円\n\nお通し代　300円', translated:'TODAY\'S RECOMMENDATIONS\n\nAssorted sashimi platter — ¥1,800\nFive-skewer yakitori set — ¥980\nDashi rolled omelette — ¥650\nDraught beer — ¥580\n\nSeating charge — ¥300', note:'"Otōshi" (お通し) is a compulsory small appetiser and seating charge, standard in izakaya. It is not a scam.' },
  barcelona: { from:'Spanish', sample:'Carta de Tapas', original:'TAPAS\n\nPan con tomate — 4,50\nJamón ibérico de bellota — 18\nPimientos de Padrón — 7\nGambas al ajillo — 12\nTortilla de patatas — 6\n\nTerraza: suplemento 10%', translated:'TAPAS\n\nBread with tomato — €4.50\nAcorn-fed Iberian ham — €18\nPadrón peppers — €7\nGarlic prawns — €12\nPotato omelette — €6\n\nTerrace seating: 10% surcharge', note:'Sitting outside costs 10% more here — common in Barcelona and legally required to be displayed.' },
  berlin:    { from:'German', sample:'Hinweisschild', original:'ACHTUNG\n\nDieser Bereich ist videoüberwacht.\n\nFahrräder bitte nur an den\nvorgesehenen Ständern abstellen.\n\nZuwiderhandlungen werden\nkostenpflichtig entfernt.', translated:'ATTENTION\n\nThis area is under video surveillance.\n\nPlease park bicycles only at the\ndesignated racks.\n\nViolations will be removed\nat the owner\'s expense.', note:'"Kostenpflichtig entfernt" means they will tow it and bill you — take this sign seriously.' }
};
