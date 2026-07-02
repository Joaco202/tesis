import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut } from 'lucide-react';
import { UBBHeader } from '../components/ubb/Header';
import { UBBNavBar } from '../components/ubb/NavBar';

export const DashboardLayout = () => {
  const { role, user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  const navItems = [];
  if (role === 'guardia' || role === 'encargado' || role === 'admin') {
    navItems.push({ label: 'Ocupación en Vivo', href: '/dashboard/guardia' });
  }
  if (role === 'encargado' || role === 'admin') {
    navItems.push({ label: 'Panel KPIs', href: '/dashboard/encargado' });
  }
  if (role === 'admin') {
    navItems.push({ label: 'Usuarios y Roles', href: '/dashboard/admin' });
  }
  navItems.push({ label: 'Vista Pública', href: '/' });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--ubb-bg)' }}>
      {/* Header con UBBHeader */}
      <UBBHeader title="Sistema de Detección de Patentes">
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.85rem' }}>
            <span style={{ opacity: 0.85 }}>{user.email}</span>
            <span style={{
              backgroundColor: 'rgba(255,255,255,0.15)',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase'
            }}>
              {role || 'usuario'}
            </span>
            <button 
              onClick={handleLogout} 
              style={{
                background: 'none',
                border: 'none',
                color: '#ff4d4f',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.85rem',
                padding: '4px 8px',
                borderRadius: '4px',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(255, 77, 79, 0.1)'}
              onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
            >
              <LogOut size={14} />
              Cerrar Sesión
            </button>
          </div>
        )}
      </UBBHeader>

      {/* Menú de Navegación superior con UBBNavBar */}
      <UBBNavBar items={navItems} />

      {/* Main Content Area */}
      <main style={{ 
        flex: 1, 
        padding: '2rem', 
        maxWidth: '1200px', 
        width: '100%', 
        margin: '0 auto' 
      }}>
        <Outlet />
      </main>
    </div>
  );
};
