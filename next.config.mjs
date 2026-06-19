import nextra from 'nextra'

const withNextra = nextra({})

// NOTE: static export (`output: 'export'`) was removed 2026-06-19 so middleware.ts
// can run a password gate at the edge. Static export has no server/middleware and
// cannot enforce auth. Deploys as a normal Next.js app on Vercel.
export default withNextra({
  images: { unoptimized: true }
})
