import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const backendUrl = (
          process.env.BACKEND_URL || 
          process.env.NEXT_PUBLIC_BACKEND_URL || 
          process.env.NEXT_PUBLIC_API_URL || 
          'http://localhost:8000'
        ).replace(/\/$/, '');

        try {
          const res = await fetch(
            `${backendUrl}/api/auth/login`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email: credentials.email,
                password: credentials.password,
              }),
            }
          );

          if (!res.ok) return null;
          const user = await res.json();
          return { id: user.id, email: user.email };
        } catch (e) {
          console.error("NextAuth authorize error:", e);
          return null;
        }
      },
    }),
  ],
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/auth/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id as string;
      }
      return session;
    },
    authorized({ auth: session, request: { nextUrl } }) {
      const isLoggedIn = !!session?.user;
      const isProtected =
        nextUrl.pathname.startsWith('/dashboard') ||
        nextUrl.pathname.startsWith('/settings');

      if (isProtected && !isLoggedIn) {
        return Response.redirect(new URL('/auth/login', nextUrl));
      }
      return true;
    },
  },
  trustHost: true,
});
