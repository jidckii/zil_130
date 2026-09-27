import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import MDXContent from '@theme/MDXContent';
import Manifesto from './_manifesto.mdx';
import styles from './index.module.css';

export default function Home() {
  return (
    <Layout
      title="Открытый проект"
      description="Недорогой и повторяемый перевод V8 ЗИЛ-130 и ЗИЛ-131 с карбюратора на распределённый впрыск, с турбонаддувом и без">
      <header className={clsx('hero hero--primary', styles.hero)}>
        <div className="container">
          <h1 className="hero__title">ЗИЛ-130 и ЗИЛ-131 на впрыске</h1>
          <p className="hero__subtitle">
            Открытый проект: недорогой и повторяемый перевод V8 ЗИЛ с карбюратора на распределённый
            впрыск — с турбонаддувом и без
          </p>
          <div className={styles.buttons}>
            <Link className="button button--secondary button--lg" to="/docs/intro">
              Документация
            </Link>
            <Link className={clsx('button button--outline button--lg', styles.outline)} to="/docs/contributing">
              Как помочь
            </Link>
          </div>
        </div>
      </header>
      <main className={clsx('container', 'markdown', styles.main)}>
        <MDXContent>
          <Manifesto />
        </MDXContent>
      </main>
    </Layout>
  );
}
