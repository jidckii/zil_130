import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import MDXContent from '@theme/MDXContent';
import Manifesto from './_manifesto.mdx';
import styles from './index.module.css';

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Модернизация ЗИЛ-130 и ЗИЛ-131"
      description="Проект-исследование по комплексной модернизации ЗИЛ-130 и ЗИЛ-131: двигатель, коробка передач и другие узлы">
      <header className={clsx('hero hero--primary', styles.hero)}>
        <div className="container">
          <h1 className="hero__title">НеоЗИЛ</h1>
          <p className="hero__subtitle">
            Проект-исследование по комплексной модернизации ЗИЛ-130 и ЗИЛ-131
          </p>
          <div className={styles.buttons}>
            <Link className="button button--secondary button--lg" to="/docs/intro">
              Документация
            </Link>
            <Link className={clsx('button button--outline button--lg', styles.outline)} to="/docs/contributing">
              Как помочь
            </Link>
            <Link className={clsx('button button--outline button--lg', styles.outline)} to={siteConfig.customFields.repo}>
              GitHub
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
