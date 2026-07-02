// src/components/ubb/Badge.jsx
export function UBBBadge({ text, type = 'primary' }) {
  const colors = {
    primary: { bg: '#0066FF', color: 'white' },
    success: { bg: '#003272', color: 'white' },
    danger:  { bg: '#E20613', color: 'white' },
    warning: { bg: '#FFCC33', color: '#1A1A1A' },
  }
  const c = colors[type] || colors.primary
  return (
    <span style={{
      backgroundColor: c.bg,
      color: c.color,
      padding: '3px 10px',
      borderRadius: '4px',
      fontSize: '0.8rem',
      fontWeight: 600,
      display: 'inline-block'
    }}>{text}</span>
  )
}
