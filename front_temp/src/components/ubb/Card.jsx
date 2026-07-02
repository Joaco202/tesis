// src/components/ubb/Card.jsx
export function UBBCard({ title, children }) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      borderRadius: '8px',
      borderTop: '3px solid var(--ubb-primary)',
      padding: '1.25rem',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)'
    }}>
      {title && (
        <h3 style={{
          color: 'var(--ubb-primary-dark)',
          margin: '0 0 1rem',
          fontSize: '1rem',
          fontWeight: 600
        }}>{title}</h3>
      )}
      {children}
    </div>
  )
}
