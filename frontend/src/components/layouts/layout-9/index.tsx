import { Helmet } from 'react-helmet-async';
import { LayoutProvider } from '@/components/layouts/layout-1/components/context';
import { Main } from './components/main';

export function Layout9() {
  return (
    <>
      <Helmet>
        <title>Photo Manager</title>
      </Helmet>

      <LayoutProvider>
        <Main />
      </LayoutProvider>
    </>
  );
}
