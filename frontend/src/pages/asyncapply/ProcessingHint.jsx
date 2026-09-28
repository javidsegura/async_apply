import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// Illustrative only -- there is no per-stage progress signal from the
// backend (see PipelineDag's deriveStages), so this never claims to know
// what is actually happening right now. It exists purely so a multi-second
// wait doesn't look frozen; phrasing is deliberately generic pipeline
// language, not a fabricated log of real steps.
const PHRASES = [
  'Reading through the posting…',
  'Comparing it against your CV…',
  'Weighing strengths and gaps…',
  'Checking work authorization and location…',
  'Choosing which projects to lead with…',
  'Drafting the tailored CV…',
  'Writing the cover letter…',
  'Looking for the right person to contact…',
  'Scoring candidates against the role…',
]

/**
 * A slowly cycling, purely decorative line of text shown while an item is
 * running, so the wait feels alive instead of frozen. Never presented as a
 * real progress log -- rotates on a fixed timer, not tied to any signal.
 */
export default function ProcessingHint() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * PHRASES.length))

  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % PHRASES.length), 9000)
    return () => clearInterval(id)
  }, [])

  return (
    <AnimatePresence mode="wait">
      <motion.span
        key={index}
        initial={{ opacity: 0, y: 3 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -3 }}
        transition={{ duration: 0.4 }}
        className="text-xs italic text-stone-400"
      >
        {PHRASES[index]}
      </motion.span>
    </AnimatePresence>
  )
}
