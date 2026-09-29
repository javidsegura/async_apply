/**
 * The AsyncApply wordmark: an inline SVG so it never needs an external
 * image asset and can be recolored/sized like any other element. The
 * glyph is a small forward chevron pair suggesting motion/automation --
 * the agent moving through a pipeline on its own.
 */
export default function Logo({ className = '', markClassName = '', textClassName = '' }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg
        viewBox="0 0 32 32"
        width="24"
        height="24"
        aria-hidden="true"
        className={`shrink-0 ${markClassName}`}
      >
        <defs>
          <linearGradient id="asyncapply-logo-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="9" fill="url(#asyncapply-logo-gradient)" />
        <path
          d="M11 9L18 16L11 23"
          stroke="white"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M18 9L25 16L18 23"
          stroke="white"
          strokeOpacity="0.55"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
      <span className={`font-semibold tracking-tight ${textClassName}`}>AsyncApply</span>
    </span>
  )
}
