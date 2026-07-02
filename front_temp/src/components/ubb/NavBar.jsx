// src/components/ubb/NavBar.jsx
import { Link, useLocation } from 'react-router-dom';

export function UBBNavBar({ items = [] }) {
  const location = useLocation();

  return (
    <nav style={{
      backgroundColor: 'var(--ubb-primary)',
      padding: '0 2rem',
      display: 'flex',
      gap: '0.5rem'
    }}>
      {items.map(item => {
        const isActive = location.pathname === item.href;
        return (
          <Link 
            key={item.label} 
            to={item.href} 
            style={{
              color: 'white',
              padding: '0.75rem 1rem',
              textDecoration: 'none',
              fontSize: '0.9rem',
              opacity: isActive ? 1 : 0.8,
              fontWeight: isActive ? 600 : 400,
              borderBottom: isActive ? '3px solid white' : '3px solid transparent',
              transition: 'all 0.2s ease'
            }}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
