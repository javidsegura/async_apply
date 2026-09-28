import { useMemo } from 'react'

/**
 * Lay out a value tree into fixed columns, one per depth level. Because each
 * item belongs to exactly one status, a node's children always partition its
 * full value -- a child's slice of its parent has exactly the child's own
 * height, so the connecting band never has to reconcile mismatched flows the
 * way a general Sankey (multiple parents per node) would.
 *
 * @param {object} node - {id, label, value, color, children?}
 * @param {number} depth
 * @param {number} y0
 * @param {number} y1
 * @returns {{boxes: object[], bands: object[]}}
 */
function layout(node, depth, y0, y1) {
  const boxes = [{ ...node, depth, y0, y1 }]
  const bands = []
  if (!node.children?.length) return { boxes, bands }

  let cursor = y0
  const total = node.value || 1
  for (const child of node.children) {
    const h = ((child.value || 0) / total) * (y1 - y0)
    const childY0 = cursor
    const childY1 = cursor + h
    bands.push({ depth, y0: childY0, y1: childY1, color: child.color })
    const sub = layout(child, depth + 1, childY0, childY1)
    boxes.push(...sub.boxes)
    bands.push(...sub.bands)
    cursor = childY1
  }
  return { boxes, bands }
}

function maxDepthOf(node, depth = 0) {
  if (!node.children?.length) return depth
  return Math.max(...node.children.map((c) => maxDepthOf(c, depth + 1)))
}

/**
 * A flow diagram from a value tree, e.g. Submitted -> Hard-stopped/Evaluated
 * -> Not applied/Applied+ -> outcomes. `compact` hides labels and shrinks
 * padding for use as a small preview.
 *
 * @param {{root: object, width?: number, height?: number, compact?: boolean}} props
 */
export default function Sankey({ root, width = 720, height = 360, compact = false }) {
  const depth = useMemo(() => maxDepthOf(root), [root])
  const nodeWidth = compact ? 5 : 14
  const pad = compact ? 4 : 10
  const usable = width - pad * 2 - nodeWidth
  const colSpacing = usable / Math.max(1, depth)

  const { boxes, bands } = useMemo(
    () => layout(root, 0, pad, height - pad),
    [root, height, pad],
  )

  const xOf = (d) => pad + d * colSpacing

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
      {bands.map((b, i) => (
        <rect
          key={i}
          x={xOf(b.depth) + nodeWidth}
          y={b.y0}
          width={colSpacing - nodeWidth}
          height={Math.max(0, b.y1 - b.y0)}
          fill={b.color}
          opacity={compact ? 0.3 : 0.22}
        />
      ))}
      {boxes.map((b) => (
        <g key={b.id}>
          <rect x={xOf(b.depth)} y={b.y0} width={nodeWidth} height={Math.max(0, b.y1 - b.y0)} fill={b.color} rx={2} />
          {!compact && b.y1 - b.y0 > 13 && (
            <text
              x={xOf(b.depth) + nodeWidth + 6}
              y={(b.y0 + b.y1) / 2}
              dominantBaseline="middle"
              className="fill-stone-600 text-[11px]"
            >
              {b.label} <tspan className="fill-stone-400">({b.value})</tspan>
            </text>
          )}
        </g>
      ))}
    </svg>
  )
}
