import { type NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

export async function middleware(request: NextRequest) {
  return await updateSession(request)
}

export const config = {
  matcher: [
    // Only run middleware on specific paths that need auth checking
    '/dashboard/:path*',
    '/login',
    '/register',
    '/',
  ],
}
