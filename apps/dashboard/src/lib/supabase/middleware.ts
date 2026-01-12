import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

type CookieToSet = { name: string; value: string; options?: CookieOptions }

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet: CookieToSet[]) {
          cookiesToSet.forEach(({ name, value }: CookieToSet) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }: CookieToSet) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // Use getSession instead of getUser for faster middleware execution
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession()

  const user = session?.user

  // Debug logging
  console.log(`[Middleware] Path: ${request.nextUrl.pathname}, Session: ${session ? 'yes' : 'no'}, User: ${user?.email || 'none'}, Error: ${error?.message || 'none'}`)

  // Protected routes - only check on initial page load, not prefetch
  const protectedPaths = ['/dashboard']
  const isProtectedPath = protectedPaths.some((path) =>
    request.nextUrl.pathname.startsWith(path)
  )

  // Skip auth check for prefetch requests
  const isPrefetch = request.headers.get('purpose') === 'prefetch' ||
                     request.headers.get('x-middleware-prefetch') === '1'

  if (isProtectedPath && !session && !isPrefetch) {
    console.log(`[Middleware] Redirecting to login - no session for protected path`)
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Redirect logged in users away from auth pages
  const authPaths = ['/login', '/register']
  const isAuthPath = authPaths.some((path) =>
    request.nextUrl.pathname.startsWith(path)
  )

  if (isAuthPath && session && !isPrefetch) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
