import { auth } from '@/lib/auth';
import { NextResponse } from 'next/server';

export const proxy = auth((req) => {
  const { nextUrl } = req;
  const isLoggedIn = !!req.auth;
  const isDashboard = nextUrl.pathname.startsWith('/dashboard');
  const isSettings = nextUrl.pathname.startsWith('/settings');
  const isAdmin = nextUrl.pathname.startsWith('/admin');

  if ((isDashboard || isSettings || isAdmin) && !isLoggedIn) {
    const loginUrl = new URL('/auth/login', nextUrl.origin);
    loginUrl.searchParams.set('callbackUrl', nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isAdmin && isLoggedIn) {
    const user = req.auth?.user as { isAdmin?: boolean } | undefined;
    if (!user?.isAdmin) {
      return NextResponse.redirect(new URL('/dashboard', nextUrl.origin));
    }
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/settings/:path*',
    '/admin/:path*',
  ],
};
