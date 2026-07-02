// src/components/ubb/Header.jsx
export function UBBHeader({ title, children }) {
  return (
    <header style={{
      backgroundColor: 'var(--ubb-primary-dark)',
      color: 'white',
      padding: '0 2rem',
      height: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Reemplaza con el logo real de la UBB */}
        <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>UBB</span>
        <span style={{
          width: '1px',
          height: '32px',
          backgroundColor: 'rgba(255,255,255,0.3)'
        }} />
        <span style={{ fontSize: '0.95rem' }}>{title}</span>
      </div>
      {children && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          {children}
        </div>
      )}
    </header>
  )
}
