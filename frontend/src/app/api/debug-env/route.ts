import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';

export async function GET() {
  if (process.env.NODE_ENV === 'production') {
    const session = await auth();
    if (!session?.user || !(session.user as { isAdmin?: boolean }).isAdmin) {
      return NextResponse.json({ error: 'Not Found' }, { status: 404 });
    }
  }

  let backendUrl = (
    process.env.BACKEND_URL || 
    process.env.NEXT_PUBLIC_BACKEND_URL || 
    process.env.NEXT_PUBLIC_API_URL || 
    'NONE_SET'
  ).trim().replace(/\/$/, '');

  if (backendUrl && backendUrl !== 'NONE_SET' && !backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
    backendUrl = `https://${backendUrl}`;
  }

  let backendReachable = false;
  let backendError = '';
  try {
    const res = await fetch(`${backendUrl}/health`, { 
      signal: AbortSignal.timeout(5000) 
    });
    backendReachable = res.ok;
  } catch (e: unknown) {
    backendError = e instanceof Error ? e.message : String(e);
  }

  return NextResponse.json({
    status: 'ok',
    backendReachable,
    backendError: backendError || undefined,
  });
}
