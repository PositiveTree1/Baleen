'use client';

import { SessionProvider, signOut } from 'next-auth/react';
import { useEffect } from 'react';
import { ThemeProvider } from '@/context/ThemeContext';

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    let signingOut = false;
    const onExpired = () => {
      if (signingOut) return;
      signingOut = true;
      void signOut({ callbackUrl: '/auth/login?reason=session-expired' });
    };
    window.addEventListener('baleen:session-expired', onExpired);
    return () => window.removeEventListener('baleen:session-expired', onExpired);
  }, []);

  return (
    <SessionProvider>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </SessionProvider>
  );
}
