import { NextRequest, NextResponse } from 'next/server'

// Password gate for the whole docs site (added 2026-06-19).
// Uses HTTP Basic Auth against Vercel env vars DOCS_USER (default "gui") and
// DOCS_PASSWORD. Runs at the edge on every request except build assets.
//
// Fail-closed: if DOCS_PASSWORD is not set in the environment, the site returns
// 503 (locked) rather than serving content unprotected.

export const config = {
  // Gate everything except Next build assets (non-sensitive JS/CSS chunks) and
  // the favicon. The browser auto-resends Basic credentials on asset requests
  // once authenticated, so gating pages + data is sufficient.
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}

function unauthorized() {
  return new NextResponse('Authentication required.', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="InnerOS Docs", charset="UTF-8"',
    },
  })
}

export function middleware(req: NextRequest) {
  const expectedUser = process.env.DOCS_USER || 'gui'
  const expectedPass = process.env.DOCS_PASSWORD

  // Fail closed if no password configured.
  if (!expectedPass) {
    return new NextResponse('Site auth not configured.', { status: 503 })
  }

  const header = req.headers.get('authorization')
  if (header?.startsWith('Basic ')) {
    try {
      const decoded = atob(header.slice(6))
      const sep = decoded.indexOf(':')
      const user = decoded.slice(0, sep)
      const pass = decoded.slice(sep + 1)
      if (user === expectedUser && pass === expectedPass) {
        return NextResponse.next()
      }
    } catch {
      // fall through to 401
    }
  }
  return unauthorized()
}
