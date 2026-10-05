// Каждый .md из docs/, research/, calc/, ecu/ должен быть здесь или в repoHidden
// (docusaurus.config.js) — иначе сборка падает, и новое исследование не потеряется.
const cat = (label, items, extra = {}) => ({type: 'category', label, items, ...extra});

export default {
  repo: [
    {type: 'doc', id: 'docs/project', label: 'Концепция и комплект'},
    {type: 'doc', id: 'docs/plan', label: 'План работ'},
    cat('Исследования', [
      'research/parts-list',
      'research/engine-data',
      cat('Впуск, газ и зажигание', [
        'research/fuel-system',
        'research/electronic-throttle',
        'research/ignition',
        'research/intake-manufacturing',
        'research/intake-rfq',
      ]),
      cat('ГРМ и смазка', ['research/valvetrain', 'research/lubrication']),
      cat('Наддув, охлаждение, выпуск', [
        'research/turbo',
        'research/drivetrain-cooling-exhaust',
        'research/cooling-accessories',
      ]),
      cat('Трансмиссия', [
        'research/transmission/zil130-manual',
        'research/transmission/zil131-chassis',
        'research/transmission/allison-2000',
        'research/transmission/alternatives',
      ]),
      cat('Вики: модификации', ['research/wiki/zil130', 'research/wiki/zil131']),
      cat('Опыт сообщества', ['research/prior-art', 'research/videos/notes']),
      cat('Библиотека источников', ['research/sources/drawings/README'], {link: {type: 'doc', id: 'research/sources/README'}}),
    ], {link: {type: 'doc', id: 'research/README'}}),
    cat('Расчёты', ['calc/results', 'calc/knock_results']),
    {type: 'doc', id: 'ecu/README', label: 'Настройки rusEFI'},
  ],
};
