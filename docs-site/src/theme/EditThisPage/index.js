import EditThisPage from '@theme-original/EditThisPage';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {useDoc} from '@docusaurus/plugin-content-docs/client';

export default function EditThisPageWrapper(props) {
  const {siteConfig} = useDocusaurusContext();
  const {metadata} = useDoc();
  const issue = new URLSearchParams({
    title: `${metadata.title}: `,
    body: `Страница: ${siteConfig.url}${metadata.permalink}\n\n`,
  });
  return (
    <>
      <EditThisPage {...props} />
      <br />
      <Link to={`${siteConfig.customFields.repo}/issues/new?${issue}`}>
        Сообщить об ошибке или прислать замер
      </Link>
    </>
  );
}
