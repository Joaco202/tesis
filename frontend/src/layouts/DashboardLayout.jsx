import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, LayoutDashboard, BarChart3, Users, Menu, X } from 'lucide-react';

export const DashboardLayout = () => {
  const { role, user, signOut } = useAuth();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  const closeMenu = () => {
    if (isMobile) setIsMobileMenuOpen(false);
  };

  const sidebarStyle = {
    width: '250px',
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    borderRadius: 0,
    borderRight: '1px solid var(--border-color)',
    borderTop: 'none',
    borderBottom: 'none',
    borderLeft: 'none',
    backgroundColor: 'var(--bg-secondary)',
    position: isMobile ? 'fixed' : 'relative',
    height: '100vh',
    zIndex: 50,
    transform: isMobile && !isMobileMenuOpen ? 'translateX(-100%)' : 'translateX(0)',
    transition: 'transform 0.3s ease',
  };

  return (
    <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      {/* Mobile Top Bar */}
      {isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: 'var(--ubb-blue)', color: 'white' }}>
          <h2 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 700 }}>UBB Parking</h2>
          <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      )}

      {/* Overlay for mobile */}
      {isMobile && isMobileMenuOpen && (
        <div 
          onClick={closeMenu}
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 40 }}
        />
      )}

      {/* Sidebar */}
      <aside className="glass-panel" style={sidebarStyle}>
        <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ color: 'var(--ubb-blue)', fontSize: '1.25rem', fontWeight: 700 }}>UBB Parking</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Campus Fernando May</p>
          </div>
          {isMobile && (
            <button onClick={closeMenu} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <X size={20} />
            </button>
          )}
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
          {(role === 'guardia' || role === 'encargado' || role === 'admin') && (
            <NavLink 
              to="/dashboard/guardia" 
              onClick={closeMenu}
              className={({isActive}) => `btn ${isActive ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'flex-start', padding: '0.75rem 1rem' }}
            >
              <LayoutDashboard size={18} /> Ocupación en Vivo
            </NavLink>
          )}

          {(role === 'encargado' || role === 'admin') && (
            <NavLink 
              to="/dashboard/encargado" 
              onClick={closeMenu}
              className={({isActive}) => `btn ${isActive ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'flex-start', padding: '0.75rem 1rem' }}
            >
              <BarChart3 size={18} /> Panel KPIs
            </NavLink>
          )}

          {role === 'admin' && (
            <NavLink 
              to="/dashboard/admin" 
              onClick={closeMenu}
              className={({isActive}) => `btn ${isActive ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'flex-start', padding: '0.75rem 1rem' }}
            >
              <Users size={18} /> Usuarios y Roles
            </NavLink>
          )}
          
          <NavLink 
            to="/" 
            onClick={closeMenu}
            className="btn btn-secondary"
            style={{ justifyContent: 'flex-start', padding: '0.75rem 1rem', marginTop: 'auto' }}
          >
             Vista Pública
          </NavLink>
        </nav>

        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            <strong>Usuario:</strong> {user?.email}
            <br />
            <span className="badge badge-primary" style={{ marginTop: '0.25rem' }}>Rol: {role || 'Test'}</span>
          </div>
          <button onClick={handleLogout} className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start', color: 'var(--status-danger)' }}>
            <LogOut size={18} /> Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: isMobile ? '1rem' : '2rem', overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
};
