import {cpSync, rmSync} from 'node:fs';
import {themes as prismThemes} from 'prism-react-renderer';

const repo = 'https://github.com/jidckii/zil_130';

// Исследования лежат в корне репозитория, и их копируем в docs-site/repo/.
// Плагин docs с path: '..' захватил бы и сам docs-site/: его MDX-правило
// компилировало бы страницы сайта второй раз, и сборка падает.
const repoDocs = ['docs/plan.md', 'research', 'calc', 'ecu'];
rmSync(new URL('repo/', import.meta.url), {recursive: true, force: true});
for (const p of repoDocs) {
  cpSync(new URL(`../${p}`, import.meta.url), new URL(`repo/${p}`, import.meta.url), {
    recursive: true,
    filter: (src) => !/\.\w+$/.test(src) || /\.(md|lua)$/.test(src),
  });
}

/** @type {import('@docusaurus/types').Config} */
export default {
  title: 'ЗИЛ-130 на впрыске',
  tagline: 'Открытый проект перевода V8 ЗИЛ-130 и ЗИЛ-131 на распределённый впрыск',
  url: 'https://jidckii.github.io',
  baseUrl: '/zil_130/',
  organizationName: 'jidckii',
  projectName: 'zil_130',
  trailingSlash: false,
  customFields: {repo},

  future: {v4: true},

  onBrokenLinks: 'throw',
  // Исследования — рабочие .md из репозитория, а не MDX: в них встречаются
  // «<», «{» и прочее, что MDX принял бы за разметку.
  markdown: {
    format: 'detect',
    hooks: {onBrokenMarkdownLinks: 'warn'},
  },

  i18n: {defaultLocale: 'ru', locales: ['ru']},

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          editUrl: ({docPath}) => `${repo}/edit/main/docs-site/docs/${docPath}`,
        },
        blog: false,
        theme: {customCss: './src/css/custom.css'},
      }),
    ],
  ],

  plugins: [
    [
      '@docusaurus/plugin-content-docs',
      {
        // URL повторяет путь файла в репозитории: /repo/research/turbo ↔ research/turbo.md
        id: 'repo',
        path: 'repo',
        routeBasePath: 'repo',
        sidebarPath: './sidebarsRepo.js',
        editUrl: ({docPath}) => `${repo}/edit/main/${docPath}`,
      },
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/renders/intake-iso-front.png',
      colorMode: {respectPrefersColorScheme: true},
      navbar: {
        title: 'ЗИЛ-130 · впрыск',
        items: [
          {type: 'docSidebar', sidebarId: 'defaultSidebar', label: 'Документация', position: 'left'},
          {type: 'docSidebar', sidebarId: 'repo', docsPluginId: 'repo', label: 'Исследования и расчёты', position: 'left'},
          {to: '/docs/contributing', label: 'Как помочь', position: 'left'},
          {href: repo, label: 'GitHub', position: 'right'},
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Проект',
            items: [
              {label: 'О проекте', to: '/docs/intro'},
              {label: 'Варианты переделки', to: '/docs/variants'},
              {label: 'План и этапы', to: '/repo/docs/plan'},
            ],
          },
          {
            title: 'Участие',
            items: [
              {label: 'Как помочь', to: '/docs/contributing'},
              {label: 'Задачи и обсуждения', href: `${repo}/issues`},
              {label: 'Исходники', href: repo},
            ],
          },
        ],
        copyright: `© 2026 Евгений Медведев и участники проекта. Код — MIT, тексты и модели — CC BY 4.0.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'lua', 'python'],
      },
    }),
};
