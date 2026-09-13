import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';

const authSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET || 'baleen_super_secret_sandbox_jwt_key_2026_polymarket';
if (!process.env.AUTH_SECRET && !process.env.NEXTAUTH_SECRET && process.env.NODE_ENV === 'production') {
  throw new Error("AUTH_SECRET or NEXTAUTH_SECRET is required in production");
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  secret: authSecret,
  trustHost: true,
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const email = String(credentials.email).toLowerCase().trim();
        const password = String(credentials.password);

        let backendUrl = (
          process.env.BACKEND_URL || 
          process.env.NEXT_PUBLIC_BACKEND_URL || 
          process.env.NEXT_PUBLIC_API_URL || 
          'http://localhost:8000'
        ).trim().replace(/\/$/, '');

        if (backendUrl && !backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
          backendUrl = `https://${backendUrl}`;
        }

        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 5000);

          const res = await fetch(
            `${backendUrl}/api/auth/login`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email,
                password,
              }),
              signal: controller.signal,
            }
          );
          clearTimeout(timeoutId);

          if (res.ok) {
            const user = await res.json();
            return {
              id: user.id,
              email: user.email,
              name: user.name || user.email,
              isAdmin: Boolean(user.is_admin || user.isAdmin),
              accessToken: user.access_token,
            };
          }
        } catch (e) {
          console.error("NextAuth backend authorize error:", e);
        }

        return null;
      },
    }),
  ],
  session: {
    strategy: 'jwt',
    maxAge: 72 * 60 * 60,
  },
  pages: {
    signIn: '/auth/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.isAdmin = (user as { isAdmin?: boolean }).isAdmin;
        token.accessToken = (user as { accessToken?: string }).accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        const u = session.user as { id?: string; isAdmin?: boolean; accessToken?: string };
        u.id = token.id as string;
        u.isAdmin = Boolean(token.isAdmin);
        u.accessToken = token.accessToken as string;
      }
      (session as { accessToken?: string }).accessToken = token.accessToken as string;
      return session;
    },
  },
});
