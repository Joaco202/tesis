import React from 'react';
import { LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AppHeader = () => {
  const { user, role, signOut } = useAuth();

  const roleLabel = {
    guardia: 'Guardia',
    encargado: 'Encargado',
    admin: 'Administrador TI',
  }[role] || role;

  return (
    <header
      style={{
        backgroundColor: 'var(--ubb-blue)',
        padding: '0.75rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
        <img
          src="/logoUBB2.png"
          alt="Logo UBB"
          style={{ height: '36px', width: 'auto' }}
        />
        <div>
          <p style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0, lineHeight: 1.2 }}>
            Universidad del Bío-Bío
          </p>
          <p style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.75)', margin: 0 }}>
            Campus Fernando May
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        {user && (
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'white', margin: 0, lineHeight: 1.2 }}>
              {user.email}
            </p>
            <p style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', margin: 0 }}>
              {roleLabel}
            </p>
          </div>
        )}
        <button
          onClick={signOut}
          title="Cerrar sesión"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.4rem 0.85rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255,255,255,0.35)',
            backgroundColor: 'rgba(255,255,255,0.1)',
            color: 'white',
            fontSize: '0.8rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'background-color 0.2s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.22)'}
          onMouseLeave={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
        >
          <LogOut size={15} />
          Salir
        </button>
      </div>
    </header>
  );
};
